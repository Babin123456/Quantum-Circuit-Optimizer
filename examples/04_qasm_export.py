"""
Example 04: OpenQASM 2.0, OpenQASM 3.0, and QUAM Export
-------------------------------------------------------
Demonstrates:
1. Creating and optimizing a quantum circuit.
2. Exporting to OpenQASM 2.0 (compatible with standard simulators and IBM Quantum).
3. Exporting to OpenQASM 3.0 (modern standard with pulse/classical timing).
4. Generating a QUAM (Quantum Machines Architecture Model) configuration skeleton.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import json
from qiskit import QuantumCircuit
from quantum_optimizer import QuantumOptimizer, QASMExporter


def main():
    print("==================================================================")
    print("Example 04: OpenQASM & QUAM Export Pipeline")
    print("==================================================================")

    # 1. Build a simple Bell state + Toffoli circuit
    qc = QuantumCircuit(3, 3)
    qc.h(0)
    qc.cx(0, 1)
    qc.ccx(0, 1, 2)
    qc.barrier()
    qc.measure([0, 1, 2], [0, 1, 2])

    print("\n--- Original Circuit ---")
    print(qc.draw(output="text"))

    # 2. Optimize circuit to standard hardware basis
    optimizer = QuantumOptimizer(optimization_level=2)
    opt_qc = optimizer.optimize(qc)

    # 3. Export to OpenQASM 2.0
    print("\n--- Exporting to OpenQASM 2.0 ---")
    qasm2_str = QASMExporter.to_qasm2(opt_qc, filename="output/circuit_optimized.qasm")
    print(qasm2_str[:300] + "\n... [truncated] ...")
    print("Saved to: output/circuit_optimized.qasm")

    # 4. Export to OpenQASM 3.0
    print("\n--- Exporting to OpenQASM 3.0 ---")
    qasm3_str = QASMExporter.to_qasm3(opt_qc, filename="output/circuit_optimized.qasm3")
    print(qasm3_str[:300] + "\n... [truncated] ...")
    print("Saved to: output/circuit_optimized.qasm3")

    # 5. Generate QUAM skeleton configuration
    print("\n--- Generating QUAM Hardware Skeleton ---")
    quam_dict = QASMExporter.to_quam_skeleton(opt_qc, machine_name="ibm_heron_replica")
    print(json.dumps(quam_dict, indent=2)[:400] + "\n... [truncated] ...")
    print("==================================================================")


if __name__ == "__main__":
    main()
