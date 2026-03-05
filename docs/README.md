# neuronpyxl

*A tool to run SNNAP-based models from a spreadsheet interface using the NEURON simulator via Python* \
Author: Uri Dickman

---

## Installing NEURON on Windows

If running NEURONpyxl on Windows, it is *highly* recommended to use Windows Subsystem for Linux (WSL) instead to avoid the hassle of using NEURON on Windows. To install WSL, you can follow the instructions [here](https://nrn.readthedocs.io/en/8.2.6/install/install_instructions.html#windows-subsystem-for-linux-wsl-python-wheel). Once WSL is installed, skip the remaining steps and continue with the installation of NEURONpyxl.

If you have decided to run NEURON on Windows, it can work with Anaconda. Install [Anaconda](https://www.anaconda.com/download), then [NEURON](https://github.com/neuronsimulator/nrn/releases/tag/8.2.7) 8.2.7, which is compatible with Python versions 3.9-3.13).

Then, go to Settings > System > About > Advanced system settings > Environment Variables. Add the following to your Path variable: *C:\path\to\anaconda3\Scripts*, *C:\path\to\anaconda3*, *C:\path\to\anaconda3\Library\bin*, and *C:\nrn\bin*.

Create a new environmental variable called PYTHONPATH with the value *C:\nrn\lib\python* if it is not already there. Make sure that the NEURONHOME variable is set to *C:\nrn*. Also add *C:\nrn\lib\nrniv.exe* to your path so that you can run the `nrniv` command if needed.

Click "Ok" and close your settings. Test if this worked by opening a new instance of Anaconda Prompt and entering `python`. Then enter `from neuron import h, gui`. If this runs without error and the NEURON main menu appears, then you are good to go. The GUI is not needed to run neuronpyxl.

If needed, see this [video](https://www.youtube.com/watch?v=jWjiPWG3DKY) for a walkthrough.

---

## Installing neuronpyxl

1. In the terminal, clone the [NEURONpyxl](https://github.com/CWRUChielLab/neuronpyxl) repository
```
git clone https://github.com/CWRUChielLab/neuronpyxl.git
```
2. Change into the *neuronpyxl* folder. Install the neuronpyxl package into a virtual Python environment:
    - With [uv](https://docs.astral.sh/uv/) (*recommended*):
    ```
    uv venv /path/to/venv --python 3.13 && source /path/to/venv/bin/activate && uv pip install .
    ```
    - With [Micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html) (*recommended*): 
    ```
    micromamba create -f environment.yml
    ```
    - With [pip](https://pypi.org/project/pip/):
    
    ```
    python3 -m venv /path/to/venv && source /path/to/venv/bin/activate && pip install .
    ```
    - With [Anaconda](https://www.anaconda.com/download): 
    ```
    conda create -f environment.yml
    ```
3. Activate NEURONpyxl (if not already):
    - With uv or pip: `source /path/to/venv/bin/activate`
    - With Micromamba: `micromamba activate neuronpyxl`
    - With Anaconda: `conda activate neuronpyxl`

---

## Usage

neuronpyxl simulations must be run using the Excel spreadsheet. A blank spreadsheet is provided in the *sheets/* folder. Once the parameters in the spreadsheet are entered, you must compile the mod files corresponding to that simulation. You only need to do this once per model -- changing parameter values or adding/removing synapses and cells does not require recompilation. You only need to recompile when adding ion pools or new ion channels.

How to run a simulation from the command line:

1. Activate virtual environment. For example
```
micromamba activate neuronpyxl
```
2. Compile the mod files
```
neuronpyxl -f gen_mods --file path/to/excel_file.xlsx
```
3. Run a simulation
```
neuronpyxl -f run_sim --file path/to/excel_file.xlsx --name simname --duration simdur
```

This saves your data into one or more HDF5 files located in "Data/simname_data/". There are other parameters to further customize your simulation.

# Command Line Interface Reference

A complete reference for all command line arguments supported by the neuronpyxl CLI.

---

## Usage

```bash
neuronpyxl -f <function_name> --file <filename> --name <simname> --duration <dur> [options]
```

---

## Required Arguments

| Argument | Syntax | Description |
|----------|--------|-------------|
| `-f` | `-f <function_name>` | `gen_mods` to generate and compile mod files, `run_sim` to run a simulation. |
| `--file` | `--file <filename>` | Path to the Excel configuration file (`.xlsx`) defining the simulation parameters. |
| `--name` | `--name <simname>` | Name of the simulation to run. Loads the corresponding `<simname>.smu` file from the spreadsheet. |
| `--duration` | `--duration <dur>` | Total simulation duration in **milliseconds**. |

---

## Optional Arguments

### Noise

```
--noise <freq> <weight> <tau>
```

Enables synaptic background noise with the specified parameters.

| Parameter | Unit | Description |
|-----------|------|-------------|
| `freq` | Hz | Noise frequency |
| `weight` | µS | Synaptic weight |
| `tau` | ms | Decay time constant |

> If `--noise` is not provided, no background noise is applied.

---

### Equilibration Period

```
--teq <dur>
```

Extends the simulation by an additional `<dur>` ms before the main run, allowing dynamical variables to relax to steady state.

**Default:** `1000` ms

---

### Integration Method

```
--method <m>
```

Specifies the numerical integration method.

| Value | Method |
|-------|--------|
| `1` | Backwards-Euler |
| `2` | Crank-Nicholson |
| `3` | CVODE *(default)* |

---

### Error Tolerance

```
--atol <a>
```

Sets the absolute error tolerance for the adaptive integrator.

**Default:** `1e-5`

---

### Time Step

```
--step <dt>
```

Forces a **fixed** time step of `<dt>` ms. If omitted, the simulation uses an adaptive (variable) time step, which is **recommended** for most use cases.

---

### Interpolation

```
--interp <dt>
```

After simulation, interpolates all output data to a uniform time step of `<dt>` ms using **cubic spline interpolation**. Useful for downstream analysis requiring evenly-sampled data.

---

### Record Synaptic Currents

```
--syn
```

*(flag, no arguments)*

When provided, records both **electrical** and **chemical** synaptic currents in addition to standard outputs.

---

### Voltage-Only Mode

```
--vonly
```

*(flag, no arguments)*

Records only membrane voltages and time, saving everything to a **single output file**. By default, each cell's data is saved into its own subfolder.

---

### Cluster Mode

```
--cluster
```

*(flag, no arguments)*

Suppresses interactive prompts for clearing data folders. Use this when running on an **HPC cluster** or in any non-interactive (headless) environment.

---

### Custom Output Folder

```
--folder <foldername>
```

Saves all simulation output into a folder named `<foldername>` instead of the default location.

---

## Examples

**Minimal run:**
```bash
neuronpyxl run_sim --file single_neuron.xlsx --name main --duration 5000
```

**With noise and synaptic recording:**
```bash
python run_sim.py --file sheets/small_nework.xlsx --name main --duration 5000 \
                  --noise 100 1e-4 12 --syn
```

**Fixed timestep with interpolation, record voltage only saved to custom folder:**
```bash
python run_sim.py --file sheets/small_nework.xlsx --name main --duration 5000 \
                  --step 0.05 --interp 0.1 --vonly --folder small_nework_results
```

See the examples and docs/TUTORIAL.md for how to use NEURONpyxl in the Python API.

---

# Citing NEURONpyxl

Dickman, U., Thomas, P. J., Chiel, H. J., Byrne, J. H., and Neveu, C. L., (2026) *Frontiers in Computational Neuroscience*. In review.

```BibTeX
@article{Dickman-2026-FCNS,
author   = {Uri Dickman, Peter J. Thomas, Hillel J. Chiel,
          John H. Byrne, and Curtis L. Neveu},
year    = {2026},
title   = {NEURONpyxl: Fast, flexible, Python-integrated simulation
          of biophysical neural networks with complex plastic synapses},
journal = {Frontiers in Computational Neuroscience},
notes   = {In review}
```
