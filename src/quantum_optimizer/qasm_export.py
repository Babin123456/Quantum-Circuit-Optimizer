"""
OpenQASM and QUAM Export Module.
Provides functions to export optimized quantum circuits to:
- OpenQASM 2.0 (legacy standard)
- OpenQASM 3.0 (modern standard with pulse/classical capabilities)
- QUAM Roadmap Stub (Quantum Machines Abstract Architecture)
"""

import os
from typing import Optional
from qiskit import QuantumCircuit
from qiskit import qasm2, qasm3


class QASMExporter:
    """Exports QuantumCircuit objects to OpenQASM 2.0, OpenQASM 3.0, and QUAM descriptors."""

    @staticmethod
    def to_qasm2(circuit: QuantumCircuit, filename: Optional[str] = None) -> str:
        """
        Export circuit to OpenQASM 2.0 format.

        Args:
            circuit: QuantumCircuit to export.
            filename: Optional filepath to save the .qasm file.

        Returns:
            OpenQASM 2.0 string.
        """
        qasm_str = qasm2.dumps(circuit)
        if filename:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(qasm_str)
        return qasm_str

    @staticmethod
    def to_qasm3(circuit: QuantumCircuit, filename: Optional[str] = None) -> str:
        """
        Export circuit to modern OpenQASM 3.0 format.

        Args:
            circuit: QuantumCircuit to export.
            filename: Optional filepath to save the .qasm file.

        Returns:
            OpenQASM 3.0 string.
        """
        qasm_str = qasm3.dumps(circuit)
        if filename:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(qasm_str)
        return qasm_str

    @staticmethod
    def to_quam_skeleton(circuit: QuantumCircuit, machine_name: str = "quantum_hardware_1") -> dict:
        """
        Generates a QUAM (Quantum Machines Architecture Model) configuration skeleton
        from a gate-level quantum circuit.

        Note: QUAM operates at the pulse, readout resonator, and qubit drive hardware level
        (OPX controllers). This method provides the bridge mapping circuit qubits to QUAM elements.

        Args:
            circuit: QuantumCircuit.
            machine_name: Name of the QUAM machine config.

        Returns:
            Dictionary representing high-level QUAM element layout.
        """
        quam_config = {
            "quam_version": "1.0.0",
            "machine": machine_name,
            "num_qubits": circuit.num_qubits,
            "qubits": {},
            "quantum_elements": [],
            "circuit_metadata": {
                "depth": circuit.depth(),
                "gate_count": sum(circuit.count_ops().values()),
                "qubit_mapping": [f"q[{i}]" for i in range(circuit.num_qubits)],
            },
        }

        for i in range(circuit.num_qubits):
            quam_config["qubits"][f"q{i}"] = {
                "f_01": 5.0e9 + i * 1.5e8,  # Approximate resonant frequency (Hz)
                "anharmonicity": -300e6,
                "xy_drive_channel": f"con1_ch{2*i+1}",
                "z_flux_channel": f"con1_ch{2*i+2}",
                "resonator": {
                    "f_readout": 7.0e9 + i * 1.0e8,
                    "readout_channel": f"con2_ch{i+1}",
                },
            }
            quam_config["quantum_elements"].append(f"q{i}")

        return quam_config
