import pytest
from qiskit import QuantumCircuit
from quantum_optimizer import DAGAnalyzer


def test_dag_properties():
    """Test basic node counting and depth via DAG."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    analyzer = DAGAnalyzer(qc)
    assert analyzer.depth == 2
    assert analyzer.num_op_nodes == 2
    assert analyzer.num_nodes > 2  # Includes input/output wire nodes


def test_critical_path():
    """Test critical path extraction."""
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.x(2)  # Parallel, shorter path

    analyzer = DAGAnalyzer(qc)
    critical_path = analyzer.get_critical_path()
    assert len(critical_path) == 2
    assert critical_path[0]["name"] == "h"
    assert critical_path[1]["name"] == "cx"


def test_parallelism_score():
    """Test circuit parallelism calculation."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.h(1)  # Perfect parallel layer

    analyzer = DAGAnalyzer(qc)
    # Depth = 1, Op nodes = 2, Qubits = 2 -> Parallelism = 2 / (1 * 2) = 1.0
    assert analyzer.depth == 1
    assert analyzer.get_parallelism_score() == 1.0
