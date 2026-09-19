"""
Custom SABRE (SWAP-Based Bidirectional Heuristic Search) Routing Pass.
Pure Python implementation of the SABRE hardware routing algorithm:
1. Calculates all-pairs shortest path distance matrix on the coupling map.
2. Maintains a Front Layer (F) of executable gates and an Extended Lookahead Window (E).
3. Evaluates SWAP candidates using the heuristic:
   Cost(S) = (1/|F|) * sum D(pi(u), pi(v)) + W * (1/|E|) * sum D(pi(u), pi(v))
4. Applies decay factors to prevent SWAP loops and livelocks.
5. Emits a valid routed circuit meeting physical coupling constraints.
"""

from typing import List, Dict, Set, Tuple, Optional
import numpy as np
from collections import deque
from ..base import TransformationPass
from ..dag import CustomDAG, DAGNode


class CustomSABRERouterPass(TransformationPass):
    """
    Hardware routing pass implementing the SABRE heuristic search from scratch.
    """

    def __init__(
        self,
        coupling_edges: List[List[int]],
        lookahead_weight: float = 0.5,
        lookahead_size: int = 20,
        decay_factor: float = 0.001,
    ):
        """
        Args:
            coupling_edges: Physical processor adjacency list [[0, 1], [1, 2], ...].
            lookahead_weight: Weight W of the extended lookahead window (typically 0.5).
            lookahead_size: Maximum number of gates in lookahead window E.
            decay_factor: Penalty multiplier applied to recently used physical qubits.
        """
        super().__init__()
        self.coupling_edges = coupling_edges
        self.lookahead_weight = lookahead_weight
        self.lookahead_size = lookahead_size
        self.decay_factor = decay_factor

        # Determine total physical qubits and build distance matrix
        self.num_physical_qubits = max([max(edge) for edge in coupling_edges]) + 1
        self.adj = self._build_adjacency_graph(self.num_physical_qubits, coupling_edges)
        self.dist = self._compute_all_pairs_distance(self.num_physical_qubits, self.adj)

    def name(self) -> str:
        return "CustomSABRERouterPass"

    @staticmethod
    def _build_adjacency_graph(n: int, edges: List[List[int]]) -> Dict[int, Set[int]]:
        adj = {i: set() for i in range(n)}
        for u, v in edges:
            adj[u].add(v)
            adj[v].add(u)
        return adj

    @staticmethod
    def _compute_all_pairs_distance(n: int, adj: Dict[int, Set[int]]) -> np.ndarray:
        """Compute shortest path distance matrix via Breadth-First Search (BFS)."""
        dist = np.full((n, n), fill_value=999, dtype=int)
        for src in range(n):
            dist[src, src] = 0
            queue = deque([src])
            while queue:
                curr = queue.popleft()
                for neighbor in adj[curr]:
                    if dist[src, neighbor] == 999:
                        dist[src, neighbor] = dist[src, curr] + 1
                        queue.append(neighbor)
        return dist

    def run(self, dag: CustomDAG) -> CustomDAG:
        """
        Route the CustomDAG gates to satisfy physical coupling constraints.
        """
        # Physical mapping: logical qubit -> physical qubit
        # Initially identity mapping: pi(l) = l
        layout = {q: q for q in range(dag.num_qubits)}
        inv_layout = {p: l for l, p in layout.items()}

        decay = {p: 1.0 for p in range(self.num_physical_qubits)}

        # Extract topological gate list
        ops = dag.topological_op_nodes()
        routed_dag = CustomDAG(num_qubits=self.num_physical_qubits, num_clbits=dag.num_clbits)

        # Predecessor counts for DAG traversal
        # We track remaining gates per logical qubit
        remaining_gates = list(ops)

        while remaining_gates:
            # 1. Find Front Layer F: gates whose predecessors have all been executed
            # In a linear scan, find first gates on each qubit
            front_layer: List[DAGNode] = []
            active_qubits: Set[int] = set()

            for gate in remaining_gates:
                if not any(q in active_qubits for q in gate.qubits):
                    front_layer.append(gate)
                    for q in gate.qubits:
                        active_qubits.add(q)

            # 2. Check if any gate in Front Layer can execute immediately
            executable_gate = None
            for gate in front_layer:
                if len(gate.qubits) == 1:
                    executable_gate = gate
                    break
                elif len(gate.qubits) == 2:
                    p0 = layout[gate.qubits[0]]
                    p1 = layout[gate.qubits[1]]
                    if self.dist[p0, p1] <= 1:
                        executable_gate = gate
                        break

            if executable_gate is not None:
                # Emit executable gate mapped to physical qubits
                phys_qubits = [layout[q] for q in executable_gate.qubits]
                routed_dag.add_op_node(executable_gate.op_name, phys_qubits, executable_gate.params)

                # Reset decay for these physical qubits
                for p in phys_qubits:
                    decay[p] = 1.0

                remaining_gates.remove(executable_gate)
                continue

            # 3. No front gate is executable -> Must insert a SWAP!
            # Generate candidate SWAPs on physical edges adjacent to active front layer qubits
            candidate_swaps: Set[Tuple[int, int]] = set()
            front_2q_gates = [g for g in front_layer if len(g.qubits) == 2]

            for g in front_2q_gates:
                p0 = layout[g.qubits[0]]
                p1 = layout[g.qubits[1]]
                for nbr in self.adj[p0]:
                    candidate_swaps.add((min(p0, nbr), max(p0, nbr)))
                for nbr in self.adj[p1]:
                    candidate_swaps.add((min(p1, nbr), max(p1, nbr)))

            # 4. Score each SWAP candidate using SABRE cost function
            best_swap = None
            best_cost = float("inf")

            # Extended lookahead window E (gates immediately after Front Layer)
            extended_layer = [g for g in remaining_gates if g not in front_layer and len(g.qubits) == 2][:self.lookahead_size]

            for (p_u, p_v) in candidate_swaps:
                # Speculatively apply SWAP
                trial_layout = dict(layout)
                l_u = inv_layout.get(p_u)
                l_v = inv_layout.get(p_v)

                if l_u is not None:
                    trial_layout[l_u] = p_v
                if l_v is not None:
                    trial_layout[l_v] = p_u

                # Front layer cost
                cost_f = sum(self.dist[trial_layout[g.qubits[0]], trial_layout[g.qubits[1]]] for g in front_2q_gates)
                cost_f /= len(front_2q_gates)

                # Extended layer cost
                cost_e = 0.0
                if extended_layer:
                    cost_e = sum(self.dist[trial_layout[g.qubits[0]], trial_layout[g.qubits[1]]] for g in extended_layer)
                    cost_e /= len(extended_layer)

                total_cost = (cost_f + self.lookahead_weight * cost_e) * max(decay[p_u], decay[p_v])

                if total_cost < best_cost:
                    best_cost = total_cost
                    best_swap = (p_u, p_v)

            # Fallback if no candidate found
            if best_swap is None:
                g = front_2q_gates[0]
                p0 = layout[g.qubits[0]]
                best_swap = (p0, list(self.adj[p0])[0])

            # Apply best SWAP
            p_a, p_b = best_swap
            routed_dag.add_op_node("swap", [p_a, p_b])

            # Update layout mappings
            l_a = inv_layout.get(p_a)
            l_b = inv_layout.get(p_b)
            if l_a is not None:
                layout[l_a] = p_b
            if l_b is not None:
                layout[l_b] = p_a

            if l_a is not None and l_b is not None:
                inv_layout[p_a], inv_layout[p_b] = l_b, l_a
            elif l_a is not None:
                inv_layout[p_b] = l_a
                del inv_layout[p_a]
            elif l_b is not None:
                inv_layout[p_a] = l_b
                del inv_layout[p_b]

            # Update decay factors
            decay[p_a] += self.decay_factor
            decay[p_b] += self.decay_factor

        return routed_dag
