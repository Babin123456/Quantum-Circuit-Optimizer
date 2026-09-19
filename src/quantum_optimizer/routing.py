"""
Hardware Topology & SABRE Routing Module.
Handles mapping logical qubits to physical qubits and inserting SWAP gates
respecting quantum processor coupling maps using SABRE heuristics.
"""

from typing import List, Optional, Union, Tuple, Dict
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap, PassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler.passes import SabreLayout, SabreSwap


class SABRERouter:
    """
    SABRE (SWAP-Based Bidirectional Heuristic) Router and Topology Manager.
    Maps logical quantum circuits onto restricted physical connectivity graphs.
    """

    def __init__(self, coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None):
        """
        Initialize the SABRE router.

        Args:
            coupling_map: CouplingMap instance or list of edge pairs [[0, 1], [1, 2], ...].
        """
        if isinstance(coupling_map, list):
            self.coupling_map = CouplingMap(coupling_map)
        else:
            self.coupling_map = coupling_map

    @classmethod
    def create_linear_coupling_map(cls, num_qubits: int) -> CouplingMap:
        """
        Create a 1D linear chain coupling map: 0 <-> 1 <-> 2 <-> ... <-> N-1.

        Args:
            num_qubits: Number of qubits.

        Returns:
            Bidirectional CouplingMap.
        """
        edges = []
        for i in range(num_qubits - 1):
            edges.append([i, i + 1])
            edges.append([i + 1, i])
        return CouplingMap(edges)

    @classmethod
    def create_ring_coupling_map(cls, num_qubits: int) -> CouplingMap:
        """
        Create a 1D closed ring coupling map: 0 <-> 1 <-> ... <-> N-1 <-> 0.

        Args:
            num_qubits: Number of qubits.

        Returns:
            Bidirectional CouplingMap.
        """
        edges = []
        for i in range(num_qubits):
            edges.append([i, (i + 1) % num_qubits])
            edges.append([(i + 1) % num_qubits, i])
        return CouplingMap(edges)

    @classmethod
    def create_star_coupling_map(cls, num_qubits: int, center_qubit: int = 0) -> CouplingMap:
        """
        Create a star topology coupling map where all outer qubits connect to a central qubit.

        Args:
            num_qubits: Total qubits.
            center_qubit: Hub qubit index (default: 0).

        Returns:
            Bidirectional CouplingMap.
        """
        edges = []
        for i in range(num_qubits):
            if i != center_qubit:
                edges.append([center_qubit, i])
                edges.append([i, center_qubit])
        return CouplingMap(edges)

    def route_circuit(
        self,
        circuit: QuantumCircuit,
        coupling_map: Optional[CouplingMap] = None,
        optimization_level: int = 2,
        seed_transpiler: int = 42,
    ) -> Tuple[QuantumCircuit, Dict[str, int]]:
        """
        Route a circuit to satisfy the coupling map constraints using preset pass manager (SABRE).

        Args:
            circuit: Logical QuantumCircuit to route.
            coupling_map: Optional override coupling map.
            optimization_level: Optimization level (2 uses SabreLayout and SabreSwap).
            seed_transpiler: Random seed for deterministic SABRE heuristic.

        Returns:
            Tuple of (routed_circuit, routing_overhead_stats).
        """
        cmap = coupling_map or self.coupling_map
        if cmap is None:
            raise ValueError("A coupling map must be provided either at init or during route_circuit.")

        pm = generate_preset_pass_manager(
            optimization_level=optimization_level,
            coupling_map=cmap,
            seed_transpiler=seed_transpiler,
        )

        routed_qc = pm.run(circuit)

        # Calculate routing overhead
        original_ops = circuit.count_ops()
        routed_ops = routed_qc.count_ops()

        original_2q = sum(count for name, count in original_ops.items() if name in ["cx", "cz", "ecr", "swap"])
        routed_2q = sum(count for name, count in routed_ops.items() if name in ["cx", "cz", "ecr", "swap"])

        # In Qiskit, SWAPs may be decomposed into 3 CXs or retained as swap gates
        swap_count = routed_ops.get("swap", 0)
        extra_cx = max(0, routed_2q - original_2q)

        stats = {
            "original_depth": circuit.depth(),
            "routed_depth": routed_qc.depth(),
            "original_2q_gates": original_2q,
            "routed_2q_gates": routed_2q,
            "swaps_inserted": swap_count,
            "extra_2q_gates": extra_cx,
        }

        return routed_qc, stats

    @staticmethod
    def check_connectivity_satisfaction(circuit: QuantumCircuit, coupling_map: CouplingMap) -> bool:
        """
        Verify whether all 2-qubit gates in the circuit strictly adhere to the coupling map.

        Args:
            circuit: QuantumCircuit to check.
            coupling_map: Hardware coupling map.

        Returns:
            True if all 2-qubit interactions exist in coupling_map, False otherwise.
        """
        for instruction in circuit.data:
            if len(instruction.qubits) == 2:
                q0 = circuit.find_bit(instruction.qubits[0]).index
                q1 = circuit.find_bit(instruction.qubits[1]).index
                if not (coupling_map.graph.has_edge(q0, q1) or coupling_map.graph.has_edge(q1, q0)):
                    return False
        return True
