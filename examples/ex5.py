"""
Ex 5: Basic parameter sweep.

Plot spike frequency vs. injected current for a single
spiking neuron with complex channel and ion pool dynamics.

First, generate the mod files by running:
    neuronpyxl -f gen_mods --file sheets/single_neuron2.xlsx
Then run this file with:
    python examples/ex5.py
"""

from neuronpyxl import Network
import numpy as np
import matplotlib.pyplot as plt

def mean_spike_freq(t:np.ndarray,v:np.ndarray,spike_thresh:float=-10.):
    """Function to detect spikes. Finds where the voltage crosses 
    spike_thresh from below and interpolates to find where the voltage is exactly spike_thresh. 

    Args:
        t (_type_): time vector
        v (_type_): voltage vector
        spike_thresh (int, optional): threshold to detect spikes. Defaults to -10.

    Returns:
        _type_: computed spike frequency
    """
    # Find where each spike crosses spike_thresh upwards
    crossings = np.where((v[:-1] < spike_thresh) \
                         & (v[1:] >= spike_thresh))[0]
    
    # Interpolate to get the exact spike time
    spike_times = np.zeros_like(crossings)
    for i,c in enumerate(crossings):
        spike_times[i] = np.interp(spike_thresh,v[c:c+1],t[c:c+1])

    spike_timing = np.diff(spike_times)     # time between spikes

    if len(spike_timing) == 0:              # Catch divide by 0 error
        return 0
    return 1000 / np.mean(spike_timing)     # Mean frequency in Hz


# NEURONpyxl already adds a current clamp if we are running 'excitability.smu' in the spreadsheet
# But let's use the 'nostim.smu' sheet and add our own using the nw.attach_iclamp() function
filepath = "sheets/single_neuron2.xlsx"
nw = Network(params_file=filepath,
                            sim_name="nostim",
                            dt=-1,
                            integrator=3,
                            atol=1e-5,
                            eq_time=1000,
                            simdur=9000,
                            noise=None
            )

# Attach a current clamp to the network
# Leave the amplitude as None since we will change it later
ic = nw.attach_iclamp(name="B4",delay=2000,dur=5000)

currents = np.linspace(0,15,num=20)
frequencies = np.zeros_like(currents)

for i,amp in enumerate(currents):
    ic.amp = amp                            # Set the current amplitude
    print(f"Amplitude set to {ic.amp} nA")
    
    nw.run(voltage_only=True)               # Only record membrane voltage
    data = nw.get_cell_data("B4")           # Get data from NEURONpyxl  

    f = mean_spike_freq(data["t"],data["V"])
    frequencies[i] = f

plt.plot(currents,frequencies,linestyle="dashed",color="black",linewidth=1)
plt.scatter(currents,frequencies,zorder=2,facecolor="none",edgecolors="red")
plt.xlabel("Injected Current (nA)")
plt.ylabel("Spike frequency (Hz)")
plt.show()