# Tutorial: NEURONpyxl in the Python API

---

## Overview

| Example | Level         | Summary                                         |
|---------|---------------|-------------------------------------------------|
| 1       | Basic         | Reading in data generated from NEURONpyxl CLI   |
| 2       | Basic         | Benchmarking NEURONpyxl simulations             |
| 3       | Basic         | Recording STATE variables                       |
| 4       | Intermediate  | Parameter sweep                                 |
| 5       | Intermediate  | Starting a simulation from saved state          |
| 6       | Advanced      | Parameter sweep using Python multiprocessing    |
---

## Prerequisites

- [x] Python 3.13 installed
- [x] Required packages: `neuronpyxl`, `matplotlib`, `numpy`
- [x] Familiarity with: conductance-based modeling, Python syntax

Install dependencies according to the instructions in the README.md.

---

## Setup

Imports required for these examples.

```python
from neuronpyxl import Network

excel_file = "path/to/excel/file.xlsx"
```

---

## Examples

### Example 1: Reading in data generated from NEURONpyxl CLI

First, generate the mod files for the spreadsheet *sheets/single_neuron.xlsx*
```bash
neuronpyxl -f gen_mods --file sheets/single_neuron.xlsx
```

Expected output (Linux):
```bash
Clear out contents of ./mod? (y/n) y
/path/to/neuronpyxl
Mod files: "mod/mod/cs.mod" "mod/mod/es.mod" "mod/mod/k.mod" "mod/mod/leak.mod" "mod/mod/na.mod"

 -> Compiling mod_func.cpp
 -> NMODL ../mod/cs.mod
 -> NMODL ../mod/es.mod
 -> NMODL ../mod/k.mod
Translating es.mod into /path/to/neuronpyxl/x86_64/es.c
Translating cs.mod into /path/to/neuronpyxl/x86_64/cs.c
Translating k.mod into /path/to/neuronpyxl/x86_64/k.c
Notice: Use of POINTER is not thread safe.
Notice: Use of POINTER is not thread safe.
 -> NMODL ../mod/leak.mod
Thread Safe
 -> NMODL ../mod/na.mod
 -> Compiling cs.c
Translating leak.mod into /path/to/neuronpyxl/x86_64/leak.c
Thread Safe
Translating na.mod into /path/to/research/neuronpyxl/x86_64/na.c
 -> Compiling es.c
Thread Safe
 -> Compiling k.c
 -> Compiling leak.c
 -> Compiling na.c
 => LINKING shared library ./libnrnmech.so
Successfully created x86_64/special
```

Next, run a simulation of that spreadsheet with a duration of 9000 ms, recording only the voltage, and using the current injections from the "main.smu" sheet in *fig2.xlsx*.

```bash
neuronpyxl -f run_sim --file sheets/single_neuron.xlsx --name main --duration 9000
```

Expected output:
```bash
Added Cell(gid=1, name=cell) to the network.
Loading simulation parameters...
Running simulation...
Saving data...
Simulation complete! Data has been saved to /path/to/neuronpyxl/data/main_data/main_data.h5.          
Simulation info can be found in /path/to/neuronpyxl/data/main_data/info.txt
```

Read in the data:

```python
import pandas as pd
import matplotlib.pyplot as plt

filepath = "data/main_data/main_data.h5"                  # Path to the data file that was generated
file = pd.HDFStore(filepath)                    # Read in the data file
keys = file.keys()
print(f"File {filepath} has keys: \
      {[k.replace("/","") for k in keys]}")     # Print keys in the data file
```

Expected output:
```bash
File data/main_data/main_data.h5 has keys: ['B4']
```

**Note:**
- Without `--vonly`: voltage and current data are saved for each cell, shown in this example.
- With `--vonly`: data are saved under a `"membrane"` key.
- With `--syn`: additional `"cs"` and `"es"` keys are included for chemical and electrical synaptic currents.

To view the data for the cell named "B4":
```python
B4_data = file["B4"]
print(B4_data)
```

Expected output:
```bash
    V           I_can           I_k         I_ka        I_kcaf          ...     t
0	-62.345983	-2.653341e-11	0.002825	0.771711	5.684559e-14	...	    0.026698
1	-62.345990	-1.768010e-10	0.002825	0.771712	5.684517e-14	...	    0.062147
2	-62.345996	-5.846480e-12	0.002825	0.771712	5.684463e-14	...	    0.097596
3	-62.346002	-4.010661e-10	0.002825	0.771712	5.684434e-14	...	    0.133045
4	-62.346005	-2.977924e-10	0.002825	0.771713	5.684417e-14	...	    0.146484
... ...         ...             ...         ...         ...             ...     ...
```

---

### Example 2: Benchmarking NEURONpyxl simulations


---

### Example 3: Recording STATE variables


---

### Example 5: Parameter sweep


---

### Example 6: Starting a simulation from saved state


---

### Example 7: Parameter sweep using Python multiprocessing


---

## Further Reading

- [NEURONpyxl paper](https://google.com)
- [README](https://github.com/CWRUChielLab/neuronpyxl/blob/main/docs/README.md)
- [NEURON tutorials](https://neuron.yale.edu/docs)
- [Source Code](https://github.com/CWRUChielLab/neuronpyxl)