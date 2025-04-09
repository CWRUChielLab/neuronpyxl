# pySNNAP

*A tool to run SNNAP-based models from a spreadsheet interface using the NEURON simulator via Python*
Authors: Uri Dickman, Curtis Neveu, Hillel Chiel, Peter Thomas

## Installing NEURON

### Mac

Download and run the pre-compiled installer [here](https://github.com/neuronsimulator/nrn/releases/download/8.2.6/nrn-8.2.6-macosx-10.9-universal2-py-38-39-310-311-312.pkg).

### Linux

Install Python according to your distribution and then run `python3 pip install neuron` after creating a virtual environment (se next section).

### Windows

It is recommended to run pySNNAP through Windows Subsystem for Linux (WSL). To install it, you can follow the instructions [here](https://nrn.readthedocs.io/en/8.2.6/install/install_instructions.html#windows-subsystem-for-linux-wsl-python-wheel). Once WSL is installed, run it and follow the Linux instructions for installing NEURON.

Otherwise, install [Anaconda](https://www.anaconda.com/download), then [NEURON](https://github.com/neuronsimulator/nrn/releases/download/8.2.6/nrn-8.2.6.w64-mingw-py-38-39-310-311-312-setup.exe) 8.2.4 or greater onto your computer (note: NEURON 8.2.4 is compatible with Python 3.7-3.11, and NEURON 8.2.6 is compatible with 3.8-3.12).

Then, go to Settings > System > About > Advanced system settings > Environment Variables. Add the following to your Path variable: *C:\path\to\anaconda3\Scripts*, *C:\path\to\anaconda3*, *C:\path\to\anaconda3\Library\bin*, and *C:\nrn\bin*.

Create a new environmental variable called PYTHONPATH with the value *C:\nrn\lib\python* if it is not already there. Make sure that the NEURONHOME variable is set to *C:\nrn*. Also add *C:\nrn\lib\nrniv.exe* to your path so that you can run the `nrniv` command if needed.

Click "Ok" and close your settings. Test if this worked by opening a new instance of Anaconda Prompt and entering `python`. Then enter `from neuron import h, gui`. If this runs without error and the NEURON main menu appears, then you are good to go. The GUI is not needed to run pySNNAP.

If needed, see this [video](https://www.youtube.com/watch?v=jWjiPWG3DKY) for a walkthrough.

## Installing pySNNAP

Clone this repository or download the Zip files and extract them to a folder. The code can be run with pip or Anaconda.

If you are using pip, [create a virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/). Activate the environment, then run `python setup.py install --user`

If you are using Anaconda (recommended in Windows), create the environment and install the package with `conda env create -f environment.yml`. Activate the environment with `conda activate pysnnap-env`.

## Usage

pySNNAP simulations must be run using the Excel spreadsheet. A blank spreadsheet is provided in the Excel_files folder. Once the parameters in the spreadsheet are entered, you must compile the mod files corresponding to that simulation. You only need to do this once per model -- simply changing parameter values or adding/removing synapses and cells does not require recompiling. You only need to recompile when adding ion pools or new ion channels.

To compile the mod files, run
`python3 -m pysnnap.cmd_util -f gen_mods --file path/to/excel_file.xlsx`

To run a simulation, run
`python3 -m pysnnap.cmd_util -f run_sim --file path/to/excel_file.xlsx --name simname --duration simdur`

This saves your data into one or more HDF5 files located in Data/simname_data/.

There are other parameters to further customize your simulation.

- --file filename: path to Excel file to run.
- --name simname: the simulation from the spreadsheet you want to run (simname.smu)
- --duration dur: runs simulation for dur ms.
- --noise freq weight tau: noise parameters. freq in Hz, weight in uS, tau in ms. If not provided, noise will not be included.
- --teq t: simulation runs for an additional t ms to relax dynamical variables to their steady states. Default is 1000.
- --method m: specify integration method (m=1 for  Backwards-Euler, m=2 for Crank-Nicholson). Default is 2.
- --atol: absolute error tolerance for the simulation. Default is 1e-5.
- --step dt: if provided, runs simulation at constant time step dt (ms). Otherwise, integrates at variable timestep (recommended)
- --interp dt: if provided, interpolates data to constant timestep dt (ms) using cubic spline interpolation.
- --syn: no arguments. If provided, records electrical and chemical synaptic currents.
- --vonly: no arguments. If provided, only records membrane voltages and time and saves to a single file. Otherwise, each cell's data is recorded into its own folder.
- --cluster: no arguments. Doesn't prompt user for clearing data folders. useful if running on a HPC cluster.

See the Examples folder for how to read data and run simulations from Python.