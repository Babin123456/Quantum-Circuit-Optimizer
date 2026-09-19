"""
Example 02: Toffoli Decomposition & Redundancy Cancellation
------------------------------------------------------------
Demonstrates:
1. Building the canonical 6-CNOT Toffoli decomposition (as shown in user image 3).
2. Introducing redundant rotation/X-gates at the end (U(pi, 0, pi) * U(pi, 0, pi) = I).
3. Analyzing the DAG structure before and after optimization.
4. Verifying unitary equivalence and gate reduction.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from quantum_optimizer import Decomposer, QuantumOptimizer, DAGAnalyzer, compare_circuits


def main():
    print("==================================================================")
    print("Example 02: Toffoli Gate Decomposition & Gate Cancellation")
    print("==================================================================")

    # 1. Build circuit modeled after user Image 3
    print("\n1. Constructing Decomposed Toffoli Circuit with Redundancies...")
    raw_circuit = Decomposer.build_redundant_toffoli_test_circuit()
    print(raw_circuit.draw(output="text"))

    # 2. DAG Analysis on raw circuit
    print("\n2. Inspecting DAG Representation of Decomposed Circuit...")
    dag_raw = DAGAnalyzer(raw_circuit)
    print(f"Total DAG Nodes:     {dag_raw.num_nodes}")
    print(f"Operation Gate Nodes: {dag_raw.num_op_nodes}")
    print(f"Circuit Depth:        {dag_raw.depth}")
    print(f"Parallelism Factor:   {dag_raw.get_parallelism_score():.3f}")

    critical_path = dag_raw.get_critical_path()
    print(f"Critical Path Length: {len(critical_path)} gates")
    print("Gates on Critical Path:", " -> ".join(op["name"] for op in critical_path[:8]) + "...")

    # 3. Optimize circuit to eliminate redundant gates and fuse single-qubit rotations
    print("\n3. Running Optimization (Level 2)...")
    optimizer = QuantumOptimizer(optimization_level=2)
    opt_circuit = optimizer.optimize(raw_circuit)
    print(opt_circuit.draw(output="text"))

    # 4. Compare Metrics
    metrics = compare_circuits(raw_circuit, opt_circuit)
    print("\n--- Optimization Results ---")
    print(f"Raw Depth:        {metrics['original_depth']} -> Optimized: {metrics['optimized_depth']} ({metrics['depth_reduction_pct']}% reduction)")
    print(f"Total Gates:      {metrics['original_total_gates']} -> Optimized: {metrics['optimized_total_gates']} ({metrics['gate_reduction_pct']}% reduction)")
    print(f"2-Qubit CX Gates: {metrics['original_2q_gates']} -> Optimized: {metrics['optimized_2q_gates']}")
    if metrics["statevector_fidelity"] is not None:
        print(f"Statevector Fidelity (Equivalence): {metrics['statevector_fidelity']:.6f} (1.0 = exact match)")
    print("==================================================================")


if __name__ == "__main__":
    main()
