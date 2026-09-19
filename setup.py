from setuptools import setup, find_packages

setup(
    name="quantum-circuit-optimizer",
    version="0.1.0",
    description="A modular framework for quantum circuit optimization, DAG analysis, gate decomposition, SABRE routing, and OpenQASM export.",
    author="Quantum Circuit Optimizer Contributors",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "qiskit>=1.0.0",
        "qiskit-aer>=0.14.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "matplotlib>=3.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pylatexenc>=2.10",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Quantum Computing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
