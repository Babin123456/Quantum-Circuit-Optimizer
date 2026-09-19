import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from quantum_optimizer import Decomposer


def test_toffoli_standard_decomposition():
    """Verify that canonical Toffoli decomposition has exactly 6 CX gates and matches CCX unitary."""
    decomp_qc = Decomposer.build_toffoli_standard_decomposition()
    ops = decomp_qc.count_ops()

    # 6 CX gates required
    assert ops.get("cx", 0) == 6

    # Verify unitary equivalence to ideal CCX gate
    ideal_qc = QuantumCircuit(3)
    ideal_qc.ccx(0, 1, 2)

    u_ideal = Operator(ideal_qc)
    u_decomp = Operator(decomp_qc)

    # Unitaries are equivalent up to global phase
    assert u_ideal.equiv(u_decomp)


def test_decompose_to_basis():
    """Verify decomposition into custom basis gates."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    decomposer = Decomposer(target_basis=["rz", "sx", "cx"])
    basis_qc = decomposer.decompose_to_basis(qc)

    ops = basis_qc.count_ops()
    assert "h" not in ops
    assert "sx" in ops or "rz" in ops
