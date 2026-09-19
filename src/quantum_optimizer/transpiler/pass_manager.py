"""
Custom Pass Manager.
Pipelines TransformationPass and AnalysisPass instances,
coordinates PropertySet sharing, and executes optimization loops until convergence.
"""

from typing import List, Union, Optional
from qiskit import QuantumCircuit
from .base import BasePass, AnalysisPass, TransformationPass, PropertySet
from .dag import CustomDAG


class CustomPassManager:
    """
    Manages and executes a sequence of custom transpilation passes over a quantum circuit.
    """

    def __init__(self, passes: Optional[List[BasePass]] = None, max_iterations: int = 10):
        """
        Args:
            passes: List of passes to execute in order.
            max_iterations: Max loop iterations when repeating passes until fixed-point convergence.
        """
        self.passes: List[BasePass] = passes or []
        self.property_set = PropertySet()
        self.max_iterations = max_iterations

    def append(self, transpiler_pass: BasePass) -> None:
        """Add a pass to the execution queue."""
        self.passes.append(transpiler_pass)

    def run(self, circuit_or_dag: Union[QuantumCircuit, CustomDAG]) -> QuantumCircuit:
        """
        Run the transpiler passes over the circuit.

        Args:
            circuit_or_dag: QuantumCircuit or CustomDAG.

        Returns:
            Transpiled and optimized QuantumCircuit.
        """
        if isinstance(circuit_or_dag, QuantumCircuit):
            dag = CustomDAG.from_circuit(circuit_or_dag)
        elif isinstance(circuit_or_dag, CustomDAG):
            dag = circuit_or_dag
        else:
            raise TypeError("Expected QuantumCircuit or CustomDAG.")

        for current_pass in self.passes:
            current_pass.property_set = self.property_set

            if isinstance(current_pass, AnalysisPass):
                current_pass.run(dag)
            elif isinstance(current_pass, TransformationPass):
                dag = current_pass.run(dag)

        return dag.to_circuit()

    def run_until_fixed_point(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Repeatedly run passes until gate count and depth stop changing (fixed-point reached).

        Args:
            circuit: Input circuit.

        Returns:
            Fully optimized QuantumCircuit.
        """
        current_qc = circuit
        for _ in range(self.max_iterations):
            next_qc = self.run(current_qc)
            if next_qc.depth() == current_qc.depth() and len(next_qc.data) == len(current_qc.data):
                break
            current_qc = next_qc

        return current_qc
