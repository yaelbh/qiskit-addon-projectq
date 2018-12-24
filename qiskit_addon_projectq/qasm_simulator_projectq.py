# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=unused-import

"""Backend for the Project Q C++ simulator."""


import time
import itertools
import operator
import random
import uuid
import logging
import warnings
from collections import OrderedDict, Counter
import numpy as np
from qiskit.result import Result
from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration
from .projectqjob import ProjectQJob
from .projectqsimulatorerror import ProjectQSimulatorError
try:
    from projectq.backends._sim._cppsim import Simulator as CppSim
except ImportError:
    CppSim = None
else:
    from projectq import MainEngine
    from projectq.backends import Simulator
    from projectq.ops import (H,
                              X,
                              Y,
                              Z,
                              S,
                              T,
                              Rx,
                              Ry,
                              Rz,
                              CX,
                              Toffoli,
                              Measure,
                              BasicGate,
                              BasicMathGate,
                              QubitOperator,
                              TimeEvolution,
                              All)
logger = logging.getLogger(__name__)


class QasmSimulatorProjectQ(BaseBackend):
    """Python interface to Project Q simulator"""

    DEFAULT_CONFIGURATION = {
        'backend_name': 'projectq_qasm_simulator',
        'backend_version': '0.1.0',
        'url': 'https://github.com/QISKit/qiskit-addon-projectq',
        'simulator': True,
        'local': True,
        'description': 'ProjectQ C++ simulator',
        'basis_gates': ['u1', 'u2', 'u3', 'cx', 'id', 'h', 's', 't'],
        'memory': True,
        'n_qubits': 30,
        'conditional': False,
        'max_shots': 100000,
        'open_pulse': False,
        'gates': [
            {
                'name': 'TODO',
                'parameters': [],
                'qasm_def': 'TODO'
            }
        ]
    }

    def __init__(self, configuration=None, provider=None):
        """
        Args:
            configuration (BackendConfiguration): backend configuration
            provider (ProjectQProvider): parent provider
        Raises:
             ImportError: if the Project Q simulator is not available.
        """
        super().__init__(configuration=(configuration or
                                        BackendConfiguration.from_dict(self.DEFAULT_CONFIGURATION)),
                         provider=provider)

        if CppSim is None:
            logger.info('Project Q C++ simulator unavailable.')
            raise ImportError('Project Q C++ simulator unavailable.')

        # Define the attributes inside __init__.
        self._number_of_qubits = 0
        self._number_of_clbits = 0
        self._classical_state = 0
        self._seed = None
        self._shots = 0
        self._sim = None

    def run(self, qobj):
        """Run qobj asynchronously.

        Args:
            qobj (QObj): QObj structure

        Returns:
            ProjectQJob: derived from BaseJob
        """
        job_id = str(uuid.uuid4())
        projectq_job = ProjectQJob(self, job_id, self._run_job, qobj)
        projectq_job.submit()
        return projectq_job

    def _run_job(self, job_id, qobj):
        """Run circuits in qobj and return the result

            Args:
                qobj (Qobj): Qobj structure
                job_id (str): A job id

            Returns:
                qiskit.Result: Result is a class including the information to be returned to users.
                    Specifically, result_list in the return contains the essential information,
                    which looks like this::

                        [{'data':
                        {
                          'counts': {'000': 40, '111': 60}
                        },
                        'status': 'DONE'
                        }]
        """

        result_list = []
        self._validate(qobj)
        self._sim = Simulator(gate_fusion=True)
        if hasattr(qobj.config, 'seed'):
            self._seed = qobj.config.seed
            self._sim._simulator = CppSim(self._seed)
        else:
            self._seed = random.getrandbits(32)
        self._shots = qobj.config.shots
        start = time.time()
        for circuit in qobj.experiments:
            result_list.append(self.run_circuit(circuit))
        end = time.time()
        job_id = str(uuid.uuid4())

        result = {'backend_name': self._configuration.backend_name,
                  'backend_version': '0.1.0',
                  'qobj_id': qobj.qobj_id,
                  'job_id': job_id,
                  'results': result_list,
                  'status': 'COMPLETED',
                  'success': True,
                  'time_taken': (end - start)}
        return Result.from_dict(result)

    def run_circuit(self, circuit):
        """Run a circuit and return a single Result.

        Args:
            circuit (QobjExperiment): Qobj experiment

        Returns:
            dict: A dictionary of results which looks something like:

                {
                "data":
                    {  #### DATA CAN BE A DIFFERENT DICTIONARY FOR EACH BACKEND ####
                    "counts": {'00000': XXXX, '00001': XXXXX},
                    "time"  : xx.xxxxxxxx
                    },
                "status": --status (string)--
                }
        Raises:
            ProjectQSimulatorError: if an error occurred.
        """
        # pylint: disable=expression-not-assigned,pointless-statement
        self._number_of_qubits = circuit.config.n_qubits
        self._number_of_clbits = circuit.config.memory_slots
        self._classical_state = 0
        cl_reg_index = []  # starting bit index of classical register
        cl_reg_nbits = []  # number of bits in classical register
        clbit_index = 0
        qobj_quregs = OrderedDict(_get_register_specs(
            circuit.header.qubit_labels))
        eng = MainEngine(backend=self._sim)
        for cl_reg in circuit.header.clbit_labels:
            cl_reg_nbits.append(cl_reg[1])
            cl_reg_index.append(clbit_index)
            clbit_index += cl_reg[1]
        # let circuit seed override qobj default
        if hasattr(circuit, 'config'):
            if hasattr(circuit.config, 'seed'):
                if circuit.config.seed is not None:
                    self._sim._simulator = CppSim(circuit.config.seed)
        outcomes = []
        snapshots = {}
        projq_qureg_dict = OrderedDict(((key, eng.allocate_qureg(size))
                                        for key, size in
                                        qobj_quregs.items()))

        if self._shots > 1:
            ground_state = np.zeros(1 << self._number_of_qubits, dtype=complex)
            ground_state[0] = 1

        start = time.time()
        for i in range(self._shots):
            # initialize starting state
            self._classical_state = 0

            qureg = [qubit for sublist in projq_qureg_dict.values()
                     for qubit in sublist]

            if i > 0:
                eng.flush()
                eng.backend.set_wavefunction(ground_state, qureg)

            # Do each operation in this shot
            for operation in circuit.instructions:
                if hasattr(operation, 'conditional'):
                    mask = int(operation.conditional.mask, 16)
                    if mask > 0:
                        value = self._classical_state & mask
                        while (mask & 0x1) == 0:
                            mask >>= 1
                            value >>= 1
                        if value != int(operation.conditional.val, 16):
                            continue
                # Check if single gate
                if operation.name in ['U', 'u3']:
                    params = operation.params
                    qubit = qureg[operation.qubits[0]]
                    Rz(params[2]) | qubit
                    Ry(params[0]) | qubit
                    Rz(params[1]) | qubit
                elif operation.name in ['u1']:
                    params = operation.params
                    qubit = qureg[operation.qubits[0]]
                    Rz(params[0]) | qubit
                elif operation.name in ['u2']:
                    params = operation.params
                    qubit = qureg[operation.qubits[0]]
                    Rz(params[1] - np.pi/2) | qubit
                    Rx(np.pi/2) | qubit
                    Rz(params[0] + np.pi/2) | qubit
                elif operation.name == 't':
                    qubit = qureg[operation.qubits[0]]
                    T | qubit
                elif operation.name == 'h':
                    qubit = qureg[operation.qubits[0]]
                    H | qubit
                elif operation.name == 's':
                    qubit = qureg[operation.qubits[0]]
                    S | qubit
                elif operation.name in ['CX', 'cx']:
                    qubit0 = qureg[operation.qubits[0]]
                    qubit1 = qureg[operation.qubits[1]]
                    CX | (qubit0, qubit1)
                elif operation.name in ['id', 'u0']:
                    pass
                # Check if measure
                elif operation.name == 'measure':
                    qubit_index = operation.qubits[0]
                    qubit = qureg[qubit_index]
                    clbit = operation.memory[0]
                    Measure | qubit
                    bit = 1 << clbit
                    self._classical_state = (
                        self._classical_state & (~bit)) | (int(qubit)
                                                           << clbit)
                # Check if reset
                elif operation.name == 'reset':
                    qubit = operation.qubits[0]
                    raise ProjectQSimulatorError('Reset operation not yet implemented '
                                                 'for ProjectQ C++ backend')
                # Check if snapshot
                elif operation.name == 'snapshot':
                    eng.flush()
                    location = str(operation.params[0])
                    statevector = np.array(eng.backend.cheat()[1], dtype=complex)

                    formatted_state = [[x.real, x.imag] for x in statevector]
                    if location in snapshots:
                        snapshots[location]['statevector'].append(formatted_state)
                    else:
                        snapshots[location] = {'statevector': [formatted_state]}
                elif operation.name == 'barrier':
                    pass
                else:
                    backend = self._configuration.backend_name
                    err_msg = '{0} encountered unrecognized operation "{1}"'
                    raise ProjectQSimulatorError(err_msg.format(backend,
                                                                operation.name))

            # Before the program terminates, all the qubits must be measured,
            # including those that have not been measured by the circuit.
            # Otherwise ProjectQ throws an exception about qubits in superposition.
            for ind in list(range(self._number_of_qubits)):
                qubit = qureg[ind]
                Measure | qubit
            eng.flush()
            # Turn classical_state (int) into bit string
            state = format(self._classical_state, 'b')
            outcomes.append(state.zfill(self._number_of_clbits))

        # Return the results
        counts = dict(Counter(outcomes))
        data = {'counts': _format_result(counts, cl_reg_nbits)}
        if snapshots != {}:
            data['snapshots'] = snapshots
        if self._shots == 1:
            data['classical_state'] = self._classical_state
        end = time.time()

        # Calculate creg_sizes
        pre_creg_sizes = {}
        for clbit_label in circuit.header.clbit_labels:
            if clbit_label[0] in pre_creg_sizes:
                pre_creg_sizes[clbit_label[0]] += 1
            else:
                pre_creg_sizes[clbit_label[0]] = 1
        creg_sizes = []
        for clbit_label in pre_creg_sizes:
            creg_sizes.append([clbit_label, pre_creg_sizes[clbit_label]])

        return {'header': {'name': circuit.header.name,
                           'memory_slots': circuit.header.memory_slots,
                           'creg_sizes': creg_sizes},
                'seed': self._seed,
                'shots': self._shots,
                'data': data,
                'status': 'DONE',
                'success': True,
                'time_taken': (end-start)}

    def _validate(self, qobj):
        if qobj.config.shots == 1:
            warnings.warn('The behavior of getting statevector from simulators '
                          'by setting shots=1 is deprecated and has been removed '
                          'for this simulator. '
                          'Use the local_statevector_simulator instead, or place '
                          'explicit snapshot instructions.',
                          DeprecationWarning)
        for circ in qobj.experiments:
            if 'measure' not in [op.name for
                                 op in circ.instructions]:
                logger.warning("no measurements in circuit '%s', "
                               "classical register will remain all zeros.", circ.header.name)
        return


def _get_register_specs(bit_labels):
    """
    Get the number and size of unique registers from bit_labels list with an
    iterator of register_name:size pairs.

    Args:
        bit_labels (list): this list is of the form::

            [['reg1', 0], ['reg1', 1], ['reg2', 0]]

            which indicates a register named "reg1" of size 2
            and a register named "reg2" of size 1. This is the
            format of classic and quantum bit labels in qobj
            header.
    Yields:
        tuple: pairs of (register_name, size)
    """
    iterator = itertools.groupby(bit_labels, operator.itemgetter(0))
    for register_name, sub_it in iterator:
        yield register_name, max(ind[1] for ind in sub_it) + 1


def _format_result(counts, cl_reg_nbits):
    """Format the result bit string.

    This formats the result bit strings to Qiskit standards.

    Args:
        counts (dict): dictionary of counts e.g. {'1111': 1000, '0000':5}
        cl_reg_nbits (list): total amount of bits in classical register
    Returns:
        dict: dictionary keys are reversed and given in hexadecimal.
    """
    fcounts = {}
    for key, value in counts.items():
        new_key = key[-cl_reg_nbits[0]:]
        fcounts[str(hex(int(new_key, 2)))] = value
    return fcounts
