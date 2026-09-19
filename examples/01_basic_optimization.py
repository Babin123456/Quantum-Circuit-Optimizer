"""
Example 01: Basic Circuit Optimization & Gate Cancellation
-----------------------------------------------------------
Demonstrates:
1. Creating a circuit with redundant gates (H-H, X-X, CX-CX cancellation).
2. Optimizing using QuantumOptimizer across different levels (0, 1, 2, 3).
3. Viewing depth and gate count reductions.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from qiskit import QuantumCircuit
from quantum_optimizer import QuantumOptimizer, compare_circuits


def main():
    print("==================================================================")
    print("Example 01: Basic Optimization & Gate Cancellation")
    print("==================================================================")

    # 1. Create a 3-qubit circuit with deliberate redundancy
    qc = QuantumCircuit(3, 3)
    qc.h(0)
    qc.h(0)            # H * H = I (Redundant pair, cancels!)
    qc.x(1)
    qc.x(1)            # X * X = I (Redundant pair, cancels!)
    qc.cx(0, 1)
    qc.cx(0, 1)        # CX * CX = I (Redundant pair, cancels!)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.barrier()
    qc.measure([0, 1, 2], [0, 1, 2])

    print("\n--- Unoptimized Circuit ---")
    print(qc.draw(output="text"))
    print(f"Original Depth: {qc.depth()}")
    print(f"Original Gate Count: {sum(qc.count_ops().values())}")

    # 2. Run QuantumOptimizer across levels
    optimizer = QuantumOptimizer()
    comparison = optimizer.compare_levels(qc)

    print("\n--- Optimization Level Comparison ---")
    print(f"{'Level':<8} | {'Depth':<8} | {'Total Gates':<12} | {'2Q Gates':<10}")
    print("-" * 46)
    for lvl, data in comparison.items():
        print(f"Level {lvl:<2} | {data['depth']:<8} | {data['total_gates']:<12} | {data['2q_gates']:<10}")

    # 3. Take Level 2 optimized circuit and show detailed metrics
    opt_qc = comparison[2]["circuit"]
    print("\n--- Optimized Circuit (Level 2) ---")
    print(opt_qc.draw(output="text"))

    metrics = compare_circuits(qc, opt_qc)
    print("\n--- Detailed Reduction Metrics ---")
    print(f"Depth Reduction:      {metrics['depth_reduction_pct']}%")
    print(f"Gate Count Reduction: {metrics['gate_reduction_pct']}%")
    print(f"Est. Hardware Fidelity: {metrics['orig_estimated_hardware_fidelity']*100:.2f}% -> {metrics['opt_estimated_hardware_fidelity']*100:.2f}%")
    print("==================================================================")


if __name__ == "__main__":
    main()
