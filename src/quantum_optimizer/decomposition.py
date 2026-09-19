"""
Gate Decomposition Module.
Handles decomposing multi-qubit gates (Toffoli/CCX, CSWAP, controlled rotations)
into elementary 1-qubit and 2-qubit basis gates (CX, SX, RZ, U3).
"""

from typing import List, Optional
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate, CSwapGate
from qiskit.transpiler.passes import BasisTranslator, UnrollCustomDefinitions
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.transpiler import PassManager


class Decomposer:
    """
    Decomposes multi-qubit and composite quantum gates into hardware-native basis gates.
    """

    def __init__(self, target_basis: Optional[List[str]] = None):
        """
        Initialize the Decomposer.

        Args:
            target_basis: List of target basis gates (default: ['cx', 'u', 'h', 't', 'tdg', 'rz', 'sx'])
        """
        self.target_basis = target_basis or ["cx", "u", "h", "t", "tdg", "rz", "sx", "x"]

    def decompose(self, circuit: QuantumCircuit, reps: int = 1) -> QuantumCircuit:
        """
        Recursively decompose composite gates in the circuit.

        Args:
            circuit: QuantumCircuit to decompose.
            reps: Number of decomposition passes to perform.

        Returns:
            Decomposed QuantumCircuit.
        """
        decomposed = circuit.copy()
        for _ in range(reps):
            decomposed = decomposed.decompose()
        return decomposed

    def decompose_to_basis(self, circuit: QuantumCircuit, basis_gates: Optional[List[str]] = None) -> QuantumCircuit:
        """
        Decompose all gates in the circuit directly into the specified basis gates
        using Qiskit's equivalence library and BasisTranslator.

        Args:
            circuit: QuantumCircuit to decompose.
            basis_gates: Target basis gates list.

        Returns:
            Fully decomposed QuantumCircuit matching basis_gates.
        """
        basis = basis_gates or self.target_basis
        pm = PassManager([
            UnrollCustomDefinitions(SessionEquivalenceLibrary, basis_gates=basis),
            BasisTranslator(SessionEquivalenceLibrary, target_basis=basis),
        ])
        return pm.run(circuit)

    @staticmethod
    def build_toffoli_standard_decomposition() -> QuantumCircuit:
        """
        Construct the canonical 6-CNOT Toffoli (CCX) decomposition into {H, T, Tdg, CX}.
        Matches the textbook construction:
        - 6 CX gates
        - 7 T/T† gates
        - 2 H gates

        Returns:
            QuantumCircuit of 3 qubits implementing Toffoli.
        """
        qc = QuantumCircuit(3, name="Decomposed_Toffoli")
        # Target is qubit 2, controls are qubits 0 and 1
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
        return qc

    @staticmethod
    def build_redundant_toffoli_test_circuit() -> QuantumCircuit:
        """
        Builds the exact decomposed circuit from User Image 3, including the
        redundant adjacent U(pi, 0, pi) cancellation pattern at the end of q2.

        Returns:
            QuantumCircuit demonstrating real-world decomposition and cancellation opportunity.
        """
        qc = QuantumCircuit(3, name="Redundant_Toffoli_Test")
        # Base Toffoli implementation
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

        # Redundant consecutive pair at the end (as observed in user image 3):
        # U(pi, 0, pi) * U(pi, 0, pi) = X * X = I (Identity)
        qc.u(np.pi, 0, np.pi, 2)
        qc.u(np.pi, 0, np.pi, 2)
        return qc
