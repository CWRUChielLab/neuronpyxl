# To compile the mod files, neuronpyxl -f gen_mods --file Excel_files/fig7.xlsx

import sys
import os
sys.path.append("../")
import pandas as pd
import scienceplots
import matplotlib.pyplot as plt
import numpy as np
from neuronpyxl import network
plt.style.use(["no-latex", "notebook"])

snnapdatapath = "/media/uri/uri-external-drive/SNNAP_data/fig7"
excelpath = "./Excel_files"
figpath = "./figs"
fig_prefix = "Dickman_etal_Results"
excelfile = "fig7.xlsx"

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
        
def plot_vertical_scalebar(ax,scalebar_length=20,bar_width=0.25,offset=0,xoffset=1,yoffset=10):
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
    # ax.text(x_start-xoffset, y_start + scalebar_length / 2, f'{scalebar_length} mV',
    #         va='center', ha='right', color='black', fontsize=16)
    
if __name__ == "__main__":

    fs = 14
    lw = 3

    snnap_data = pd.read_csv(os.path.join(snnapdatapath,"synapse.smu.out"), sep="\t").dropna(axis=1)
    snnap_data.columns = ["t", "V_A", "nai_A", "V_B", "nai_B", "V_C", "nai_C"]
    tsnnap = np.asarray(snnap_data["t"])

    nw = network.Network(params_file=os.path.join(excelpath, excelfile), sim_name="synapse",
                                noise=None,dt=-1,integrator=2,atol=1e-5,eq_time=5000,simdur=13000,seed=False)

    nw.run(voltage_only=True)

    A = nw.get_cell_data("A")
    B = nw.get_cell_data("B")
    C = nw.get_cell_data("C")
    t = np.array(A["t"]) / 1000

    colors = ["red", "teal", "orchid"]
    snnapcolor = "dodgerblue"
    nrncolor = "orangered"
    dx = 0.6
    cells = {"A": {"snnap": snnap_data["V_A"], "neuron": A["V"]},
             "B": {"snnap": snnap_data["V_B"], "neuron": B["V"]},
             "C": {"snnap": snnap_data["V_C"], "neuron": C["V"]}
            }
    xranges = [(1-dx,4+dx+0.1), (5-dx,8+dx+0.1), (9-dx,12+dx+0.1)]
    yrange1 = (-80,40)
    yrange2 = (-90,-60)

    fig, axs = plt.subplots(3, 3, figsize=(14,10))

    for i, (cell_name, series) in enumerate(cells.items()):
        for j, xlim in enumerate(xranges):
            ax = axs[i,j]

            # Plot
            ax.plot(t, series["neuron"], color=nrncolor, lw=lw)
            ax.plot(tsnnap, series["snnap"], color=snnapcolor, lw=lw,linestyle="dashed")

            # Apply x-limits for column
            ax.set_xlim(xlim)

            # Apply y-limits depending on diagonal or not
            if i == j:  # diagonal
                ax.set_ylim(yrange1)
            else:
                ax.set_ylim(yrange2)

            # Label rows/cols
            # if i == 0:
            #     ax.set_title(f"Range {xlim}")
            # if j == 0:
            #     ax.set_ylabel(cell_name)
            
            remove_axes(ax,remove_x=True,remove_y=True)

    plot_vertical_scalebar(axs[2,2],scalebar_length=50,bar_width=0.05,offset=0,xoffset=0.05,yoffset=20)
    plot_vertical_scalebar(axs[0,2],scalebar_length=10,bar_width=0.05,offset=0,xoffset=0.05,yoffset=0)

    axs[2,1].set_xticks([5,6,7])

    fig.subplots_adjust(wspace=0.2, hspace=0.2)

    plt.show()

    fig.savefig(os.path.join(figpath,f"{fig_prefix}_network_plast.jpg"), bbox_inches="tight",dpi=300)








    # fig, ax = plt.subplots(3, 1, figsize=(14,10),constrained_layout=True)
    # ax[0].plot(t, A["V"], color=nrncolor,label="NEURON",linewidth=lw)
    # ax[0].plot(tsnnap, snnap_data["V_A"], label="SNNAP", color=snnapcolor,linestyle="--",linewidth=lw)
    # # ax[0].set_ylabel("Neuron A",rotation=0,fontsize=20)
    # ax[0].legend(frameon=False,fontsize=20)

    # ax[1].plot(t, B["V"],color=nrncolor,linewidth=lw)
    # ax[1].plot(tsnnap, snnap_data["V_B"], color=snnapcolor,linestyle="--",linewidth=lw)
    # # ax[1].set_ylabel("Neuron B",rotation=0,fontsize=20)

    # ax[2].plot(t, C["V"],color=nrncolor,linewidth=lw)
    # ax[2].plot(tsnnap, snnap_data["V_C"], color=snnapcolor,linestyle="--",linewidth=lw)
    # # ax[2].set_ylabel("Neuron C",rotation=0,fontsize=20)

    # ax[2].set_xlabel("Time (s)",fontsize=fs)
    # ax[2].set_xticks(np.arange(0,14,step=0.5))

    # for a in ax:
    #     a.set_xlim((0,13))

    # remove_axes(ax[0],remove_x=True,remove_y=True)
    # remove_axes(ax[1],remove_x=True,remove_y=True)
    # remove_axes(ax[2],remove_x=False,remove_y=True)

    # plot_vertical_scalebar(ax[2],scalebar_length=50,bar_width=0.025,xoffset=0.1,yoffset=20)
    # plt.show()
    # # plt.tight_layout(pad=2.0, w_pad=0.5, h_pad=0.5)
    # fig.savefig(os.path.join(figpath,f"{fig_prefix}_network_plast.jpg"), bbox_inches="tight",dpi=300)
