"""
Example 05: Master Unified Transpiler Function
-----------------------------------------------
Demonstrates calling `transpile_circuit(...)` directly with ANY quantum circuit
of N qubits and N arbitrary gates.
Runs through the exact 8-stage pipeline:
  Logical Circuit -> DAG -> Fusion -> Cancellation -> Commutation ->
  Decomposition -> Qubit Mapping -> SABRE Routing -> Final Optimize -> Hardware Circuit
Outputs:
- ASCII Circuit before and after
- Step-by-step console logs
- Depth and Gate count reductions
- OpenQASM 2.0 & 3.0 files
- Quantum Machines QUAM configuration skeleton
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from qiskit import QuantumCircuit
from quantum_optimizer import transpile_circuit


def main():
    print("==================================================================")
    print("Example 05: Unified 8-Stage Quantum Transpiler Function")
    print("==================================================================")

    # 1. Create an arbitrary circuit from user research specification
    # Has multi-qubit Toffoli, rotations, and adjacent redundant pairs
    num_qubits = 4
    qc = QuantumCircuit(num_qubits)

    # Stage demo gates:
    qc.u(np.pi / 2, 0, np.pi, 0)
    qc.h(2)
    qc.cx(1, 2)
    qc.tdg(2)
    qc.cx(0, 2)
    qc.t(2)
    qc.cx(1, 2)
    qc.tdg(2)
    qc.cx(0, 2)
    qc.t(1)
    qc.t(2)
    qc.cx(0, 1)
    qc.h(2)
    qc.t(0)
    qc.tdg(1)
    qc.cx(0, 1)

    # Add redundant cancellation pairs from User Image 3
    qc.u(np.pi, 0, np.pi, 2)
    qc.u(np.pi, 0, np.pi, 2)  # Cancels! U*U = I

    # Add distant interaction requiring SABRE routing
    qc.cx(0, 3)

    print("\n--- Input User Circuit (Logical N Gates) ---")
    print(qc.draw(output="text"))

    # 2. Define a linear physical coupling architecture: 0 <-> 1 <-> 2 <-> 3
    coupling_edges = [[0, 1], [1, 2], [2, 3]]

    # 3. Call the master unified transpiler function!
    optimized_circuit, metrics = transpile_circuit(
        circuit=qc,
        coupling_map=coupling_edges,
        export_qasm=True,
        qasm_filename="output/master_transpiled_circuit",
        generate_quam=True,
        verbose=True,
    )

    print("\n--- Final Hardware-Compliant Circuit ---")
    print(optimized_circuit.draw(output="text"))

    print("\nAll pipeline stages applied successfully:")
    for stage in metrics["pipeline_stages_applied"]:
        print(f"  ✔ {stage}")

    print("\nExported artifacts:")
    print(f"  📄 OpenQASM 2.0: {metrics['qasm2_exported_to']}")
    print(f"  📄 OpenQASM 3.0: {metrics['qasm3_exported_to']}")
    print(f"  📄 QUAM Skeleton Qubits Configured: {metrics['quam_skeleton']['num_qubits']}")
    print("==================================================================")


if __name__ == "__main__":
    main()
