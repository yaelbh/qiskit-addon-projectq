# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Example showing how to use the ProjectQ Provider at level 0 (novice).

This example shows the most basic way to user the ProjectQ Provider. It builds some circuits
and runs them on both the statevector and qasm simulators.
"""

from qiskit_addon_projectq import ProjectQProvider
from qiskit import execute, QuantumCircuit, ClassicalRegister, QuantumRegister

ProjectQ = ProjectQProvider()

# Create a Quantum and Classical Register.
qubit_reg = QuantumRegister(2)
clbit_reg = ClassicalRegister(2)

# making first circuit: bell state
qc1 = QuantumCircuit(qubit_reg, clbit_reg)
qc1.h(qubit_reg[0])
qc1.cx(qubit_reg[0], qubit_reg[1])

# making another circuit: superpositions
qc2 = QuantumCircuit(qubit_reg, clbit_reg)
qc2.h(qubit_reg)

# setting up the backend
print("(ProjectQ Backends)")
print(ProjectQ.backends())

# running the statevector simulator
statevector_job = execute([qc1, qc2], ProjectQ.get_backend('projectq_statevector_simulator'))
statevector_result = statevector_job.result()

# show the results
print("Stevector simulator:")
print(statevector_result.get_statevector(qc1))
print(statevector_result.get_statevector(qc2))

# running the qasm simulator
qc1.measure(qubit_reg, clbit_reg)
qc2.measure(qubit_reg, clbit_reg)
qasm_job = execute([qc1, qc2], ProjectQ.get_backend('projectq_qasm_simulator'), shots=100)
qasm_result = qasm_job.result()

# show the results
print("Qasm simulator:")
print(qasm_result.get_counts(qc1))
print(qasm_result.get_counts(qc2))
