from setuptools import setup, find_packages

# Requirements for use
reqs = [
    "numpy>=2.2.1",
    "pandas>=2.2.3",
    "XlsxWriter>=3.2.0",
    "openpyxl>=3.1.5",
    "tables>=3.10.1",
    "scipy>=1.15.0"
]

# List of all modules involved with the project
MODULES = ["cell", "modbuilder", "network", "reader", "cmd_util"]

setup(
    name="neuronpyxl",
    version="1.0.0",
    author="Uri Dickman",
    description="neuronpyxl provides an Excel spreadsheet interface bulit into Python to run SNNAP-based models via the NEURON simulator.",
    license="GNU General Public License v3.0",
    python_requires=">=3.10",
    install_requires=reqs,
    py_modules=MODULES,
    packages=find_packages(),
    package_data={"neuronpyxl": ["modls/*.mod"]}
)
