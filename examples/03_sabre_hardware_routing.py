"""
Example 03: Hardware Coupling Map & SABRE SWAP Routing
------------------------------------------------------
Demonstrates:
1. Creating an unconstrained logical circuit requiring non-adjacent 2-qubit gates.
2. Defining a linear 1D hardware architecture (Q0 <-> Q1 <-> Q2 <-> Q3 <-> Q4).
3. Using SABRE (SWAP-Based Bidirectional heuristic) to insert optimal SWAP gates.
4. Verifying hardware constraint satisfaction and inspecting routing overhead.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from qiskit import QuantumCircuit
from quantum_optimizer import SABRERouter


def main():
    print("==================================================================")
    print("Example 03: Hardware Topology & SABRE SWAP Routing")
    print("==================================================================")

    # 1. Define a 5-qubit linear hardware topology
    num_qubits = 5
    coupling_map = SABRERouter.create_linear_coupling_map(num_qubits)
    print(f"\nTarget Hardware Topology: Linear Chain of {num_qubits} Qubits")
    print("Allowed Connections: 0 <-> 1 <-> 2 <-> 3 <-> 4")

    # 2. Build a logical circuit requiring interactions between distant qubits
    # E.g. CX between Q0 and Q4 (distance 4 on linear chain!)
    qc = QuantumCircuit(num_qubits)
    qc.h(0)
    qc.cx(0, 4)   # Long distance! Requires multiple SWAPs
    qc.cx(1, 3)   # Distance 2! Requires 1 SWAP
    qc.cx(2, 4)   # Distance 2! Requires 1 SWAP
    qc.cx(0, 2)   # Distance 2! Requires 1 SWAP

    print("\n--- Logical Circuit (Before Routing) ---")
    print(qc.draw(output="text"))

    # Verify if original circuit meets hardware connectivity
    is_valid_before = SABRERouter.check_connectivity_satisfaction(qc, coupling_map)
    print(f"Meets Linear Hardware Constraints Before Routing? {is_valid_before}")

    # 3. Apply SABRE Routing
    router = SABRERouter(coupling_map)
    routed_qc, stats = router.route_circuit(qc, optimization_level=2)

    print("\n--- Routed Circuit (Physical Execution Ready) ---")
    print(routed_qc.draw(output="text"))

    # Verify after routing
    is_valid_after = SABRERouter.check_connectivity_satisfaction(routed_qc, coupling_map)
    print(f"Meets Linear Hardware Constraints After Routing? {is_valid_after}")

    print("\n--- SABRE Routing Overhead Statistics ---")
    print(f"Original Depth:      {stats['original_depth']}")
    print(f"Routed Depth:        {stats['routed_depth']}")
    print(f"Original 2Q Gates:   {stats['original_2q_gates']}")
    print(f"Routed 2Q Gates:     {stats['routed_2q_gates']}")
    print(f"SWAP Gates Inserted: {stats['swaps_inserted']}")
    print(f"Extra 2Q Gates:      {stats['extra_2q_gates']}")
    print("==================================================================")


if __name__ == "__main__":
    main()
