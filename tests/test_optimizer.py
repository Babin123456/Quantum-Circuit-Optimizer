import pytest
import numpy as np
from qiskit import QuantumCircuit
from quantum_optimizer import QuantumOptimizer, compare_circuits


def test_redundant_gate_cancellation():
    """Test that consecutive self-inverse gates (H-H, X-X, CX-CX) cancel."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.h(0)  # Cancels
    qc.x(1)
    qc.x(1)  # Cancels
    qc.cx(0, 1)
    qc.cx(0, 1)  # Cancels
    qc.h(0)

    optimizer = QuantumOptimizer(optimization_level=1)
    opt_qc = optimizer.optimize(qc)

    # After cancellation, only single H gate (decomposed to RZ-SX-RZ) on q0 remains
    ops = opt_qc.count_ops()
    assert ops.get("cx", 0) == 0
    assert opt_qc.depth() <= 3


def test_level_comparison():
    """Test multi-level optimization comparison dictionary."""
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)

    optimizer = QuantumOptimizer()
    results = optimizer.compare_levels(qc, levels=[0, 1, 2])

    assert 0 in results
    assert 1 in results
    assert 2 in results
    assert results[0]["depth"] >= 1
