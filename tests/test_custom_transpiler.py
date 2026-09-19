import pytest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from quantum_optimizer.transpiler import (
    CustomDAG,
    CustomPassManager,
    CustomGateCancellationPass,
    CustomRotationFusionPass,
    CustomCommutationPass,
    CustomDecompositionPass,
    CustomSABRERouterPass,
)


def test_custom_dag_creation_and_reconstruction():
    """Verify converting QuantumCircuit to CustomDAG and back preserves unitary."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    dag = CustomDAG.from_circuit(qc)
    assert len(dag.op_nodes()) == 2
    assert dag.depth() == 2

    reconstructed_qc = dag.to_circuit()
    assert Operator(qc).equiv(Operator(reconstructed_qc))


def test_custom_gate_cancellation():
    """Verify custom cancellation pass eliminates self-inverses without Qiskit passes."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.h(0)  # Cancels
    qc.x(1)
    qc.x(1)  # Cancels
    qc.cx(0, 1)
    qc.cx(0, 1)  # Cancels
    qc.h(0)

    pm = CustomPassManager([CustomGateCancellationPass()])
    opt_qc = pm.run(qc)

    # Only single H on qubit 0 should remain
    assert len(opt_qc.data) == 1
    assert opt_qc.data[0].operation.name == "h"
    assert Operator(qc).equiv(Operator(opt_qc))


def test_custom_rotation_fusion():
    """Verify fusing Rz(pi/4) + Rz(pi/4) -> Rz(pi/2)."""
    qc = QuantumCircuit(1)
    qc.rz(np.pi / 4, 0)
    qc.rz(np.pi / 4, 0)

    pm = CustomPassManager([CustomRotationFusionPass()])
    fused_qc = pm.run(qc)

    assert len(fused_qc.data) == 1
    assert fused_qc.data[0].operation.name == "rz"
    assert np.isclose(fused_qc.data[0].operation.params[0], np.pi / 2)
    assert Operator(qc).equiv(Operator(fused_qc))


def test_custom_rotation_fusion_to_identity():
    """Verify Rz(pi/3) + Rz(-pi/3) cancels out to Identity."""
    qc = QuantumCircuit(1)
    qc.rz(np.pi / 3, 0)
    qc.rz(-np.pi / 3, 0)

    pm = CustomPassManager([CustomRotationFusionPass()])
    fused_qc = pm.run(qc)

    assert len(fused_qc.data) == 0


def test_custom_toffoli_decomposition():
    """Verify custom decomposition pass unrolls CCX into 6 CX + single-qubit gates."""
    qc = QuantumCircuit(3)
    qc.ccx(0, 1, 2)

    pm = CustomPassManager([CustomDecompositionPass()])
    decomp_qc = pm.run(qc)

    ops = decomp_qc.count_ops()
    assert ops.get("cx", 0) == 6
    assert ops.get("ccx", 0) == 0
    assert Operator(qc).equiv(Operator(decomp_qc))


def test_custom_sabre_routing_on_linear_chain():
    """Verify custom SABRE router places SWAPs so every CX is on adjacent physical qubits."""
    edges = [[0, 1], [1, 2], [2, 3]]  # 4-qubit line
    qc = QuantumCircuit(4)
    qc.cx(0, 3)  # Distance 3

    router = CustomSABRERouterPass(edges)
    pm = CustomPassManager([router])
    routed_qc = pm.run(qc)

    # Verify every 2-qubit gate in routed circuit is on a physical edge
    valid_edges = set((u, v) for u, v in edges) | set((v, u) for u, v in edges)
    for inst in routed_qc.data:
        if len(inst.qubits) == 2:
            q0 = routed_qc.find_bit(inst.qubits[0]).index
            q1 = routed_qc.find_bit(inst.qubits[1]).index
            assert (q0, q1) in valid_edges
