"""
Custom Rotation Fusion Pass.
Scans CustomDAG for adjacent single-qubit rotation gates along the same axis:
- Rz(theta1) * Rz(theta2) = Rz(theta1 + theta2)
- Rx(theta1) * Rx(theta2) = Rx(theta1 + theta2)
- Ry(theta1) * Ry(theta2) = Ry(theta1 + theta2)

If (theta1 + theta2) mod 2*pi ~= 0, both are eliminated completely.
Otherwise, merges into a single rotation node.
"""

import numpy as np
from typing import Set, Tuple
from ..base import TransformationPass
from ..dag import CustomDAG, DAGNode


class CustomRotationFusionPass(TransformationPass):
    """
    Pass that fuses consecutive rotation gates around the same axis.
    """

    ROTATION_GATES = {"rz", "rx", "ry"}
    ATOL = 1e-7

    def name(self) -> str:
        return "CustomRotationFusionPass"

    def run(self, dag: CustomDAG) -> CustomDAG:
        changed = True
        while changed:
            changed = False
            topological_nodes = dag.topological_op_nodes()

            for node in topological_nodes:
                if node.node_id not in dag.nodes:
                    continue

                if node.op_name in self.ROTATION_GATES and len(node.qubits) == 1 and node.params:
                    wire = node.qubits[0]
                    succ = dag.get_wire_successor(node.node_id, wire)

                    if succ and succ.node_type == "op" and succ.op_name == node.op_name and succ.qubits == node.qubits and succ.params:
                        # Combine angles modulo 2*pi
                        combined_angle = (node.params[0] + succ.params[0]) % (2 * np.pi)
                        
                        # Normalize to [-pi, pi]
                        if combined_angle > np.pi:
                            combined_angle -= 2 * np.pi

                        if abs(combined_angle) < self.ATOL or abs(abs(combined_angle) - 2 * np.pi) < self.ATOL:
                            # Fused angle is effectively zero (Identity) -> eliminate both!
                            dag.remove_op_node(node.node_id)
                            dag.remove_op_node(succ.node_id)
                        else:
                            # Mutate first node to new angle and remove second node
                            node.params = [float(combined_angle)]
                            dag.remove_op_node(succ.node_id)

                        changed = True
                        break

        return dag
