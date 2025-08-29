# To compile the mod files, run neuronpyxl -f gen_mods --file Excel_files/fig8.xlsx

import pandas as pd
import scienceplots
import matplotlib.pyplot as plt
import sys
sys.path.append("../")
from neuronpyxl import network
import numpy as np
import math
import os

snnapdatapath = "/media/uri/uri-external-drive/SNNAP_data/fig8"
excelpath = "./Excel_files"
figpath = "./figs"
fig_prefix = "Dickman_etal_Results"
excelfile = "fig8.xlsx"

def remove_axes(ax,remove_x=True,remove_y=False):
    # For aesthetics
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if remove_x:
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks([])
    if remove_y:
        ax.spines['left'].set_visible(False)
        ax.set_yticks([])
        
def plot_vertical_scalebar(ax,scalebar_length=20,bar_width=0.25,offset=0,yoffset=10):
    from matplotlib.patches import Rectangle
    # Get axis limits
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Coordinates for bottom-right corner
    x_start = xlim[1] - offset - bar_width
    y_start = ylim[0] + offset + yoffset

    scalebar = Rectangle((x_start, y_start), width=bar_width, height=scalebar_length,
                        color='black', linewidth=0, zorder=10)

    ax.add_patch(scalebar)

    # Optional: Add text label
    ax.text(x_start-1, y_start + scalebar_length / 2, f'{scalebar_length} mV',
            va='center', ha='right', color='black', fontsize=16)

if __name__ == "__main__":

    fs = 16
    lw = 2

    snnap_data = pd.read_csv(os.path.join(snnapdatapath,"synapse_vsyn2.smu.out"), sep="\t").dropna(axis=1)
    snnap_data.columns = ["t", "VA", "VB"]
    nw = network.Network(params_file=os.path.join(excelpath, excelfile), sim_name="main",
                                noise=None,dt=0.01,integrator=2,atol=1e-5,eq_time=0,simdur=6000,seed=False)

    nw.run(voltage_only=True)

    tvec = np.array(snnap_data["t"])*1000
    A = nw.get_interpolated_cell_data("A",tvec)
    B = nw.get_interpolated_cell_data("B",tvec)
    t = np.array(A["t"]) / 1000

    times = np.array([(850, 1000), (1350, 1500), (1850, 2000), (2350, 2500), (2850, 3000), (3350, 3500), (3850, 4000), (4350, 4500), (4850, 5000)])
    dt = 0.005
    # Convert times to indices directly
    indices = (times / dt).astype(int)

    from matplotlib import colormaps
    cmap = colormaps['coolwarm']
    colors = [cmap(i/9) for i in range(9)]  # 10 colors from the colormap

    amps_snnap = []
    Vs_snnap = []

    fig, (ax1,ax2) = plt.subplots(1, 2, figsize=(14, 7),width_ratios=[1.4,1])

    # Plot in a single loop without building the ranges list
    # for i,(start, end) in enumerate(indices):
    #     x = np.asarray(snnap_data["t"][start:end-15]*1000 - snnap_data["t"][start]*1000)
    #     y = np.asarray(snnap_data["VB"][start:end-15] - snnap_data["VB"][start])
    #     Vs_snnap.append(snnap_data["VB"][start])
    #     amps_snnap.append(max(y))
    #     ax1.plot(x, y, label=f'{math.floor(snnap_data["VB"][end])}',color="grey",linewidth=lw,zorder=2,linestyle="dotted",alpha=0.5)
        
    # ax2.plot(Vs_snnap, amps_snnap,color="grey",linestyle="dashed",linewidth=lw)
    # ax2.scatter(Vs_snnap, amps_snnap,color="grey",marker="o",s=80,zorder=2,edgecolors="none")
    amps_nrn = []
    Vs_nrn = []

    # Plot in a single loop without building the ranges list
    for i,(start, end) in enumerate(indices):
        x = np.asarray(B["t"][start:end] - B["t"][start])
        y = np.asarray(B["V"][start:end] - B["V"][start])
        Vs_nrn.append(B["V"][start])
        amps_nrn.append(max(y))
        ax1.plot(x,y, label=f'{math.floor(B["V"][end])}',color=colors[i],linewidth=lw,zorder=1)
    

    ax2.plot(Vs_nrn, amps_nrn,color="black",linewidth=lw,linestyle="dashed",zorder=0)
    ax2.scatter(Vs_nrn, amps_nrn,color=colors,marker="o",s=80,zorder=1,edgecolors="black")
    ax2.set_xlabel("Holding potential (mV)",fontsize=fs)
    ax2.set_xticks([-90,-70,-50,-30,-10])
    ax1.set_xlabel("Time (ms)",fontsize=16)
    ax1.set_xticks([0,30,60,90,120,150])

    remove_axes(ax1,remove_x=False,remove_y=False)
    remove_axes(ax2,remove_x=False,remove_y=True)

    ax1.set_ylabel(r"$V_i(t)-V_i(0)$ (mV)",fontsize=16)
    ax1.set_yticks([0,0.1,0.2,0.3,0.4])
    ax2.set_ylim(ax1.get_ylim())
    ax1.tick_params(axis="y", labelsize=16)
    ax1.tick_params(axis='x', labelsize=16)
    ax2.tick_params(axis='x', labelsize=16)

    # ax1.set_title("Post-synaptic Potential",fontsize=20)
    # ax2.set_title("PSP Amplitude",fontsize=20)
    # axs[0, 0].legend(title='Holding potential',fontsize=12,bbox_to_anchor=(-0.5,0.5),loc="center left",title_fontsize='medium')
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(
        handles[::-1], labels[::-1],
        title="Holding potential",
        title_fontsize='xx-large',
        fontsize=20,
        loc="center left",
        bbox_to_anchor=(1, 0.7),  # tweak these values for fine placement
        frameon=False,
        borderaxespad=0,
        ncol=1,
        bbox_transform=fig.transFigure
    )

    # plot_vertical_scalebar(axs[1,1],scalebar_length=0.1,bar_width=0.4,yoffset=0.05)
    fig.tight_layout(pad=3.0)
    fig.align_ylabels()
    plt.show()
    fig.savefig(os.path.join(figpath,f"{fig_prefix}_psp.jpg"), dpi=300, bbox_inches='tight')
