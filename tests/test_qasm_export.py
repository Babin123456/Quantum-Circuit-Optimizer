import os
import pytest
from qiskit import QuantumCircuit
from quantum_optimizer import QASMExporter


def test_qasm2_export(tmp_path):
    """Test exporting to OpenQASM 2.0 format."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    file_path = tmp_path / "test.qasm"
    qasm_str = QASMExporter.to_qasm2(qc, filename=str(file_path))

    assert "OPENQASM 2.0;" in qasm_str
    assert "cx" in qasm_str
    assert os.path.exists(file_path)


def test_qasm3_export(tmp_path):
    """Test exporting to OpenQASM 3.0 format."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    file_path = tmp_path / "test.qasm3"
    qasm_str = QASMExporter.to_qasm3(qc, filename=str(file_path))

    assert "OPENQASM 3" in qasm_str
    assert os.path.exists(file_path)


def test_quam_skeleton():
    """Test QUAM skeleton generation."""
    qc = QuantumCircuit(3)
    qc.h(0)

    quam_config = QASMExporter.to_quam_skeleton(qc, machine_name="test_qpu")
    assert quam_config["machine"] == "test_qpu"
    assert quam_config["num_qubits"] == 3
    assert "q0" in quam_config["qubits"]
