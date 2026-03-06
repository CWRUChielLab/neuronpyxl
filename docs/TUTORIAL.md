# Tutorial: NEURONpyxl in the Python API

---

## Overview

| Example | Level         | Summary                                         |
|---------|---------------|-------------------------------------------------|
| 1       | Basic         | Reading in data generated from NEURONpyxl CLI   |
| 2       | Basic         | Benchmarking NEURONpyxl simulations             |
| 3       | Intermediate  | Recording NEURON objects                        |
| 4       | Intermediate  | Starting a simulation from saved state          |
| 5       | Intermediate  | Parameter sweep                                 |
| 6       | Intermediate  | Variable input current                          |
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

First, generate the mod files for the spreadsheet *sheets/single_neuron1.xlsx*
```bash
neuronpyxl -f gen_mods --file sheets/single_neuron2.xlsx
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

Next, run a simulation of that spreadsheet with a duration of 9000 ms, recording only the voltage with the CVODE integrators, and using the current injections from the "main.smu" sheet in *fig2.xlsx*.

```bash
neuronpyxl -f run_sim --file sheets/single_neuron2.xlsx \
                      --name excitability --duration 9000 --method 3
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

filepath = "data/excitability_data/excitability_data.h5" # Path to the data file
file = pd.HDFStore(filepath)                             # Read in the data file
keys = file.keys()
print(f"File {filepath} has keys: \
      {[k.replace("/","") for k in keys]}")              # Print keys in the data file
```

Expected output:
```bash
File data/excitability_data/excitability_data.h5 has keys: ['B4']
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

As you can see, NEURONpyxl saves the membrane potential, all of the ion currents, the total applied current, and the time.
When we include noise, NEURONpyxl also saves the total injected noisy current.

Plot the membrane voltage and injected current:
```python
t = B4_data["t"]/1000           # Convert to seconds
v = B4_data["V"]                # Get membrane potential
iapp = B4_data["I_app"]         # Get applied current

fig,axs = plt.subplots(2,1,figsize=(12,8),sharex=True)
axs[0].plot(t,v)
axs[0].set_ylabel("Voltage (mV)")

axs[1].plot(t,iapp)
axs[1].set_ylabel("Applied current (nA)")

fig.supxlabel("Time (s)")
fig.suptitle("Simple B4 Neuron Simulation")

plt.show()
```

---

### Example 2: Benchmarking NEURONpyxl simulations

The goal of this example is to benchmark noisy NEURON simulations of a single neuron. The steps are
1. Compile the mod files
```bash
neuronpyxl -f gen_mods --file sheets/single_neuron1.xlsx
```
2. Construct a Network object without and with noise

```python
import numpy as np
from neuronpyxl import Network

excel_path = "sheets/single_neuron1.xlsx"
simdur = 9000
eq_time = 1000

nw = Network(
    params_file=excel_path,
    sim_name="main",
    noise=(500,1e-3,3), # Replace with None for no noise
    dt=-1,
    integrator=2,
    atol=1e-5,
    eq_time=eq_time,
    simdur=simdur
)
```

3. Run 20 simulations for each network
```python
N = 20
times = np.zeros(N)

for i in range(N):
    nw.run(record_none=True)    # We're not using any data so don't record anything
    times[i] = nw.simtime       # NEURONpyxl records the simulation time already
```

4. Compute the mean times 
```python
mean = np.mean(times)
std = np.std(times)
```

We expect to see that with adaptivity, the simulations with noise take much longer than without noise because CVODE uses smaller timesteps when there are steeper gradients in the
dynamical variables.

See [ex2.py](../examples/ex2.py) for the full simulation.

---

### Example 3: Recording NEURON objects

This example shows how to interface with NEURON and the NEURONpyxl data structures to record state variables other than currents and voltages.

As always, compile the mod files:

```bash
neuronpyxl -f gen_mods --file sheets/small_network.xlsx
```

Next, construct a small network of 3 neurons connected with chemical synapses.

```python
import matplotlib.pyplot as plt
from neuronpyxl import network
from neuron import h

filepath = "./sheets/small_network.xlsx"
nw = network.Network(
    params_file=filepath,
    sim_name="synapse",
    dt=-1,
    integrator=2,
    atol=1e-5,
    eq_time=2500,
    simdur=5000,
    noise=None,
    seed=False,
)

seg_a = nw.cells["A"].section(0.5)                       # Get the NEURON segment of cell A at location 0.5
synw = nw.chemical_synapses["fast"]["A"]["B"]["synapse"] # Get the fast synapse hoc object from A -> B

# Record during simulation
Ana_rec = h.Vector().record(seg_a._ref_A_neuronpyxl_na)  # Na activation
nai_rec = h.Vector().record(seg_a._ref_nai)              # Internal Na concentration
Atsyn_rec = h.Vector().record(synw._ref_At)              # Synaptic time-dependent activation
t_rec = h.Vector().record(h._ref_t)                      # Time

nw.run(record_none=True)                                 # We only want our own recordings
```

`segment._ref_` records the value of the hoc pointer at that NEURON segment.
Follow the `_ref_` with the variable name you want to record (see the mod files) and then the mechanism in which they are defined.
NEURONpyxl mechanism names start with neuronpyxl_.
There are other global pointers. The time pointer is in the `h` object, and in Point Processes like synapses and ion pools, you don't need a mechanism definition.
Instead of accessing from a segment, you access it from the point process object (like h.IClamp or h.neuronpyxl_CS).

See [ex3.py](../examples/ex3.py) for the full simulation data processing.

---

### Example 4: Starting a simulation from a saved state

In this example, we demonstrate how to save the state of a simulation and continue the simulation from that state.

First, compile the mod files.

```bash
neuronpyxl -f gen_mods --file sheets/small_network.xlsx
```

```python
from neuron import h
from neuronpyxl import network

filepath = "./sheets/small_network.xlsx"
nw = Network(params_file=filepath,
                    sim_name="synapse",
                    dt=-1,
                    integrator=2,
                    atol=1e-5,
                    eq_time=2500,
                    simdur=13000,
                    noise=None
    )
```

Run the simulation to where you want to save the state

```python
nw.run(voltage_only=True)
nw.save_state(filename="state.bin")
```

Now, you should see a file called "state.bin" that was created in the current directory.

In order to restore to the state in that file, you *must* setup the entire NEURON memory structure **exactly** to when you recorded the state previously.

This is very easy with NEURONpyxl, since we can just copy the code from above along with a few extra NEURON calls to make it all work.

```python
filepath = "./sheets/small_network.xlsx"
nw_restored = network.Network(params_file=filepath,
                            sim_name="synapse",
                            dt=-1,
                            integrator=2,
                            atol=1e-5,
                            eq_time=2500,
                            simdur=13000,
                            noise=None,
                            seed=False
                            )

# We also need to set up the recordings the same
# but without calling the entire initialization sequence
# (which resets the dynamical variables and the global time)
nw_restored.record_voltage_only()
nw_restored.restore_state(filename="state.bin")
```

Now, the state has been restored so let's attach current clamp. You can add anything you want to the model in this section.

```python
ic = nw_restored.attach_iclamp(name="B",delay=h.t-nw_restored.eq_time,dur=5000,amp=2)
```

Re-initialize CVODE and start the simulation where it left off, advancing for another 5 seconds.

```python
h.cvode_active(1)
h.cvode.re_init()
h.continuerun(h.t + 5000)
```

See [ex4.py](examples/ex4.py)

---

### Example 5: Parameter sweep

In this example, we demonstrate a simple parameter sweep using a simple Python over a range of parameter values. We show the increase in frequency of the voltage of a single spiking neuron in response to increasing the injected current.

First, build the mod files.

```bash
neuronpyxl -f gen_mods --file sheets/single_neuron2.xlsx
```

Instead of defining the current clamp in, we attach it to the network using the `attach_iclamp` function in the Network class, which returns the hoc IClamp object.

```python
nw = Network(params_file=filepath,
                            sim_name="nostim",
                            dt=-1,
                            integrator=2,
                            atol=1e-5,
                            eq_time=1000,
                            simdur=9000,
                            noise=None,
                            seed=False
            )
ic = nw.attach_iclamp(name="B4",delay=2000,dur=5000)
```

We define a function in [ex5.py](examples/ex5.py) to compute the mean frequency of a spiking neuron, where a spike is detected when the voltage exceeds $-10$ mV. Then, we iterate across several values of current. We can see where the onset of spiking occurs and the relationship of spike frequency and total current injected.

```python
currents = np.linspace(0,15,num=20)
frequencies = np.zeros_like(currents)

# Do the parameter sweep
for i,amp in enumerate(currents):
    ic.amp = amp                            # Set the current amplitude
    print(f"Amplitude set to {ic.amp} nA")
    
    nw.run(voltage_only=True)               # Only record membrane voltage
    data = nw.get_cell_data("B4")           # Get data from NEURONpyxl  

    f = mean_spike_freq(data["t"],data["V"])
    frequencies[i] = f
```

See [ex5.py](examples/ex5.py) for the full simulation.

---

### Example 6: Variable input current

Just like the previous example, compile the mod files and construct the Network.

```bash
neuronpyxl -f gen_mods --file sheets/single_neuron2.xlsx
```

```python
filepath = "./sheets/single_neuron2.xlsx"
nw = Network(params_file=filepath,
                            sim_name="nostim",
                            dt=-1,
                            integrator=2,
                            atol=1e-5,
                            eq_time=1000,
                            simdur=10000,
                            noise=None
            )

ic = nw.attach_iclamp(name="B4",delay=0,dur=1e9)
```

Next, define a sinusoidal current with frequency 0.5 Hz and amplitude 2 nA.

```python
f = 0.5                     # Frequency in Hz
w = 2 * np.pi * f / 1000    # Angular frequency in rad/ms
A = 2                       # Current amplitude in nA
t = np.linspace(nw.eq_time,nw.simdur+nw.eq_time,10000)
sin_current = A * np.sin(w*t) + A

# Convert time series to hoc Vector
tvec = h.Vector(t)
ivec = h.Vector(sin_current)
```

Now, play the current vector into the amplitude of the current clamp.

```python
ivec.play(ic._ref_amp, tvec, True)
```

Run the simulation, get the data and plot.

```python
nw.run()
B4_data = pd.DataFrame(nw.get_cell_data("B4"))
t = B4_data["t"] / 1000

fig,axs = plt.subplots(2,1,figsize=(12,8),sharex=True)
axs[0].plot(t,B4_data["V"])
axs[0].set_ylabel("Voltage (mV)")

axs[1].plot(t,B4_data["I_app"])
axs[1].set_ylabel("Applied current (nA)")

fig.supxlabel("Time (s)")
fig.suptitle("B4 Neuron with Oscillatory Current")

plt.show()
```

See [ex6.py](examples/ex6.py) for the full simulation.

---

## Further Reading

- [NEURONpyxl paper](https://google.com)
- [README](./README.md)
- [NEURON tutorials](https://neuron.yale.edu/docs)
- [Source Code](../neuronpyxl)