# To compile the mod files, run neuronpyxl -f gen_mods --file Excel_files/fig5-fig9.xlsx

import sys
import os
sys.path.append("../")
import scienceplots
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from neuronpyxl import network
from neuron import h
plt.style.use(["no-latex", "notebook"])

snnapdatapath = "/media/udickman/uri-external-drive/SNNAP_data/fig5"
excelpath = "./Excel_files"
figpath = "./figs"
fig_prefix = "Dickman_etal_Results"
excelfile = "fig5-fig9.xlsx"

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
        
def plot_vertical_scalebar(ax,scalebar_length=10,bar_width=0.25,offset=0,yoffset=10,xoffset=0,textoffset=0.001):
    from matplotlib.patches import Rectangle
    # Get axis limits
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Coordinates for bottom-right corner
    x_start = xlim[1] - offset - bar_width + xoffset
    y_start = ylim[0] + offset + yoffset

    scalebar = Rectangle((x_start, y_start), width=bar_width, height=scalebar_length,
                        color='black', linewidth=0, zorder=10)

    ax.add_patch(scalebar)

    # Optional: Add text label
    ax.text(x_start-textoffset, y_start + scalebar_length / 2, f'{scalebar_length} mV',
            va='center', ha='right', color='black', fontsize=14)
    

if __name__ == "__main__":
    nw = network.Network(params_file=os.path.join(excelpath, excelfile), sim_name="excitability",
                                noise=None,dt=-1,integrator=2,atol=1e-5,eq_time=1000,simdur=9000,seed=False)
    nw.run()
    tvec = np.arange(0,9000,step=0.05)
    data = pd.DataFrame(nw.get_interpolated_cell_data("B4",tvec))

    snnapdata = pd.read_csv(os.path.join(snnapdatapath,"excitability.smu.out"), sep="\t").dropna(axis=1).dropna(axis=0)
    snnapdata.columns = ["t", "V", "I_leak", "I_na", "I_k", "I_kcas", "cai", "I_app"]
    snnapdata = snnapdata[snnapdata["t"]>=10]
    snnapdata["t"] -= 10
    t = data["t"] / 1000
    tsnnap = np.array(snnapdata["t"])

    nw2 = network.Network(params_file=os.path.join(excelpath, excelfile), sim_name="nostim",
                                noise=None,dt=-1,integrator=2,atol=1e-5,eq_time=1000,simdur=9000,seed=False)
    ic = nw2.attach_iclamp(name="B4",delay=0,dur=1e9) 
    t0 = 2000 + nw2.eq_time
    t1 = 7000 + nw2.eq_time
    tmax = 10000 + nw2.eq_time  # example
    N = 2000                   # total resolution for the whole domain
    amp = 25

    t2 = np.linspace(0, tmax, N)

    # triangle function
    y = np.zeros_like(t2)
    mask = (t2 >= t0) & (t2 <= t1)
    mid = (t0 + t1) / 2
    y[mask] = np.where(
        t2[mask] <= mid,
        amp * (t2[mask] - t0) / (mid - t0),       # rising edge
        amp * (t1 - t2[mask]) / (t1 - mid)        # falling edge
    )

    tvec = h.Vector(t2)
    ivec = h.Vector(y)
    # Play current vector into IClamp amplitude hoc pointer (3rd argument => NEURON interpolates to the internal timestep)
    ivec.play(ic._ref_amp, tvec, True)
    nw2.run()
    B4_data = pd.DataFrame(nw2.get_cell_data("B4"))

    fig = plt.figure(figsize=(14, 10), constrained_layout=True)
    subfigs = fig.subfigures(2, 1, height_ratios=[1.5, 1])
    sfigs1 = subfigs[0].subfigures(1, 2, width_ratios=[2, 1.2])
    sfigs2 = subfigs[1]
    ax1 = sfigs1[0].subplots(3, 1)   # left subfigure: 3 rows × 1 col
    ax2 = sfigs1[1].subplots(1, 1)   # right subfigure: 1 plot
    ax3 = sfigs2.subplots(1,1)      # bottom: 1 plot

    snnapcolor = "dodgerblue"
    nrncolor = "orangered"
    lw = 3
    fs=14

    ax1[0].plot(t,data["V"],color=nrncolor,linewidth=lw)
    ax1[0].plot(tsnnap,snnapdata["V"],color=snnapcolor,linestyle="dashed",linewidth=lw)
    ax1[0].set_ylabel("Voltage (mV)",fontsize=fs)
    remove_axes(ax1[0])
    ax1[1].plot(t,data["I_kcas"],color=nrncolor,linewidth=lw)
    ax1[1].plot(tsnnap,snnapdata["I_kcas"],color=snnapcolor,linestyle="dashed",linewidth=lw)
    ax1[1].set_ylabel(r"$I_{K_{Ca,s}}$ (nA)",fontsize=fs)
    remove_axes(ax1[1])
    ax1[2].plot(t,data["cai"]*1e6,color=nrncolor,linewidth=lw)
    ax1[2].plot(tsnnap,snnapdata["cai"],color=snnapcolor,linestyle="dashed",linewidth=lw)
    ax1[2].set_ylabel(r"$[Ca]_i$ (nM)",fontsize=fs)
    ax1[2].set_xlabel("Time (s)",fontsize=fs)
    remove_axes(ax1[2],remove_x=False,remove_y=False)

    t3 = B4_data["t"]
    mask2 = (t3 > 1000) & (t3 < 8000)
    ax3.plot(B4_data["t"][mask2]/1000,B4_data["V"][mask2],color=nrncolor,linewidth=lw)
    # ax3.set_ylabel("Voltage (mV)",fontsize=fs)
    ax3.set_xlabel("Time (s)",fontsize=fs)
    ax3.set_xticks([0,0.5,1,8,9])
    remove_axes(ax3,remove_x=False,remove_y=True)
    plot_vertical_scalebar(ax3,bar_width=0.02,offset=0,yoffset=10,xoffset=-0.05,scalebar_length=20,textoffset=0.05)

    start = 97600
    end = 99200
    ax2.plot(t[start:end]-t[start],data["V"][start:end],label="NEURON",color=nrncolor,linewidth=lw)
    ax2.plot(tsnnap[start:end]-tsnnap[start],snnapdata["V"][start:end],label="SNNAP",color=snnapcolor,linestyle="dashed",linewidth=lw)
    remove_axes(ax2,remove_x=False,remove_y=True)
    ax2.legend(frameon=False,fontsize=20)
    ax2.set_xlabel("Time (s)",fontsize=fs)
    plot_vertical_scalebar(ax2,bar_width=0.0005,offset=0,yoffset=2)

    # sfig_labels = ['A', 'B', 'C']

    # for subfig, label in zip([sfigs1[0],sfigs1[1],sfigs2], sfig_labels):
    #     # Add label to the upper left of each subfigure
    #     subfig.suptitle(label, x=0.0, y=1.06, ha='left', va='top', fontsize=22, fontweight='bold')
        
    sfigs1[0].align_ylabels()
    plt.show()
    fig.savefig(os.path.join(figpath,f"{fig_prefix}_regulation.jpg"),bbox_inches="tight",dpi=300)