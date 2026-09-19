"""
Custom Gate Cancellation Pass.
Directly traverses the CustomDAG to identify and remove:
1. Self-inverse pairs on identical qubits:
   - H * H = I
   - X * X = I
   - Y * Y = I
   - Z * Z = I
   - CX * CX = I (acting on same control and target)
   - SWAP * SWAP = I
2. Inverse adjoint pairs:
   - S * Sdg = I, Sdg * S = I
   - T * Tdg = I, Tdg * T = I
"""

from typing import Set, Tuple
from ..base import TransformationPass
from ..dag import CustomDAG, DAGNode


class CustomGateCancellationPass(TransformationPass):
    """
    Pass that inspects consecutive operations along qubit wires in CustomDAG
    and removes inverse operation pairs cleanly.
    """

    SELF_INVERSE_1Q = {"h", "x", "y", "z"}
    SELF_INVERSE_2Q = {"cx", "cz", "swap"}
    ADJOINT_PAIRS = {
        ("s", "sdg"), ("sdg", "s"),
        ("t", "tdg"), ("tdg", "t"),
    }

    def name(self) -> str:
        return "CustomGateCancellationPass"

    def _are_inverse(self, node1: DAGNode, node2: DAGNode) -> bool:
        """Check if two consecutive nodes cancel out to identity."""
        if node1.qubits != node2.qubits:
            return False

        name1 = node1.op_name.lower()
        name2 = node2.op_name.lower()

        # 1-qubit self inverses (H-H, X-X, etc.)
        if len(node1.qubits) == 1 and name1 == name2 and name1 in self.SELF_INVERSE_1Q:
            return True

        # 2-qubit self inverses (CX-CX, CZ-CZ, SWAP-SWAP)
        if len(node1.qubits) == 2 and name1 == name2 and name1 in self.SELF_INVERSE_2Q:
            return True

        # Adjoint pairs (T-Tdg, S-Sdg)
        if (name1, name2) in self.ADJOINT_PAIRS:
            return True

        # Parameterized U gates: U(pi, 0, pi) * U(pi, 0, pi) = X * X = I
        if name1 == "u" and name2 == "u" and len(node1.params) == 3 and len(node2.params) == 3:
            import numpy as np
            # Check if both are X gates (theta=pi, phi=0, lam=pi)
            is_x1 = np.isclose(node1.params[0], np.pi) and np.isclose(node1.params[1], 0) and np.isclose(node1.params[2], np.pi)
            is_x2 = np.isclose(node2.params[0], np.pi) and np.isclose(node2.params[1], 0) and np.isclose(node2.params[2], np.pi)
            if is_x1 and is_x2:
                return True

        return False

    def run(self, dag: CustomDAG) -> CustomDAG:
        """
        Execute cancellation sweep over all wires until no more pairs can be canceled.
        """
        changed = True
        while changed:
            changed = False
            topological_nodes = dag.topological_op_nodes()
            nodes_to_delete: Set[int] = set()

            for node in topological_nodes:
                if node.node_id in nodes_to_delete or node.node_id not in dag.nodes:
                    continue

                # Check if all wires have the exact same downstream node
                primary_wire = node.qubits[0]
                succ = dag.get_wire_successor(node.node_id, primary_wire)

                if succ and succ.node_type == "op" and succ.node_id not in nodes_to_delete:
                    # For multi-qubit gates, verify succ is successor on ALL participating wires
                    if len(node.qubits) > 1:
                        all_match = all(dag.get_wire_successor(node.node_id, q) == succ for q in node.qubits)
                    else:
                        all_match = True

                    if all_match and self._are_inverse(node, succ):
                        nodes_to_delete.add(node.node_id)
                        nodes_to_delete.add(succ.node_id)
                        changed = True

            # Cleanly remove the canceled nodes from DAG
            for nid in nodes_to_delete:
                if nid in dag.nodes:
                    dag.remove_op_node(nid)

        return dag
