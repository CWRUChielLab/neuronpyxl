from setuptools import setup, find_packages
import platform
import warnings
os_name = platform.system()

# Requirements for use
reqs = [
    "numpy>=2.2.1",
    "pandas>=2.2.3",
    "XlsxWriter>=3.2.0",
    "openpyxl>=3.1.5",
    "tables>=3.10.1",
    "scipy>=1.15.0",
    "matplotlib"
]

if os_name == "Linux" or os_name == "Darwin":
    reqs.append("neuron==8.2.7")
else:
    warnings.warn("For running neuronpyxl on Windows,\
                  make sure to install NEURON 8.2.7 before installing neuronpyxl.")


# List of all modules involved with the project
MODULES = ["cell", "modbuilder", "network", "reader"]

with open("docs/README.md", 'r') as f:
    README = f.read()

setup(
    name="neuronpyxl",
    version="1.0.0",
    author="Uri Dickman",
    description="neuronpyxl provides an Excel spreadsheet interface \
                    bulit into Python to run SNNAP-based models via the NEURON simulator.",
    long_description=README,
    license="GNU General Public License v3.0",
    python_requires=">=3.10",
    install_requires=reqs,
    py_modules=MODULES,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'neuronpyxl=neuronpyxl.scripts:main',
        ],
    },
    project_urls={
        "Source code": "https://github.com/CWRUChielLab/neuronpyxl.git"
    },
    package_data={
        "neuronpyxl": ["modls/*.mod"]
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        'Development Status :: 1 - Pre-Alpha',
        'Intended Audience :: Science/Research/Education',
        'Topic :: Scientific/Engineering',
        'License :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent'
    ],
)
