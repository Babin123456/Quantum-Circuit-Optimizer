import pytest
from qiskit import QuantumCircuit
from quantum_optimizer import SABRERouter


def test_sabre_routing_satisfies_linear_coupling():
    """Verify that routing resolves non-adjacent interactions on a 1D linear chain."""
    num_qubits = 4
    coupling_map = SABRERouter.create_linear_coupling_map(num_qubits)

    # Distant 2-qubit gate (Q0 to Q3)
    qc = QuantumCircuit(num_qubits)
    qc.cx(0, 3)

    assert not SABRERouter.check_connectivity_satisfaction(qc, coupling_map)

    router = SABRERouter(coupling_map)
    routed_qc, stats = router.route_circuit(qc, optimization_level=2)

    assert SABRERouter.check_connectivity_satisfaction(routed_qc, coupling_map)
    assert stats["routed_depth"] >= stats["original_depth"]
