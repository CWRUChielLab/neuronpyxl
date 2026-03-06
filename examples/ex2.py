"""
Ex 2: Benchmarking simulations

Construct 2 NEURONpyxl networks: 1 with noise and one without.
Report the mean and standard deviation simulation times for each case
for 10 iterations.

First, generate the mod files by running:
    neuronpyxl -f gen_mods --file sheets/single_neuron1.xlsx
Then run this file with:
    python examples/ex2.py
"""

import numpy as np
from neuronpyxl import Network

excel_path = "sheets/single_neuron1.xlsx"
simdur = 9000
eq_time = 1000

# ---- Run simulations ---- #

N = 20
times_noisy = np.zeros(N)
times_no_noise = np.zeros(N)

nw_no_noise = Network(
        params_file=excel_path,
        sim_name="main",
        noise=None, # Without noise
        dt=-1,
        integrator=2,
        atol=1e-5,
        eq_time=eq_time,
        simdur=simdur
)

for i in range(N):
    nw_no_noise.run(record_none=True)
    times_no_noise[i] = nw_no_noise.simtime

del nw_no_noise

nw_noisy = Network(
        params_file=excel_path,
        sim_name="main",
        noise=(500,1e-3,3), # With noise: 500 Hz, 1e-3 uS weight, 3 ms time constant
        dt=-1,
        integrator=2,
        atol=1e-5,
        eq_time=eq_time,
        simdur=simdur
)

for i in range(N):
    nw_noisy.run(record_none=True)
    times_noisy[i] = nw_noisy.simtime

del nw_noisy

# ---- Calculate Mean and Std ---- #

mean_noisy = np.mean(times_noisy)
std_noisy = np.std(times_noisy)

mean_no_noise = np.mean(times_no_noise)
std_no_noise = np.std(times_no_noise)

# ---- Print Results ---- #

print("\n" + "="*50)
print("Simulation Timing Results")
print("="*50)

print(f"Number of runs: {N}")
print(f"Simulation duration: {simdur} ms")
print(f"Equilibration time: {eq_time} ms")
print("-"*50)

print("No Noise Condition")
print(f"  Mean runtime : {mean_no_noise:10.4f} s")
print(f"  Std runtime  : {std_no_noise:10.4f} s")

print("\nNoisy Condition")
print(f"  Mean runtime : {mean_noisy:10.4f} s")
print(f"  Std runtime  : {std_noisy:10.4f} s")

print("-"*50)
print("Relative slowdown (Noisy / No Noise): "
      f"{mean_noisy / mean_no_noise:6.3f}×")
print("="*50 + "\n")