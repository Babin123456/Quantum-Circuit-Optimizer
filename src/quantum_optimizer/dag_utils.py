"""
DAG (Directed Acyclic Graph) Circuit Analysis utilities.
Enables graph-based inspection of quantum circuits:
- Topological ordering
- Critical path identification
- Circuit parallelism calculation
- Gate dependency tracing
"""

from typing import List, Dict, Any, Tuple
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit, DAGOpNode, DAGInNode, DAGOutNode


class DAGAnalyzer:
    """
    Analyzer for quantum circuit DAG representations.
    Provides methods to query gate dependencies, critical paths, and topological layers.
    """

    def __init__(self, circuit_or_dag: Any):
        """
        Initialize the analyzer with either a QuantumCircuit or a DAGCircuit.

        Args:
            circuit_or_dag: QuantumCircuit or DAGCircuit instance.
        """
        if isinstance(circuit_or_dag, QuantumCircuit):
            self.circuit = circuit_or_dag
            self.dag = circuit_to_dag(circuit_or_dag)
        elif isinstance(circuit_or_dag, DAGCircuit):
            self.dag = circuit_or_dag
            self.circuit = dag_to_circuit(circuit_or_dag)
        else:
            raise TypeError("Expected QuantumCircuit or DAGCircuit instance.")

    @property
    def num_nodes(self) -> int:
        """Total number of nodes (including input/output wire nodes)."""
        return len(list(self.dag.nodes()))

    @property
    def num_op_nodes(self) -> int:
        """Number of operation (gate) nodes."""
        return len(self.dag.op_nodes())

    @property
    def depth(self) -> int:
        """Circuit depth computed via DAG longest path."""
        return self.dag.depth()

    def get_op_node_summary(self) -> List[Dict[str, Any]]:
        """
        Extract structured details for every operation node in topological order.

        Returns:
            List of dictionaries with name, qubits, params, and wire dependencies.
        """
        summary = []
        for node in self.dag.topological_op_nodes():
            summary.append({
                "name": node.op.name,
                "qubits": [self.circuit.find_bit(q).index for q in node.qargs],
                "params": list(node.op.params),
                "num_qubits": len(node.qargs),
            })
        return summary

    def get_critical_path(self) -> List[Dict[str, Any]]:
        """
        Find the longest path (critical path) through the DAG operations.

        Returns:
            List of operation node summaries along the critical path.
        """
        longest_path_nodes = self.dag.longest_path()
        critical_ops = []
        for node in longest_path_nodes:
            if isinstance(node, DAGOpNode):
                critical_ops.append({
                    "name": node.op.name,
                    "qubits": [self.circuit.find_bit(q).index for q in node.qargs],
                    "params": list(node.op.params),
                })
        return critical_ops

    def get_parallelism_score(self) -> float:
        """
        Calculate circuit parallelism: (total operations) / (depth * num_qubits).
        A score of 1.0 means every qubit executes an operation at every time step.

        Returns:
            Parallelism factor between 0.0 and 1.0.
        """
        if self.depth == 0 or self.circuit.num_qubits == 0:
            return 0.0
        return self.num_op_nodes / (self.depth * self.circuit.num_qubits)

    def print_topological_layers(self) -> None:
        """Print the operations present in each discrete layer of the DAG."""
        layers = list(self.dag.layers())
        print(f"=== Circuit DAG Layers (Total Depth: {len(layers)}) ===")
        for idx, layer in enumerate(layers):
            ops = [f"{n.op.name}({[self.circuit.find_bit(q).index for q in n.qargs]})" for n in layer["graph"].op_nodes()]
            print(f"  Layer {idx:02d}: {', '.join(ops) if ops else '[Empty wire step]'}")
