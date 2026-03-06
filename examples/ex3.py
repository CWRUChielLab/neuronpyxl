import matplotlib.pyplot as plt
from neuronpyxl import network
from neuron import h


# --- Simulation Setup ---
filepath = "./sheets/fig5.xlsx"
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

# --- Recording Setup ---
# nw.cells maps cell names to Cell objects (see cell.py)
# nw.chemical_synapses is structured as: speed -> pre cell -> post cell -> synapses
seg_a = nw.cells["A"].section(0.5)
cell_A = nw.cells["A"]
synw = nw.chemical_synapses["fast"]["A"]["B"]["synapse"]

Ana_rec = h.Vector().record(seg_a._ref_A_neuronpyxl_na)  # Na activation
nai_rec = h.Vector().record(seg_a._ref_nai)              # Internal Na concentration
Atsyn_rec = h.Vector().record(synw._ref_At)              # Synaptic time-dependent activation
t_rec = h.Vector().record(h._ref_t)                      # Time

# --- Run Simulation ---
# record_none=True skips default recordings to conserve memory
nw.run(record_none=True)

# --- Post-Processing ---
# Convert to numpy and trim equilibration period
# (nw.noise_eq_time is 0 when noise=None)
t = t_rec.as_numpy()
mask = t > nw.eq_time + nw.noise_eq_time

t = (t[mask] - t[mask][0]) / 1000  # Shift to start at 0 and convert ms -> s
Ana = Ana_rec.as_numpy()[mask]
nai = nai_rec.as_numpy()[mask]
Atsyn = Atsyn_rec.as_numpy()[mask]

# --- Plotting ---
fig, axs = plt.subplots(3, 1, figsize=(12, 8), sharex=True, constrained_layout=True)

axs[0].plot(t, Atsyn)
axs[0].set_ylabel("Time-dependent Synaptic Activation")

axs[1].plot(t, nai)
axs[1].set_ylabel("Internal Na Concentration (mM)")

axs[2].plot(t, Ana)
axs[2].set_ylabel("Na Activation")

fig.supxlabel("Time (s)")
plt.show()