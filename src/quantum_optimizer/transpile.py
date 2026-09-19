"""
Master Transpiler Function Module.
Provides the primary unified function `transpile_circuit(...)` that implements
the exact 8-stage quantum transpilation pipeline:

  Logical Circuit (N gates)
             │
             ▼
            DAG
             │
             ▼
       ┌───────────┐
       │Gate Fusion│
       └─────┬─────┘
             ▼
      ┌────────────┐
      │Cancellation│
      └──────┬─────┘
             ▼
      ┌───────────┐
      │Commutation│
      └──────┬────┘
             ▼
     ┌─────────────┐
     │Decomposition│
     └───────┬─────┘
             ▼
     ┌─────────────┐
     │Qubit Mapping│
     └───────┬─────┘
             ▼
     ┌─────────────┐
     │SABRE Routing│
     └───────┬─────┘
             ▼
    ┌────────────────┐
    │ Final Optimize │
    └────────┬───────┘
             ▼
      Hardware Circuit -> OpenQASM 2.0 / 3.0 -> QUAM
"""

from typing import Optional, List, Dict, Any, Union, Tuple
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap

from .transpiler.dag import CustomDAG
from .transpiler.pass_manager import CustomPassManager
from .transpiler.passes.fusion import CustomRotationFusionPass
from .transpiler.passes.cancellation import CustomGateCancellationPass
from .transpiler.passes.commutation import CustomCommutationPass
from .transpiler.passes.decomposition import CustomDecompositionPass
from .transpiler.passes.sabre_router import CustomSABRERouterPass
from .metrics import compare_circuits, calculate_estimated_fidelity
from .qasm_export import QASMExporter


def transpile_circuit(
    circuit: QuantumCircuit,
    coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None,
    basis_gates: Optional[List[str]] = None,
    export_qasm: bool = False,
    qasm_filename: Optional[str] = None,
    generate_quam: bool = False,
    verbose: bool = False,
) -> Tuple[QuantumCircuit, Dict[str, Any]]:
    """
    Master from-scratch quantum transpiler function.
    Optimizes an arbitrary quantum circuit of N qubits and N gates through our 8-stage pipeline.

    Args:
        circuit: Input logical QuantumCircuit with any number of gates.
        coupling_map: Physical hardware connectivity (CouplingMap or list of edges [[0,1], [1,2], ...]).
                      If None, default to a linear chain coupling map covering circuit.num_qubits.
        basis_gates: Target hardware basis gate set (e.g., ['cx', 'rz', 'sx', 'x']).
        export_qasm: If True, exports optimized circuit to OpenQASM 2.0 & 3.0.
        qasm_filename: Optional filepath base to save the .qasm file.
        generate_quam: If True, generates a Quantum Machines QUAM architecture skeleton.
        verbose: If True, prints step-by-step progress through each transpiler stage.

    Returns:
        Tuple of (optimized_hardware_circuit, summary_metrics_dictionary).
    """
    if verbose:
        print("\n" + "=" * 70)
        print("🌌 STARTING QUANTUMFORGE 8-STAGE TRANSPILER PIPELINE")
        print("=" * 70)
        print(f"Input Circuit: {circuit.num_qubits} Qubits, {len(circuit.data)} Gates, Depth {circuit.depth()}")

    # -------------------------------------------------------------
    # Stage 1: Logical Circuit Sanitization & Baseline Recording
    # -------------------------------------------------------------
    num_qubits = circuit.num_qubits
    orig_depth = circuit.depth()
    orig_gate_count = len(circuit.data)

    # -------------------------------------------------------------
    # Stage 2: Convert Circuit to Directed Acyclic Graph (DAG)
    # -------------------------------------------------------------
    if verbose:
        print("[Stage 2] Constructing CustomDAG from Logical Circuit...")
    dag = CustomDAG.from_circuit(circuit)

    # -------------------------------------------------------------
    # Stage 3: Gate Fusion Pass (Continuous Rotation Merge)
    # Merges contiguous Rz(θ₁) + Rz(θ₂) -> Rz(θ₁ + θ₂)
    # -------------------------------------------------------------
    if verbose:
        print("[Stage 3] Applying Gate Fusion Pass (merging contiguous rotation angles)...")
    fusion_pass = CustomRotationFusionPass()
    dag = fusion_pass.run(dag)

    # -------------------------------------------------------------
    # Stage 4: Gate Cancellation Pass (Self-Inverses & Adjoints)
    # Eliminates H·H -> I, X·X -> I, CX·CX -> I, U·U -> I, T·T† -> I
    # -------------------------------------------------------------
    if verbose:
        print("[Stage 4] Applying Algebraic Gate Cancellation Pass (H-H, CX-CX, X-X, U-U)...")
    cancellation_pass = CustomGateCancellationPass()
    dag = cancellation_pass.run(dag)

    # -------------------------------------------------------------
    # Stage 5: Commutation Analysis Pass
    # Slides commuting gates past each other to expose new cancellations
    # -------------------------------------------------------------
    if verbose:
        print("[Stage 5] Applying Commutation Pass (sliding commuting gates to unlock cancellations)...")
    commutation_pass = CustomCommutationPass()
    dag = commutation_pass.run(dag)
    dag = cancellation_pass.run(dag)  # Clean up newly exposed cancellations

    # -------------------------------------------------------------
    # Stage 6: Gate Decomposition Pass
    # Unrolls complex multi-qubit gates (CCX -> 6 CX + 7 T/T† + 2 H, SWAP -> 3 CX)
    # -------------------------------------------------------------
    if verbose:
        print("[Stage 6] Applying Gate Decomposition Pass (unrolling multi-qubit gates to basis)...")
    decomp_pass = CustomDecompositionPass()
    dag = decomp_pass.run(dag)
    dag = cancellation_pass.run(dag)  # Cancel any newly formed adjacent inverses

    # -------------------------------------------------------------
    # Stage 7 & 8: Qubit Initial Mapping & SABRE Hardware Routing
    # Maps logical qubits to physical qubits and inserts optimal SWAPs
    # -------------------------------------------------------------
    # Normalize coupling map
    if coupling_map is None:
        # Default to 1D linear chain: 0 <-> 1 <-> 2 <-> ...
        coupling_edges = [[i, i + 1] for i in range(num_qubits - 1)] + [[i + 1, i] for i in range(num_qubits - 1)]
    elif isinstance(coupling_map, CouplingMap):
        coupling_edges = [list(e) for e in coupling_map.get_edges()]
    else:
        coupling_edges = [list(e) for e in coupling_map]

    if verbose:
        print(f"[Stage 7 & 8] Applying SABRE Lookahead SWAP Routing over {len(coupling_edges)} physical couplers...")

    sabre_router = CustomSABRERouterPass(coupling_edges)
    dag = sabre_router.run(dag)

    # -------------------------------------------------------------
    # Stage 9: Final Optimization Cleanup
    # Run a final cleanup sweep over the routed physical circuit
    # -------------------------------------------------------------
    if verbose:
        print("[Stage 9] Applying Final Post-Routing Optimization Sweep...")
    dag = decomp_pass.run(dag)  # If any SWAPs were decomposed
    dag = cancellation_pass.run(dag)
    dag = fusion_pass.run(dag)
    dag = cancellation_pass.run(dag)

    # -------------------------------------------------------------
    # Stage 10: Convert DAG back to Hardware-Compliant QuantumCircuit
    # -------------------------------------------------------------
    hardware_circuit = dag.to_circuit()

    # Calculate comparative metrics
    metrics = compare_circuits(circuit, hardware_circuit)
    metrics["pipeline_stages_applied"] = [
        "DAG_Construction",
        "Gate_Fusion",
        "Cancellation",
        "Commutation",
        "Gate_Decomposition",
        "Qubit_Mapping",
        "SABRE_Routing",
        "Final_Optimization",
    ]

    if verbose:
        print("\n" + "-" * 50)
        print("📊 OPTIMIZATION SUMMARY METRICS:")
        print(f"Original Depth:   {orig_depth} -> Optimized: {hardware_circuit.depth()} ({metrics['depth_reduction_pct']}% reduction)")
        print(f"Original Gates:   {orig_gate_count} -> Optimized: {len(hardware_circuit.data)} ({metrics['gate_reduction_pct']}% reduction)")
        print(f"Est. Hardware Fidelity: {metrics['orig_estimated_hardware_fidelity']*100:.2f}% -> {metrics['opt_estimated_hardware_fidelity']*100:.2f}%")
        print("-" * 50)

    # -------------------------------------------------------------
    # Optional Exports: OpenQASM 2.0, 3.0 & QUAM Skeleton
    # -------------------------------------------------------------
    if export_qasm:
        base_fn = qasm_filename or "output/transpiled_circuit"
        qasm2_str = QASMExporter.to_qasm2(hardware_circuit, filename=f"{base_fn}.qasm")
        qasm3_str = QASMExporter.to_qasm3(hardware_circuit, filename=f"{base_fn}.qasm3")
        metrics["qasm2_exported_to"] = f"{base_fn}.qasm"
        metrics["qasm3_exported_to"] = f"{base_fn}.qasm3"
        if verbose:
            print(f"[Export] Saved OpenQASM 2.0 to: {base_fn}.qasm")
            print(f"[Export] Saved OpenQASM 3.0 to: {base_fn}.qasm3")

    if generate_quam:
        quam_skeleton = QASMExporter.to_quam_skeleton(hardware_circuit)
        metrics["quam_skeleton"] = quam_skeleton
        if verbose:
            print("[Export] Generated Quantum Machines QUAM architecture skeleton.")

    if verbose:
        print("=" * 70 + "\n")

    return hardware_circuit, metrics
