# PySNNAP

*A tool to run SNNAP-based models from a spreadsheet interface using the NEURON simulator via Python*

## Installation Guide

Before you install NEURON and PySNNAP, make sure that you have Git [installed](https://git-scm.com/downloads). On macOS, it is recommended to install Python and Git via [Homebrew](https://brew.sh/), as it will also automatically install Command Line Tools if not already installed.

Next, install NEURON version 8.2.4 or later (see below). This code is functional for *Python 3.10* because of package dependencies.

### Windows

It is highly recommended to run NEURON through WSL, but if you must use Windows, follow these instructions. Install [Anaconda](https://www.anaconda.com/download) and [NEURON](https://www.neuron.yale.edu/neuron/download) 8.2.4 or greater onto your computer (note: NEURON 8.2.4 is compatible with Python 3.7-3.11, and NEURON 8.2.6 is compatible with 3.8-3.12). This project requires Python 3.10 anyways, so make sure you have the correct version.

Install Anaconda and Python *first*, then install NEURON. Then, go to Settings > System > About > Advanced system settings > Environment Variables. Add the following to your Path variable (replace with correct location of Anaconda installation): *C:\path\to\anaconda3\Scripts*, *C:\path\to\anaconda3*, *C:\path\to\anaconda3\Library\bin*, and *C:\nrn\bin*.

Next, create a new environmental variable called PYTHONPATH with the value *C:\nrn\lib\python*. Make sure that the NEURONHOME is set to *C:\nrn* as long as NEURON installed there. It is also useful to add *C:\nrn\lib\nrniv.exe* to your path so that you can run the `nrniv` command.

Click "Ok" and close your settings. Test if this worked by opening a new instance of Anaconda Prompt and typing `python` to access the Python interpreter. Click enter and then type `from neuron import h, gui`. If this runs without error and the NEURON main menu appears, then you are good to go.

See this [video](https://www.youtube.com/watch?v=jWjiPWG3DKY) for a walkthrough.

### Linux or WSL

To install via Windows Subsystem for Linux, you can follow the instructions [here](https://nrn.readthedocs.io/en/8.2.6/install/install_instructions.html#windows-subsystem-for-linux-wsl-python-wheel).

Install Python according to your distribution and then run `pip install neuron`.

### macOS

Install Python for macOS. Run `python3 -m pip install neuron`. If installing NEURON with pip doesn't work, you can download the pre-compiled installer [here](https://www.neuron.yale.edu/neuron/download).

## Usage

### Setup

Either download the Zip files or [clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) the repository.

Install the package by running `python3 setup.py install`, or run `python3 setup.py develop --user` if you wish to edit the source code (use `python` on Windows).

### Run a simulation

Interfacing with the simulation can be done either through the commmand line or Python API. Running this through the command line can be done via the `cmd_util` module.

First, generate and compile the mod files. This command only needs to be executed once for a given spreadsheet. You *only* need to run this command if you haven't run it before for a given spreadsheet, or if you have added new ion channels or ion pools. You do *not* need to run this file if you want to run a different .smu sheet within the main .xlsx file, or if you simply change the values of a parameter. The mod files have no information about the parameter values, only about the ion channels and pools that exist. Editing the synapse parameters in any way does not change anything about the mod files.

`python3 -m pysnnap.cmd_util -f gen_mods --file /path/to/file.xlsx`

Next, you can either run a simulation through a Python script or the terminal. Here is how to run a simulation through the terminal:

`python3 -m pysnnap.cmd_util -f run_sim --file /path/to/file.xlsx --name simulation_name **kwargs`

All possible arguments:
- -f function: function to run. The options are gen_mods and run_sim. The only required argument for gen_mods is --file.
- --file filename: required argument to specify path to the Excel file to run
- --name sim_name: required argument to specify name of the .smu sheet in the excel file (without the smu)
- --duration dur: required argument to specify length of the simulation runtime in ms
- --step dt: optional argument to specify the timestep of the simulation. Defaults to variable timestepping (recommended)
- --method num: optional argument to specify the integration method of the simulation. Method 1 is Backwards-Euler and method 2 is Crank-Nicholson. Defaults to 2.
- --noise freq weight tau: optional argument to specify noise parameters to inject a noisy current into the cell via an exponential synapse (see ExpSyn NEURON documention). freq determines the frequency in Hz, the weight is the synaptic weight in nS, and tau is the time constant in ms.
- --interp dt: optional argument. If provided, recorded data will be interpolated to the provided constant timestep dt.
- --atol tol: optional argument to specify the absolute error tolernace of the integration. Defaults to 1e-5.
- --syn: optional with no arguments. If provided, will record the currents from chemical and electrical synapses if available
- --vonly: optional with no arguments. If provided, will record the membrane potentials and time from each cell only.
- --teq: Sets equilibration time to provided value. Defaults to 1000.0 ms. User should test model for
ideal values of teq.

The data recorded from each cell is recorded in its own .h5 file within the folder. If --vonly is provided, then records all data into one file. If --syn is provided, records electrical and chemical synaptic currents in their own respective files, if they exist. If --vonly and --syn are provided, defaults to --vonly. To access the data, write the following code:

```
import pandas as pd
cell_data = pd.HDFStore("Data/sim_data/cell_name.h5)["data"]
```

Keys:
- t -> time (ms)
- V -> membrane potential (mV)
- I_applied_0.5 -> total applied current injection (nA)

Model-dependent keys:
- I_na, I_k, I_leak, I_can etc. (depends on the ion channels present in model)
- cai -> internal Ca2+ concentration (mM) (if Ca pool present)
- nai -> internal Na+ concentration (mM) (if Na pool present)
- ki -> internal K+ concentration (mM) (if K pool present)
- cli -> internal Cl- concentration (mM) (if Cl pool present)

Synaptic current keys (if present):
- Chemical synapses: I_presyn_2_postsyn_fast or I_presyn_2_postsyn_slow
- Electrical synapses: I_presyn_2_postsyn
- Both files have a "t" key.

Alternately, you can run a simulation from a Python file or Jupyter Notebook, samples of which are located in the *Examples* folder. A blank spreadsheet is also available at *Examples/Excel_files/blank.xlsx*.

To use the Python API, write the following code, for example:

```
from pysnnap.network import NetworkBuilder
import matplotlib.pyplot as plyt

excel_path = "path/to/excel/file.xlsx"
sim = "sim_name"
nb = NetworkBuilder(params_file=excel_path, sim_name=sim) # Optionally, set noise=(100, 1, 10)
nb.simdur = 1000
nb.run() # Optionally, set voltage_only=True
data = nb.get_cell_data("cell_name")

plt.plot(data["t], data["V"])
```

For more examples, see the *Examples* folder.