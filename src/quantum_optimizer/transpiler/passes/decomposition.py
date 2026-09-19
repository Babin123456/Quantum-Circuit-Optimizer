"""
Custom Gate Decomposition Pass.
Decomposes composite and multi-qubit gates into native elementary basis sets:
1. SWAP -> 3 CX gates:
   SWAP(a, b) = CX(a, b) * CX(b, a) * CX(a, b)
2. Toffoli (CCX) -> 6 CX + 7 T/Tdg + 2 H (canonical Barenco et al. construction)
3. CZ -> H(target) * CX(control, target) * H(target)
"""

from typing import List
from ..base import TransformationPass
from ..dag import CustomDAG, DAGNode


class CustomDecompositionPass(TransformationPass):
    """
    Pass that pattern-matches composite gates and replaces them with elementary basis decompositions.
    """

    def name(self) -> str:
        return "CustomDecompositionPass"

    def run(self, dag: CustomDAG) -> CustomDAG:
        new_dag = CustomDAG(num_qubits=dag.num_qubits, num_clbits=dag.num_clbits)

        for node in dag.topological_op_nodes():
            name = node.op_name.lower()
            q = node.qubits
            p = node.params

            if name == "swap":
                # Decompose SWAP into 3 CX gates
                new_dag.add_op_node("cx", [q[0], q[1]])
                new_dag.add_op_node("cx", [q[1], q[0]])
                new_dag.add_op_node("cx", [q[0], q[1]])

            elif name == "cz":
                # Decompose CZ into H + CX + H on target
                new_dag.add_op_node("h", [q[1]])
                new_dag.add_op_node("cx", [q[0], q[1]])
                new_dag.add_op_node("h", [q[1]])

            elif name == "ccx":
                # Canonical 6-CX Toffoli decomposition
                # Controls: q[0], q[1]; Target: q[2]
                new_dag.add_op_node("h", [q[2]])
                new_dag.add_op_node("cx", [q[1], q[2]])
                new_dag.add_op_node("tdg", [q[2]])
                new_dag.add_op_node("cx", [q[0], q[2]])
                new_dag.add_op_node("t", [q[2]])
                new_dag.add_op_node("cx", [q[1], q[2]])
                new_dag.add_op_node("tdg", [q[2]])
                new_dag.add_op_node("cx", [q[0], q[2]])
                new_dag.add_op_node("t", [q[1]])
                new_dag.add_op_node("t", [q[2]])
                new_dag.add_op_node("cx", [q[0], q[1]])
                new_dag.add_op_node("h", [q[2]])
                new_dag.add_op_node("t", [q[0]])
                new_dag.add_op_node("tdg", [q[1]])
                new_dag.add_op_node("cx", [q[0], q[1]])

            else:
                # Retain other gates as-is
                new_dag.add_op_node(node.op_name, node.qubits, node.params)

        return new_dag
