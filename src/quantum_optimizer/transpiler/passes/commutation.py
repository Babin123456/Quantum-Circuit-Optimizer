"""
Custom Commutation Cancellation Pass.
Identifies gates that mathematically commute, sliding them past each other
to expose hidden cancellation opportunities.

Commutation Rules:
1. Z, Rz, S, T commute with CX on the CONTROL qubit.
2. X, Rx commute with CX on the TARGET qubit.
3. CX(c, t1) and CX(c, t2) commute (shared control).
4. CX(c1, t) and CX(c2, t) commute (shared target).
"""

from typing import Set
from ..base import TransformationPass
from ..dag import CustomDAG, DAGNode


class CustomCommutationPass(TransformationPass):
    """
    Pass that slides commuting gates forward along DAG wires to expose adjacent cancellations.
    """

    def name(self) -> str:
        return "CustomCommutationPass"

    def _commutes_1q_with_2q(self, op1q: DAGNode, op2q: DAGNode) -> bool:
        """Check if a 1-qubit gate commutes with a 2-qubit gate."""
        name1 = op1q.op_name.lower()
        name2 = op2q.op_name.lower()

        if name2 == "cx":
            ctrl = op2q.qubits[0]
            tgt = op2q.qubits[1]
            q = op1q.qubits[0]

            # Z-basis gates commute with CX control
            if q == ctrl and name1 in {"z", "rz", "s", "sdg", "t", "tdg"}:
                return True

            # X-basis gates commute with CX target
            if q == tgt and name1 in {"x", "rx"}:
                return True

        return False

    def run(self, dag: CustomDAG) -> CustomDAG:
        """
        Scan for commuting pairs: if op1 commutes with op2, and swapping them
        allows op1 to meet an identical gate downstream, swap their positions.
        """
        # Reconstruct circuit with commuting re-orderings
        # For simplicity and robust correctness, when an op1 commutes with op2,
        # we check if op2's downstream neighbor matches op1.
        circuit = dag.to_circuit()
        ops = list(circuit.data)
        n = len(ops)
        modified = False

        for i in range(n - 2):
            inst1 = ops[i]
            inst2 = ops[i + 1]
            inst3 = ops[i + 2]

            name1 = inst1.operation.name
            name2 = inst2.operation.name
            name3 = inst3.operation.name

            q1 = [circuit.find_bit(q).index for q in inst1.qubits]
            q2 = [circuit.find_bit(q).index for q in inst2.qubits]
            q3 = [circuit.find_bit(q).index for q in inst3.qubits]

            # Case: 1Q gate, then 2Q CX, then 1Q gate matching inst1
            if len(q1) == 1 and len(q2) == 2 and q1 == q3 and name1 == name3:
                node1 = DAGNode(0, "op", name1, q1)
                node2 = DAGNode(1, "op", name2, q2)
                if self._commutes_1q_with_2q(node1, node2):
                    # Swap inst1 and inst2 so inst1 meets inst3
                    ops[i], ops[i + 1] = ops[i + 1], ops[i]
                    modified = True

        if modified:
            from qiskit import QuantumCircuit
            new_qc = QuantumCircuit(circuit.num_qubits, circuit.num_clbits)
            for inst in ops:
                new_qc.append(inst)
            return CustomDAG.from_circuit(new_qc)

        return dag
