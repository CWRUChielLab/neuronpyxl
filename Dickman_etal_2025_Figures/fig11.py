excelpath = "/home/udickman/Desktop/projects/cwru/neuronpyxl/Excel_files"
figpath = "/home/udickman/Desktop/projects/cwru/neuronpyxl/figs"
datapath = "/home/udickman/Desktop/projects/cwru/neuronpyxl/Data"
excelfile = "fig11-12-13.xlsx"
fig_prefix = "Dickman_etal_Results"

import sys
import subprocess
import os
sys.path.append("../neuronpyxl")
subprocess.run(f"yes | neuronpyxl -f gen_mods --file {os.path.join(excelpath,excelfile)}",shell=True,check=True)

from neuronpyxl import network
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import sys
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D


def set_params(nw:network.Network,v1,v2):
    nw.cells["B64s"].section(0.5).g_neuronpyxl_kpp = v1
    nw.chemical_synapses["fast"]["B30"]["B63"]["synapse"].g = v2

legend_labels = {"forestgreen": "Control",
                 "orangered": "Protraction",
                 "purple": "Closure",
                 "teal": "Retraction",
                 "black": "Retraction terminating"
                }

colors = {
    "forestgreen": ["CBI2"], # command-like neuron
    "orangered": ["B20", "B30", "B31a", "B34", "B35", "B40", "B63"], # protraction
    "purple": ["B8"], # closure
    "teal": ["B51s", "B51a", "B64a","B4"], # retraction
    "black": ["B52"] # retraction termination
}

all_cells = [(cell, color) for color, cells in colors.items() for cell in cells]
num_cells = len(all_cells)
# folder = "Control"
# file = pd.HDFStore(os.path.join(datapath, folder, "BMP_data.h5"))
# data = file["data"]
#noise_params = None
noise_params = (200,1e-4,8)

param1 = "vdg_g_B64s_kpp"
param2 = "cs_g_B30_B63_fast"
params = {'loaded': {
                    param1: 0.7423728813559323,
                    param2: 2.535593220338983
        }, 'unloaded': {
                    param1: 1.0728813559322037,
                    param2: 1.3915254237288135
        }, 'control': {
                    param1: 0.35,
                    param2: 0.25
        
        }
}

nw = network.Network(
        params_file=os.path.join(excelpath,excelfile),
        sim_name="BMP",noise=noise_params,dt=-1,integrator=2,atol=1e-5,
        eq_time=10000,simdur=150000,seed=False
        )

condition = "control"
#set_params(nw,params[condition][param1],params[condition][param2])
nw.run(voltage_only=True)

data = {}
for name,_ in nw.cells.items():
    cell_data = nw.get_cell_data(name)
    if "t" not in data:
        data["t"] = cell_data["t"]
    data[f"V_{name}"] = cell_data["V"]


import matplotlib.ticker as ticker
def xtickson(ax,ticks):
    ax.tick_params(axis='x', which='both', bottom=True, top=False)
    ax.spines["bottom"].set_visible(True)
    # Specify number of ticks on x-axis
    ax.set_xticks(ticks)

def ylabel(ax,text):
    ax.text(-0.05, 0.5, text, transform=ax.transAxes,
        rotation=0, va='center', ha='center', fontsize=18)

def plot_bmps(data,axs,all_cells,xlim=(0,65),snnap=True,ylab=False):
    if num_cells == 1:
        axs = [axs]  # Ensure axes is a list when there's only one subplot
    t = np.array(data["t"])
    if not snnap:
        t /= 1000

    # Plot data from each cell
    for ax, (cell, color) in zip(axs, all_cells):
        if snnap:
            ind = np.where(t > 10)[0]
            t = np.array(t[ind])
            t -= t[0]
            V = data[f"V_{cell}"][ind]
        else:
            V = data[f"V_{cell}"]
        
        ax.plot(t, V, color=color, linewidth=1,label=None)
        ax.spines['left'].set_visible(False)
        ax.set_yticks([])
        ax.set_xlim(xlim)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks([])
        if ylab:
            ylabel(ax,cell)


def plot_vertical_scalebar(ax,scalebar_length=100,bar_width=0.25,xoffset=0,yoffset=0):
    from matplotlib.patches import Rectangle
    # Get axis limits
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Coordinates for bottom-right corner
    x_start = xlim[1] + xoffset - bar_width
    y_start = ylim[0] + yoffset

    scalebar = Rectangle((x_start, y_start), width=bar_width, height=scalebar_length,
                        color='black', linewidth=0, zorder=10)

    ax.add_patch(scalebar)

    # Optional: Add text label
    ax.text(x_start - 1, y_start + scalebar_length / 2, f'{scalebar_length} mV',
            va='center', ha='right', color='black', fontsize=12)
            
            
fig,ax = plt.subplots(num_cells,1,figsize=(12,10),sharey=True,constrained_layout=True)
plot_bmps(data,ax,all_cells, (0,nw.simdur/1000),False,True)
xtickson(ax[-1],[0,30,60,90,120,150])
plot_vertical_scalebar(ax[-2],yoffset=0)
fig.supxlabel("Time (s)",x=0.53,y=0.04)

for color, label in legend_labels.items():
    ax[-1].plot([], [], color=color, label=label,linewidth=2)

# Add legend at the bottom center, in one row
ax[-1].legend(
    loc='upper center',
    bbox_to_anchor=(0.5, -1.2),  # Centered, adjust vertical position if needed
    ncol=len(legend_labels),     # All in one row
    frameon=False                 # Optional: removes legend box
)

fig.savefig(os.path.join(figpath,f"{fig_prefix}_cpg_updated{'' if noise_params is None else '_noise'}.jpg"),dpi=300)
plt.show()
