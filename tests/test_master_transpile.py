import pytest
import numpy as np
from qiskit import QuantumCircuit
from quantum_optimizer import transpile_circuit


def test_transpile_circuit_pipeline():
    """Verify master transpile_circuit executes all 8 stages and returns valid output."""
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.h(0)  # Cancels
    qc.cx(0, 1)
    qc.cx(0, 2)  # Distant interaction on linear chain

    coupling_edges = [[0, 1], [1, 2]]

    hardware_qc, metrics = transpile_circuit(
        circuit=qc,
        coupling_map=coupling_edges,
        export_qasm=False,
    )

    assert hardware_qc is not None
    assert "pipeline_stages_applied" in metrics
    assert len(metrics["pipeline_stages_applied"]) == 8
    # H-H should be eliminated
    assert not any(inst.operation.name == "h" and hardware_qc.find_bit(inst.qubits[0]).index == 0 for inst in hardware_qc.data if len(inst.qubits) == 1)


def test_transpile_circuit_with_qasm_export(tmp_path):
    """Verify master transpile_circuit exports OpenQASM 2 and 3 files correctly."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    base_path = str(tmp_path / "test_export")
    hardware_qc, metrics = transpile_circuit(
        circuit=qc,
        coupling_map=[[0, 1]],
        export_qasm=True,
        qasm_filename=base_path,
        generate_quam=True,
    )

    import os
    assert os.path.exists(f"{base_path}.qasm")
    assert os.path.exists(f"{base_path}.qasm3")
    assert "quam_skeleton" in metrics
