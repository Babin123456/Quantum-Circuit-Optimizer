"""
Custom DAG (Directed Acyclic Graph) Circuit Implementation.
Built entirely in pure Python without reliance on third-party graph compilers.
Tracks:
- Operation nodes (gates)
- Qubit wire dependencies
- Predecessor and successor node relationships
- Topological ordering and critical paths
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, deque
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction, Qubit, Clbit


class DAGNode:
    """Represents a discrete node in the quantum DAG."""

    def __init__(self, node_id: int, node_type: str, op_name: str, qubits: List[int], params: Optional[List[float]] = None):
        """
        Args:
            node_id: Unique integer identifier.
            node_type: 'op' (gate/operation), 'in' (wire input), 'out' (wire output).
            op_name: Name of the gate (e.g., 'h', 'x', 'cx', 'rz') or wire name.
            qubits: List of qubit integer indices this operation acts on.
            params: Parameters (for parameterized rotations like rz, rx, u).
        """
        self.node_id = node_id
        self.node_type = node_type
        self.op_name = op_name
        self.qubits = list(qubits)
        self.params = list(params) if params is not None else []

    def __repr__(self) -> str:
        if self.node_type == "op":
            p_str = f"({', '.join(f'{p:.3f}' for p in self.params)})" if self.params else ""
            return f"Node_{self.node_id}:{self.op_name}{p_str}{self.qubits}"
        return f"Node_{self.node_id}:{self.node_type}_{self.op_name}"


class CustomDAG:
    """
    Directed Acyclic Graph representation of a quantum circuit.
    Nodes are gates; directed edges represent dependency along specific qubit wires.
    """

    def __init__(self, num_qubits: int = 0, num_clbits: int = 0):
        self.num_qubits = num_qubits
        self.num_clbits = num_clbits
        self._next_node_id = 0
        self.nodes: Dict[int, DAGNode] = {}
        
        # Graph adjacency: node_id -> dict(neighbor_id -> list of wire indices)
        self._successors: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._predecessors: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        
        # Wire boundaries: wire_index -> (in_node_id, out_node_id)
        self.wire_in: Dict[int, int] = {}
        self.wire_out: Dict[int, int] = {}

        # Initialize input/output wire nodes
        for q in range(num_qubits):
            in_node = self._create_node("in", f"q[{q}]", [q])
            out_node = self._create_node("out", f"q[{q}]", [q])
            self.wire_in[q] = in_node.node_id
            self.wire_out[q] = out_node.node_id
            self._add_edge(in_node.node_id, out_node.node_id, q)

    def _create_node(self, node_type: str, op_name: str, qubits: List[int], params: Optional[List[float]] = None) -> DAGNode:
        node = DAGNode(self._next_node_id, node_type, op_name, qubits, params)
        self.nodes[self._next_node_id] = node
        self._next_node_id += 1
        return node

    def _add_edge(self, u: int, v: int, wire: int) -> None:
        self._successors[u][v].append(wire)
        self._predecessors[v][u].append(wire)

    def _remove_edge(self, u: int, v: int, wire: Optional[int] = None) -> None:
        if wire is None:
            if v in self._successors[u]:
                del self._successors[u][v]
            if u in self._predecessors[v]:
                del self._predecessors[v][u]
        else:
            if v in self._successors[u] and wire in self._successors[u][v]:
                self._successors[u][v].remove(wire)
                if not self._successors[u][v]:
                    del self._successors[u][v]
            if u in self._predecessors[v] and wire in self._predecessors[v][u]:
                self._predecessors[v][u].remove(wire)
                if not self._predecessors[v][u]:
                    del self._predecessors[v][u]

    def add_op_node(self, op_name: str, qubits: List[int], params: Optional[List[float]] = None) -> DAGNode:
        """
        Append an operation node at the end of each participating qubit wire.
        """
        node = self._create_node("op", op_name, qubits, params)
        for q in qubits:
            # The current predecessor of wire_out[q] on wire q is the last op
            preds = [pred for pred, wires in self._predecessors[self.wire_out[q]].items() if q in wires]
            last_op_id = preds[0] if preds else self.wire_in[q]

            # Rewire: last_op -> new_node -> wire_out
            self._remove_edge(last_op_id, self.wire_out[q], q)
            self._add_edge(last_op_id, node.node_id, q)
            self._add_edge(node.node_id, self.wire_out[q], q)

        return node

    def remove_op_node(self, node_id: int) -> None:
        """
        Remove an operation node and splice its incoming and outgoing wires together.
        """
        node = self.nodes.get(node_id)
        if not node or node.node_type != "op":
            return

        for q in node.qubits:
            # Find the predecessor on wire q
            preds = [p for p, wires in self._predecessors[node_id].items() if q in wires]
            succs = [s for s, wires in self._successors[node_id].items() if q in wires]

            pred_id = preds[0] if preds else None
            succ_id = succs[0] if succs else None

            if pred_id is not None and succ_id is not None:
                self._remove_edge(pred_id, node_id, q)
                self._remove_edge(node_id, succ_id, q)
                self._add_edge(pred_id, succ_id, q)

        del self.nodes[node_id]
        if node_id in self._successors:
            del self._successors[node_id]
        if node_id in self._predecessors:
            del self._predecessors[node_id]

    def op_nodes(self) -> List[DAGNode]:
        """Return all gate operation nodes in the DAG."""
        return [node for node in self.nodes.values() if node.node_type == "op"]

    def topological_op_nodes(self) -> List[DAGNode]:
        """Return all operation nodes sorted by topological order."""
        in_degree = {nid: sum(len(w) for w in self._predecessors[nid].values()) for nid in self.nodes}
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        ordered_ops = []

        while queue:
            curr = queue.popleft()
            node = self.nodes[curr]
            if node.node_type == "op":
                ordered_ops.append(node)

            for succ, wires in list(self._successors[curr].items()):
                in_degree[succ] -= len(wires)
                if in_degree[succ] == 0:
                    queue.append(succ)

        return ordered_ops

    def depth(self) -> int:
        """Compute the critical path depth of the DAG operations."""
        dist = {nid: 0 for nid in self.nodes}
        for node in self.topological_op_nodes():
            nid = node.node_id
            pred_max = max([dist[p] for p in self._predecessors[nid]] or [0])
            dist[nid] = pred_max + 1

        out_nodes = [self.wire_out[q] for q in range(self.num_qubits)]
        return max([max([dist[p] for p in self._predecessors[out]] or [0]) for out in out_nodes] or [0])

    def get_wire_successor(self, node_id: int, wire: int) -> Optional[DAGNode]:
        """Find the immediate downstream node on a specific qubit wire."""
        succs = [s for s, wires in self._successors[node_id].items() if wire in wires]
        return self.nodes[succs[0]] if succs else None

    @classmethod
    def from_circuit(cls, circuit: QuantumCircuit) -> "CustomDAG":
        """Convert a Qiskit QuantumCircuit into our CustomDAG."""
        dag = cls(num_qubits=circuit.num_qubits, num_clbits=circuit.num_clbits)
        for instruction in circuit.data:
            op = instruction.operation
            # Skip barriers for cleaner optimization processing
            if op.name in ["barrier"]:
                continue
            qubit_indices = [circuit.find_bit(q).index for q in instruction.qubits]
            params = [float(p) for p in op.params] if hasattr(op, "params") else []
            dag.add_op_node(op.name, qubit_indices, params)
        return dag

    def to_circuit(self) -> QuantumCircuit:
        """Reconstruct a Qiskit QuantumCircuit from the CustomDAG in topological order."""
        qc = QuantumCircuit(self.num_qubits, self.num_clbits)
        for node in self.topological_op_nodes():
            name = node.op_name
            q = node.qubits
            p = node.params

            if name == "h":
                qc.h(q[0])
            elif name == "x":
                qc.x(q[0])
            elif name == "y":
                qc.y(q[0])
            elif name == "z":
                qc.z(q[0])
            elif name == "s":
                qc.s(q[0])
            elif name == "sdg":
                qc.sdg(q[0])
            elif name == "t":
                qc.t(q[0])
            elif name == "tdg":
                qc.tdg(q[0])
            elif name == "sx":
                qc.sx(q[0])
            elif name == "rz":
                qc.rz(p[0], q[0])
            elif name == "rx":
                qc.rx(p[0], q[0])
            elif name == "ry":
                qc.ry(p[0], q[0])
            elif name == "u":
                qc.u(p[0], p[1], p[2], q[0])
            elif name == "cx":
                qc.cx(q[0], q[1])
            elif name == "cz":
                qc.cz(q[0], q[1])
            elif name == "swap":
                qc.swap(q[0], q[1])
            elif name == "ccx":
                qc.ccx(q[0], q[1], q[2])
            elif name == "cswap":
                qc.cswap(q[0], q[1], q[2])
            elif name == "measure":
                # If measuring, default to map q[0] -> c[0]
                qc.measure(q[0], q[0])
            else:
                # Generic fallback if gate has custom constructor
                try:
                    getattr(qc, name)(*p, *q)
                except Exception:
                    pass
        return qc
