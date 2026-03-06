import pandas as pd
import matplotlib.pyplot as plt

filepath = "./Data/example1/excitability_data.h5" # path to the data file that was generated
file = pd.HDFStore(filepath) # Read in the data file
keys = file.keys()
print(f"File {filepath} has keys: {[k.replace("/","") for k in keys]}") # Print keys in the data file

B4_data = file["B4"] # Get the data corresponding to the B4 neuron
B4_data # View all data corresponding to the B4 neuron

# Plot the voltage data
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