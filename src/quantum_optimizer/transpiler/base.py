"""
Custom Transpiler Base Architecture.
Defines:
- PropertySet: Shared state / blackboard across passes (e.g. layout, DAG statistics)
- BasePass: Abstract root for all transpiler passes
- AnalysisPass: Pass that inspects the DAG/circuit and populates PropertySet without modifying the circuit
- TransformationPass: Pass that mutates or transforms the DAG/circuit
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PropertySet(dict):
    """A dictionary-based blackboard for sharing analysis and layout state between passes."""
    pass


class BasePass(ABC):
    """Abstract base class for all custom compiler passes."""

    def __init__(self):
        self.property_set: Optional[PropertySet] = None

    @abstractmethod
    def name(self) -> str:
        """Returns the human-readable name of the pass."""
        return self.__class__.__name__


class AnalysisPass(BasePass):
    """
    An AnalysisPass inspects the circuit or DAG and computes properties
    (e.g., depth, gate count, commutation sets, layout) without modifying the circuit.
    """

    @abstractmethod
    def run(self, dag: Any) -> None:
        """Run analysis on the DAG and write findings to self.property_set."""
        pass


class TransformationPass(BasePass):
    """
    A TransformationPass takes a DAG or circuit, transforms it, and returns the modified result.
    """

    @abstractmethod
    def run(self, dag: Any) -> Any:
        """
        Execute the transformation on the DAG.

        Args:
            dag: The input CustomDAG or circuit.

        Returns:
            The transformed CustomDAG or circuit.
        """
        pass
