# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Example showing how to use the ProjectQ Provider at level 1 (intermediate).

This example shows how an intermediate user interacts with the ProjectQ Provider. It builds some circuits
and compiles them. It makes a qobj object which is a container to be 
run on a backend. The same qobj can run on many backends (as shown). It is the
user responsibility to make sure it can be run. This is useful when you want to compare the same
circuits on different backends or change the compile parameters.
"""

import time

from qiskit_addon_projectq import ProjectQProvider
from qiskit import compile, QuantumCircuit, ClassicalRegister, QuantumRegister, BasicAer
from qiskit.providers import JobStatus

ProjectQ = ProjectQProvider()
    
# Create a quantum and classical register.
qubit_reg = QuantumRegister(2, name='q')
clbit_reg = ClassicalRegister(2, name='c')

# Making first circuit: Bell state
qc1 = QuantumCircuit(qubit_reg, clbit_reg, name="bell")
qc1.h(qubit_reg[0])
qc1.cx(qubit_reg[0], qubit_reg[1])

# Making another circuit: superpositions
qc2 = QuantumCircuit(qubit_reg, clbit_reg, name="superposition")
qc2.h(qubit_reg)

# Setting up the backend
print("(ProjectQ Backends)")
for backend in ProjectQ.backends():
    print(backend.status())

# Compiling the qobj for the projectq backends
qobj = {}
qobj['statevector'] = compile([qc1, qc2], backend=BasicAer.get_backend('qasm_simulator'), shots=100)
qc1.measure(qubit_reg, clbit_reg)
qc2.measure(qubit_reg, clbit_reg)
qobj['qasm'] = compile([qc1, qc2], backend=BasicAer.get_backend('qasm_simulator'), shots=100)

backends = {'statevector': {'ProjectQ': ProjectQ.get_backend('projectq_statevector_simulator'),
                            'BasicAer': BasicAer.get_backend('statevector_simulator')},
            'qasm': {'ProjectQ': ProjectQ.get_backend('projectq_qasm_simulator'),
                     'BasicAer': BasicAer.get_backend('qasm_simulator')}}

# Running four backends on two qobj
jobs = {}
for mode in ['statevector', 'qasm']:
    jobs[mode] = {}
    for backend in ['ProjectQ', 'BasicAer']:
        jobs[mode][backend] = backends[mode][backend].run(qobj[mode])

lapse = 0
interval = 0.01
while any(jobs[mode][backend].status() != JobStatus.DONE for mode in ['statevector', 'qasm'] for backend in ['ProjectQ', 'BasicAer']):
    print('Status at {} milliseconds'.format(1000 * interval * lapse))
    for mode in ['statevector', 'qasm']:
        for backend in ['ProjectQ', 'BasicAer']:
            print(backend + " " + mode + " simulator: ", jobs[mode][backend].status())
    time.sleep(interval)
    lapse += 1

# Show the results
for mode in ['statevector', 'qasm']:
    for backend in ['ProjectQ', 'BasicAer']:
        result = jobs[mode][backend].result()
        print(backend + " " + mode + " simulator:")
        for circ in [qc1, qc2]:
            if mode == 'statevector':
                print(result.get_statevector(circ))
            else:
                print(result.get_counts(circ))



