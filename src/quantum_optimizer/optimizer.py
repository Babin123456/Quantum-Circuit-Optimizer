from typing import Optional, List, Dict, Any, Union
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from .transpiler import (
    CustomPassManager,
    CustomGateCancellationPass,
    CustomRotationFusionPass,
    CustomCommutationPass,
    CustomDecompositionPass,
    CustomSABRERouterPass,
    CustomDAG,
)


class QuantumOptimizer:
    """
    High-level quantum circuit optimizer driven by our custom, from-scratch transpiler engine.
    Does not rely on Qiskit's internal transpiler passes.
    """

    DEFAULT_BASIS_GATES = ["sx", "rz", "cx", "id"]

    def __init__(
        self,
        optimization_level: int = 2,
        basis_gates: Optional[List[str]] = None,
        coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None,
        backend: Optional[Any] = None,
    ):
        if not (0 <= optimization_level <= 3):
            raise ValueError(f"Optimization level must be between 0 and 3, got {optimization_level}")

        self.optimization_level = optimization_level
        self.basis_gates = basis_gates or self.DEFAULT_BASIS_GATES
        self.backend = backend

        if isinstance(coupling_map, list):
            self.coupling_map = CouplingMap(coupling_map)
        else:
            self.coupling_map = coupling_map

    def build_custom_pass_manager(self, optimization_level: Optional[int] = None) -> CustomPassManager:
        """
        Construct a custom pass manager according to the requested optimization level.
        - Level 0: Direct decomposition (unrolling) without optimization.
        - Level 1: Decomposition + Inverse Gate Cancellation.
        - Level 2: Decomposition + Cancellation + Rotation Fusion + Commutation.
        - Level 3: Level 2 + SABRE hardware routing (if coupling map provided) + loop until fixed-point.
        """
        lvl = self.optimization_level if optimization_level is None else optimization_level
        pm = CustomPassManager()

        if lvl == 0:
            pm.append(CustomDecompositionPass())
        elif lvl == 1:
            pm.append(CustomDecompositionPass())
            pm.append(CustomGateCancellationPass())
        elif lvl == 2:
            pm.append(CustomDecompositionPass())
            pm.append(CustomCommutationPass())
            pm.append(CustomGateCancellationPass())
            pm.append(CustomRotationFusionPass())
            pm.append(CustomGateCancellationPass())
        elif lvl == 3:
            pm.append(CustomDecompositionPass())
            pm.append(CustomCommutationPass())
            pm.append(CustomGateCancellationPass())
            pm.append(CustomRotationFusionPass())
            pm.append(CustomGateCancellationPass())
            if self.coupling_map is not None:
                edges = [list(e) for e in self.coupling_map.get_edges()]
                pm.append(CustomSABRERouterPass(edges))
                pm.append(CustomDecompositionPass())
                pm.append(CustomGateCancellationPass())

        return pm

    def optimize(
        self,
        circuit: QuantumCircuit,
        optimization_level: Optional[int] = None,
        seed_transpiler: Optional[int] = 42,
    ) -> QuantumCircuit:
        """
        Optimize a quantum circuit using our custom transpiler pipeline.
        """
        pm = self.build_custom_pass_manager(optimization_level=optimization_level)
        return pm.run(circuit)

    def apply_custom_cancellation_pipeline(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Apply our custom cancellation and rotation fusion passes directly.
        """
        pm = CustomPassManager([
            CustomGateCancellationPass(),
            CustomRotationFusionPass(),
            CustomGateCancellationPass(),
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
