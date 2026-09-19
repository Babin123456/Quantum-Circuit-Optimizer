"""
Quantum Circuit Optimizer
=========================
A comprehensive toolkit for quantum circuit optimization, DAG circuit analysis,
gate decomposition, SABRE heuristic hardware routing, and OpenQASM / QUAM export.
"""

from .optimizer import QuantumOptimizer
from .dag_utils import DAGAnalyzer
from .decomposition import Decomposer
from .routing import SABRERouter
from .metrics import CircuitMetrics, compare_circuits, calculate_estimated_fidelity
from .qasm_export import QASMExporter

__version__ = "0.1.0"
__all__ = [
    "QuantumOptimizer",
    "DAGAnalyzer",
    "Decomposer",
    "SABRERouter",
    "CircuitMetrics",
    "compare_circuits",
    "calculate_estimated_fidelity",
    "QASMExporter",
]
