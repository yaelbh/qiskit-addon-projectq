# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Interface to ProjectQ C++ quantum circuit simulator.
"""

import logging
import uuid

from qiskit.providers.models import BackendConfiguration
from qiskit.qobj import QobjInstruction
from qiskit.result import Result

from qiskit_addon_projectq import QasmSimulatorProjectQ
from .projectqjob import ProjectQJob
from .projectqsimulatorerror import ProjectQSimulatorError

logger = logging.getLogger(__name__)


class StatevectorSimulatorProjectQ(QasmSimulatorProjectQ):
    """ProjectQ C++ statevector simulator"""

    DEFAULT_CONFIGURATION = {
        'backend_name': 'projectq_statevector_simulator',
        'backend_version': '0.1.0',
        'url': 'https://github.com/QISKit/qiskit-addon-projectq',
        'simulator': True,
        'local': True,
        'description': 'A ProjectQ C++ statevector simulator for qobj files',
        'basis_gates': ['u1', 'u2', 'u3', 'cx', 'id', 'h', 's', 't'],
        'memory': True,
        'n_qubits': 30,
        'conditional': False,
        'max_shots': 1,
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
                          'statevector': array([sqrt(2)/2, 0, 0, sqrt(2)/2], dtype=object),
                        },
                        'status': 'DONE'
                        }]
        """

        self._validate(qobj)
        final_state_key = '32767'  # Internal key for final state snapshot
        # Add final snapshots to circuits
        for circuit in qobj.experiments:
            circuit.instructions.append(QobjInstruction.from_dict(
                {'name': 'snapshot', 'params': [final_state_key]}))
        qobj.config.shots = 1
        result_dict = super()._run_job(job_id, qobj).to_dict()
        # Extract final state snapshot and move to 'statevector' data field
        for res in result_dict['results']:
            snapshots = res['data']['snapshots']
            # Pop off final snapshot added above
            final_state = snapshots.pop(final_state_key, None)
            final_state = final_state['statevector'][0]
            # Add final state to results data
            res['data']['statevector'] = final_state
            # Remove snapshot dict if empty
            if snapshots == {}:
                res['data'].pop('snapshots', None)

        return Result.from_dict(result_dict)

    def _validate(self, qobj):
        """Semantic validations of the qobj which cannot be done via schemas.
        Some of these may later move to backend schemas.

        Args:
            qobj (Qobj): Qobj structure.

        Raises:
            ProjectQSimulatorError: if unsupported operations passed, these are measure and reset
        """
        for circuit in qobj.experiments:
            for operator in circuit.instructions:
                if operator.name in ('measure', 'reset'):
                    raise ProjectQSimulatorError(
                        "In circuit {}: statevector simulator does not support measure or "
                        "reset.".format(circuit.header.name))
