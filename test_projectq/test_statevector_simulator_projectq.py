# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,missing-docstring,broad-except

# Copyright 2018 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

from test.python.common import QiskitTestCase

import unittest
from qiskit import qasm, unroll, QuantumJob, execute, load_qasm_file
from qiskit_addon_projectq import StatevectorSimulatorProjectQ

from qiskit_addon_projectq import QasmSimulatorProjectQ
try:
    pq_simulator = QasmSimulatorProjectQ()
except Exception as err:
    _skip_class = True
else:
    _skip_class = False


@unittest.skipIf(_skip_class, 'Project Q C++ simulator unavailable')
class StatevectorSimulatorProjectQTest(QiskitTestCase):
    """Test ProjectQ C++ statevector simulator."""

    def setUp(self):
        self.qasm_filename = self._get_resource_path('qasm/simple.qasm')
        self.q_circuit = load_qasm_file(self.qasm_filename, name='example')
   
    def test_statevector_simulator_projectq(self):
        """Test final state vector for single circuit run."""
        result = execute(self.q_circuit, backend=StatevectorSimulatorProjectQ()).result()
        self.assertEqual(result.get_status(), 'COMPLETED')
        actual = result.get_statevector(self.q_circuit)

        # state is 1/sqrt(2)|00> + 1/sqrt(2)|11>, up to a global phase
        self.assertAlmostEqual((abs(actual[0]))**2, 1/2)
        self.assertEqual(actual[1], 0)
        self.assertEqual(actual[2], 0)
        self.assertAlmostEqual((abs(actual[3]))**2, 1/2)


if __name__ == '__main__':
    unittest.main()
