"""
Ex 4: Start a simulation from a saved state

Save the state, then re-construct the network
in the same way as it was saved. Then, re-run
the network starting from where you left off.

First, generate the mod files by running:
    neuronpyxl -f gen_mods --file sheets/small_network.xlsx
Then run this file with:
    python examples/ex4.py
"""

from neuron import h
from neuronpyxl import Network
import matplotlib.pyplot as plt

filepath = "./sheets/small_network.xlsx"

# Comment below after saving the state
nw = Network(params_file=filepath,
                            sim_name="synapse",
                            dt=-1,
                            integrator=2,
                            atol=1e-5,
                            eq_time=2500,
                            simdur=13000,
                            noise=None,
                            seed=False
                            )

nw.run(voltage_only=True)
nw.save_state(filename="state.bin")

# Uncomment below after saving the state
#
# Set up the simulation exactly the same as before
# filepath = "./sheets/small_network.xlsx"
# nw_restored = Network(params_file=filepath,
#                             sim_name="synapse",
#                             dt=-1,
#                             integrator=2,
#                             atol=1e-5,
#                             eq_time=2500,
#                             simdur=13000,
#                             noise=None,
#                             seed=False
#               )
# nw_restored.record_voltage_only() # We also need to set up the recordings the same
# nw_restored.restore_state(filename="state.bin")

# ic = nw_restored.attach_iclamp(name="B",delay=h.t-nw_restored.eq_time,dur=5000,amp=2)

# h.cvode_active(1)
# h.cvode.re_init()
# h.continuerun(h.t + 5000) # Run for another 5000 ms

# A_data = nw_restored.get_cell_data("A")
# B_data = nw_restored.get_cell_data("B")
# C_data = nw_restored.get_cell_data("C")
# t = A_data["t"]

# fig,axs = plt.subplots(3,1,figsize=(12,8),constrained_layout=True,sharex=True,sharey=True)
# axs[0].plot(A_data["t"],A_data["V"])
# axs[0].set_ylabel("V_A (mV)")
# axs[1].plot(B_data["t"],B_data["V"])
# axs[1].set_ylabel("V_B (mV)")
# axs[2].plot(C_data["t"],C_data["V"])
# axs[2].set_ylabel("V_B (mV)")
# axs[2].set_xlabel("Time (ms)")
# plt.show()