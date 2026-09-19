"""
Core Quantum Circuit Optimizer module.
Provides high-level optimization pipeline with configurable stages:
- Level 0: No optimization (direct translation)
- Level 1: Light optimization (gate cancellation, 1Q fusion)
- Level 2: Medium optimization (commutation analysis, SABRE placement)
- Level 3: Heavy optimization (deep 2Q unitaries, SABRE routing, global phase)
"""

from typing import Optional, List, Dict, Any, Union
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager, StagedPassManager, Target, CouplingMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler.passes import (
    InverseCancellation,
    Optimize1qGatesDecomposition,
    CommutativeCancellation,
    ConsolidateBlocks,
    UnitarySynthesis,
    Depth,
    Size,
)


class QuantumOptimizer:
    """
    High-level quantum circuit optimizer supporting preset levels and custom passes.

    Attributes:
        optimization_level (int): Optimization level from 0 to 3.
        basis_gates (list): Target basis gates (e.g., ['sx', 'rz', 'cx']).
        coupling_map (CouplingMap): Hardware connectivity graph.
    """

    DEFAULT_BASIS_GATES = ["sx", "rz", "cx", "id"]

    def __init__(
        self,
        optimization_level: int = 2,
        basis_gates: Optional[List[str]] = None,
        coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None,
        backend: Optional[Any] = None,
    ):
        """
        Initialize the Quantum Optimizer.

        Args:
            optimization_level: 0 (none), 1 (light), 2 (medium/SABRE), 3 (deep/resynthesis)
            basis_gates: List of basis gate names (default: ['sx', 'rz', 'cx', 'id'])
            coupling_map: Hardware coupling map (directed or undirected graph)
            backend: Optional Qiskit backend or Target for hardware-aware compilation
        """
        if not (0 <= optimization_level <= 3):
            raise ValueError(f"Optimization level must be between 0 and 3, got {optimization_level}")

        self.optimization_level = optimization_level
        self.basis_gates = basis_gates or self.DEFAULT_BASIS_GATES
        self.backend = backend

        if isinstance(coupling_map, list):
            self.coupling_map = CouplingMap(coupling_map)
        else:
            self.coupling_map = coupling_map

    def optimize(
        self,
        circuit: QuantumCircuit,
        optimization_level: Optional[int] = None,
        seed_transpiler: Optional[int] = 42,
    ) -> QuantumCircuit:
        """
        Transpile and optimize a quantum circuit using Qiskit preset pass managers.

        Args:
            circuit: QuantumCircuit to optimize.
            optimization_level: Override instance optimization level if specified.
            seed_transpiler: Random seed for stochastic algorithms like SABRE layout/routing.

        Returns:
            Optimized QuantumCircuit.
        """
        level = self.optimization_level if optimization_level is None else optimization_level

        # If backend is provided, use target; else use basis_gates and coupling_map
        if self.backend is not None:
            pm = generate_preset_pass_manager(
                optimization_level=level,
                backend=self.backend,
                seed_transpiler=seed_transpiler,
            )
        else:
            pm = generate_preset_pass_manager(
                optimization_level=level,
                basis_gates=self.basis_gates,
                coupling_map=self.coupling_map,
                seed_transpiler=seed_transpiler,
            )

        optimized_circuit = pm.run(circuit)
        return optimized_circuit

    def apply_custom_cancellation_pipeline(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Apply explicit gate cancellation passes (CXCancellation, 1Q consolidation, CommutativeCancellation).
        Useful for inspecting intermediate transformation steps cleanly.

        Args:
            circuit: QuantumCircuit to simplify.

        Returns:
            Simplified QuantumCircuit.
        """
        from qiskit.circuit.library import CXGate
        pm = PassManager([
            Optimize1qGatesDecomposition(basis=self.basis_gates),
            InverseCancellation([(CXGate(), CXGate())]),
            CommutativeCancellation(basis_gates=self.basis_gates),
            Optimize1qGatesDecomposition(basis=self.basis_gates),
        ])
        return pm.run(circuit)

    def compare_levels(
        self,
        circuit: QuantumCircuit,
        levels: Optional[List[int]] = None,
        seed_transpiler: int = 42,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Run optimizations across different levels (0, 1, 2, 3) and return comparison metrics.

        Args:
            circuit: QuantumCircuit to test.
            levels: List of levels to compare (default: [0, 1, 2, 3]).
            seed_transpiler: Random seed for consistency.

        Returns:
            Dictionary mapping level -> {depth, total_gates, 2q_gates, circuit}.
        """
        if levels is None:
            levels = [0, 1, 2, 3]

        results = {}
        for lvl in levels:
            opt_circ = self.optimize(circuit, optimization_level=lvl, seed_transpiler=seed_transpiler)
            ops = opt_circ.count_ops()
            two_q_gates = sum(count for name, count in ops.items() if opt_circ.find_bit(opt_circ.qubits[0]) and name in ["cx", "cz", "ecr", "swap"])
            
            # More general: count operations that act on >= 2 qubits
            two_q_count = sum(1 for instruction in opt_circ.data if len(instruction.qubits) >= 2)

            results[lvl] = {
                "depth": opt_circ.depth(),
                "total_gates": sum(ops.values()),
                "2q_gates": two_q_count,
                "ops": dict(ops),
                "circuit": opt_circ,
            }

        return results
