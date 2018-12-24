# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Provider for local ProjectQ backends."""

from qiskit.providers import BaseProvider
from qiskit.providers.providerutils import filter_backends

from .statevector_simulator_projectq import StatevectorSimulatorProjectQ
from .qasm_simulator_projectq import QasmSimulatorProjectQ


class ProjectQProvider(BaseProvider):
    """Provider for ProjectQ backends."""
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        # Populate the list of local ProjectQ backends.
        self._backends = [StatevectorSimulatorProjectQ(provider=self),
                          QasmSimulatorProjectQ(provider=self)]

    def get_backend(self, name=None, **kwargs):
        return super().get_backend(name=name, **kwargs)

    def backends(self, name=None, filters=None, **kwargs):
        # pylint: disable=arguments-differ
        backends = self._backends
        if name:
            backends = [backend for backend in backends if backend.name() == name]

        return filter_backends(backends, filters=filters, **kwargs)

    def __str__(self):
        return 'ProjectQProvider'
