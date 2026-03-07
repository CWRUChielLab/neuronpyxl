"""
Ex 6: Variable current injection

Plot voltage vs. current injected for a single
spiking neuron with complex channel and ion pool dynamics,
using a variable current source.

First, generate the mod files by running:
    neuronpyxl -f gen_mods --file sheets/single_neuron2.xlsx
Then run this file with:
    python examples/ex6.py
"""

from neuron import h
from neuronpyxl import Network
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

filepath = "./sheets/single_neuron2.xlsx"
nw = Network(params_file=filepath,
                            sim_name="nostim",
                            dt=-1,
                            integrator=3,
                            atol=1e-5,
                            eq_time=1000,
                            simdur=10000,
                            noise=None
            )

ic = nw.attach_iclamp(name="B4",delay=0,dur=1e9)

# Define sinusoidal current with frequency 0.5 Hz
f = 0.5                     # Frequency in Hz
w = 2 * np.pi * f / 1000    # Angular frequency in rad/ms
A = 2                       # Current amplitude in nA
t = np.linspace(nw.eq_time,nw.simdur+nw.eq_time,10000)
sin_current = A * np.sin(w*t) + A

# Convert time series to hoc Vector
tvec = h.Vector(t)
ivec = h.Vector(sin_current)

# Play current vector into IClamp amplitude hoc pointer
# 3rd argument => NEURON interpolates current at the internal timestep using tvec
ivec.play(ic._ref_amp, tvec, True)

nw.run()    # Default is record all current and voltages
B4_data = pd.DataFrame(nw.get_cell_data("B4"))
t = B4_data["t"] / 1000

# Plot
fig,axs = plt.subplots(2,1,figsize=(12,8),sharex=True)
axs[0].plot(t,B4_data["V"])
axs[0].set_ylabel("Voltage (mV)")

axs[1].plot(t,B4_data["I_app"])
axs[1].set_ylabel("Applied current (nA)")

fig.supxlabel("Time (s)")
fig.suptitle("B4 Neuron with Oscillatory Current")

plt.show()