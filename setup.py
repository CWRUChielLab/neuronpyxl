from setuptools import setup, find_packages

# Requirements for use
reqs = [
    "numpy>=2.1.2",
    "pandas>=2.2.3",
    "XlsxWriter>=3.2.0",
    "openpyxl>=3.1.5",
    "tables>=3.10.1",
    "scipy==1.15.1",
    "neuron>=8.2.4"
]

# List of all modules involved with the project
MODULES = ["cell", "modbuilder", "network", "reader", "cmd_util"]

setup(
    name="pysnnap",
    version="1.0.0",
    author="Uri Dickman",
    description="pySNNAP provides an Excel spreadsheet interface bulit into Python to run SNNAP-based models via the NEURON simulator.",
    license="GNU General Public License v3.0",
    python_requires="==3.10",  # Python 3.10 is required because some packages are not fully up to date with Python releases
    install_requires=reqs,
    py_modules=MODULES,
    packages=find_packages(),
    package_data={"pysnnap": ["modls/*.mod"]}
)