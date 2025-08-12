import numpy as np
import os
import scienceplots
import matplotlib.pyplot as plt
plt.style.use(['no-latex','notebook'])

excelpath = "./Excel_files"
excelfile = "fig5-fig9.xlsx"

# Optionally compile the mode files here
import subprocess
subprocess.run(f"yes | neuronpyxl -f gen_mods --file {os.path.join(excelpath,excelfile)}", shell=True, check=True)

from neuronpyxl import network

freq = 500
weight = 1e-3
tau = 5

nb = network.Network(
        params_file=os.path.join(excelpath,excelfile),
        sim_name="nostim",
        noise=None,
        dt=-1,
        integrator=2,
        atol=1e-5,
        seed=True,
        eq_time=5000,
        simdur=10000
        )

nb.run()
rest_potential = nb.get_cell_data("B4")["V"][-1]
print(f"Rest potential: {rest_potential} mV")

nb_noisy = network.Network(
        params_file=os.path.join(excelpath,excelfile),
        sim_name="nostim",
        noise=(freq,weight,tau),
        dt=-1,
        integrator=2,
        atol=1e-5,
        seed=True,
        eq_time=1000,
        simdur=50000
        )
nb_noisy.run()

data = nb_noisy.get_cell_data("B4")
t = data["t"] / 1000
v = data["V"]
inoise = data["I_cap"]

from scipy.optimize import curve_fit

def gauss(x, A, mu, sigma):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

def gaussian_fit(counts,bins,data):    
    # Bin centers
    bin_centers = 0.5*(bins[1:] + bins[:-1])

    # Fit Gaussian
    # Initial guess
    p0 = [1., np.mean(data), np.std(data)]

    # Fit
    popt, _ = curve_fit(gauss, bin_centers, counts, p0=p0)
    x_fit = np.linspace(min(bins), max(bins), 100)
    
    return x_fit, *popt

fig, axs = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True,width_ratios=[1.5,1])
vcounts, vbins, _ = axs[0, 1].hist(v, bins=30, color='dodgerblue', edgecolor='white',
                                   alpha=0.8,orientation="horizontal", density=True)
icounts, ibins, _ = axs[1, 1].hist(inoise, bins=30, color='dodgerblue', edgecolor='white',
                                   alpha=0.8,orientation="horizontal", density=True)
ifit, iA, imean, istd = gaussian_fit(icounts, ibins, inoise)
vfit, vA, vmean, vstd = gaussian_fit(vcounts, vbins, v)

# Plot voltage trace
axs[0,0].plot(t, v, color="red", linewidth=1,alpha=0.8)
axs[0,0].set_ylabel("Membrane potential (mV)")

# Plot noisy current trace
axs[1,0].plot(t, inoise, color="red", linewidth=1,alpha=0.8)
axs[1,0].set_ylabel("Membrane current (nA)")
axs[1,0].set_xlabel("Time (s)")
axs[0,0].hlines([rest_potential],0,50,linestyle="dashed",linewidth=1,colors="black")
axs[1,0].hlines([0],0,50,linestyle="dashed",linewidth=1,colors="black")

axs[0, 0].set_yticks([-62.6, -62.5, -62.4, -62.3, -62.2])
axs[1, 0].set_yticks([-0.2, -0.1, 0.0, 0.1, 0.2])
# Plot histograms

axs[1, 1].set_xlabel("Relative frequency")

# Fit and plot Gaussian curves

axs[0, 1].plot(gauss(vfit, vA, vmean, vstd), vfit, 'r--', label="Gaussian fit")
axs[1, 1].plot(gauss(ifit, iA, imean, istd), ifit, 'r--', label="Gaussian fit")

# Remove yticks for right column
for i in range(2):
    axs[i, 1].set_yticks([])

axs[0,1].set_xlim(axs[1,1].get_xlim())
# Hide tick labels for top row (except bottom row keeps x-labels)
for j in range(2):
    axs[0, j].set_xticks([])

# Spine cleanup: keep only outer spines
for i in range(2):
    for j in range(2):
        ax = axs[i, j]
        for spine_pos in ['top', 'right']:
            ax.spines[spine_pos].set_visible(False)
        if j != 0:
            ax.spines['left'].set_visible(False)
        if i != 1:
            ax.spines['bottom'].set_visible(False)
fig.align_ylabels()
plt.show()

fig.savefig("figs/Dickman_etal_Results_noise.jpg", bbox_inches="tight", dpi=300)

voltage_bias = vmean - rest_potential
current_bias = imean
print(f"Number of samples: {len(t)}")
print(f"Voltage bias = {voltage_bias} mV")
print(f"Current bias = {current_bias} nA")

