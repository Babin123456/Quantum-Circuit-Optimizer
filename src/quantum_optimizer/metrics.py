"""
Circuit Metrics and Fidelity Analysis Module.
Calculates depth reduction, gate count differences, estimated hardware fidelity,
and statevector fidelity verification via Qiskit Aer simulation.
"""

from typing import Dict, Any, Optional
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, state_fidelity


class CircuitMetrics:
    """Stores and calculates comparative metrics between two quantum circuits."""

    def __init__(self, original: QuantumCircuit, optimized: QuantumCircuit):
        self.original = original
        self.optimized = optimized

    def calculate_summary(self) -> Dict[str, Any]:
        """
        Compute comparative metrics between the original and optimized circuits.

        Returns:
            Dictionary of metrics including depths, gate counts, and reduction percentages.
        """
        orig_ops = self.original.count_ops()
        opt_ops = self.optimized.count_ops()

        orig_depth = self.original.depth()
        opt_depth = self.optimized.depth()

        orig_total = sum(orig_ops.values())
        opt_total = sum(opt_ops.values())

        orig_2q = sum(count for name, count in orig_ops.items() if name in ["cx", "cz", "ecr", "swap"])
        opt_2q = sum(count for name, count in opt_ops.items() if name in ["cx", "cz", "ecr", "swap"])

        depth_reduction = ((orig_depth - opt_depth) / orig_depth * 100) if orig_depth > 0 else 0.0
        gate_reduction = ((orig_total - opt_total) / orig_total * 100) if orig_total > 0 else 0.0
        two_q_reduction = ((orig_2q - opt_2q) / orig_2q * 100) if orig_2q > 0 else 0.0

        return {
            "original_depth": orig_depth,
            "optimized_depth": opt_depth,
            "depth_reduction_pct": round(depth_reduction, 2),
            "original_total_gates": orig_total,
            "optimized_total_gates": opt_total,
            "gate_reduction_pct": round(gate_reduction, 2),
            "original_2q_gates": orig_2q,
            "optimized_2q_gates": opt_2q,
            "two_q_reduction_pct": round(two_q_reduction, 2),
            "original_ops": dict(orig_ops),
            "optimized_ops": dict(opt_ops),
        }


def calculate_estimated_fidelity(
    circuit: QuantumCircuit,
    f_1q: float = 0.9995,
    f_2q: float = 0.990,
    f_readout: float = 0.985,
) -> float:
    """
    Calculate rough estimated circuit fidelity based on component error product:
    F_total = (F_1q ^ N_1q) * (F_2q ^ N_2q) * (F_readout ^ N_qubits)

    Args:
        circuit: QuantumCircuit to evaluate.
        f_1q: Average single-qubit gate fidelity (default: 0.9995 = 99.95%).
        f_2q: Average two-qubit gate fidelity (default: 0.990 = 99.0%).
        f_readout: Average readout fidelity per qubit (default: 0.985 = 98.5%).

    Returns:
        Estimated total circuit success probability (0.0 to 1.0).
    """
    ops = circuit.count_ops()
    num_2q = sum(count for name, count in ops.items() if name in ["cx", "cz", "ecr", "swap"])
    num_total = sum(count for name, count in ops.items() if name not in ["barrier", "measure"])
    num_1q = max(0, num_total - num_2q)
    num_qubits = circuit.num_qubits

    f_circuit = (f_1q ** num_1q) * (f_2q ** num_2q) * (f_readout ** num_qubits)
    return float(np.clip(f_circuit, 0.0, 1.0))


def compare_circuits(original: QuantumCircuit, optimized: QuantumCircuit) -> Dict[str, Any]:
    """
    Convenience function to compare two circuits and compute state fidelity if circuit size allows.

    Args:
        original: Unoptimized circuit.
        optimized: Transpiled/optimized circuit.

    Returns:
        Summary metrics dictionary.
    """
    metrics = CircuitMetrics(original, optimized).calculate_summary()

    # Estimate hardware fidelities
    metrics["orig_estimated_hardware_fidelity"] = round(calculate_estimated_fidelity(original), 4)
    metrics["opt_estimated_hardware_fidelity"] = round(calculate_estimated_fidelity(optimized), 4)

    # Statevector fidelity check for smaller circuits (<= 14 qubits)
    if original.num_qubits == optimized.num_qubits and original.num_qubits <= 14:
        try:
            # Check without measurements
            orig_no_meas = original.remove_final_measurements(inplace=False)
            opt_no_meas = optimized.remove_final_measurements(inplace=False)

            sv_orig = Statevector.from_instruction(orig_no_meas)
            sv_opt = Statevector.from_instruction(opt_no_meas)
            state_fid = state_fidelity(sv_orig, sv_opt)
            metrics["statevector_fidelity"] = float(state_fid)
        except Exception:
            metrics["statevector_fidelity"] = None
    else:
        metrics["statevector_fidelity"] = None

    return metrics
