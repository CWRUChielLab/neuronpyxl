# To compile the mod files, run neuronpyxl -f gen_mods --file Excel_files/fig6.xlsx

import sys
import os
sys.path.append("../")
import scienceplots
import pandas as pd
import matplotlib.pyplot as plt
from neuronpyxl import network
plt.style.use(["no-latex", "notebook"])

snnapdatapath = "/media/udickman/uri-external-drive/SNNAP_data/fig6"
excelpath = "./Excel_files"
figpath = "./figs"
fig_prefix = "Dickman_etal_Results"
excelfile = "fig6.xlsx"

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
        
def plot_vertical_scalebar(ax,scalebar_length=20,bar_width=0.25,xoffset=1,yoffset=10):
    from matplotlib.patches import Rectangle
    # Get axis limits
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Coordinates for bottom-right corner
    x_start = xlim[1] - bar_width - xoffset
    y_start = ylim[0] + yoffset

    scalebar = Rectangle((x_start, y_start), width=bar_width, height=scalebar_length,
                        color='black', linewidth=0, zorder=10)

    ax.add_patch(scalebar)

    # Optional: Add text label
    ax.text(x_start-xoffset, y_start + scalebar_length / 2, f'{scalebar_length} mV',
            va='center', ha='right', color='black', fontsize=16)
    
if __name__ == "__main__":

    lw = 3
    fs = 14
    
    nw = network.Network(params_file=os.path.join(excelpath, excelfile),\
                          sim_name="synapse",noise=None,dt=-1,integrator=2,\
                          atol=1e-5,eq_time=1000,simdur=9000,seed=False) 
    nw.run(voltage_only=True)

    dataA = nw.get_cell_data("A")
    dataB = nw.get_cell_data("B")

    snnap_data = pd.read_csv(os.path.join(snnapdatapath,"synapse.smu.out"),header=None,sep="\t").drop(3,axis=1)
    snnap_data.columns = ["t","VA","VB"]
    snnap_data = snnap_data[snnap_data["t"] >= 1]
    snnap_data["t"] -= 1
    snnap_data = snnap_data[snnap_data["t"] <= 9]
    snnapcolor = "dodgerblue"
    nrncolor = "orangered"

    fig,(ax1,ax2) = plt.subplots(2,1,figsize=(14,10),height_ratios=(1,1))

    ax1.plot(dataA["t"]/1000,dataA["V"],color=nrncolor,linestyle="solid",label="NEURON",linewidth=lw)
    ax1.plot(snnap_data["t"],snnap_data["VA"],color=snnapcolor,linestyle="dashed",label="SNNAP",linewidth=lw) 
    ax1.set_ylim((-80,40))
    ax1.set_xlim((0,10))
    # ax1.set_ylabel("Neuron A",rotation=0,fontsize=20)
    remove_axes(ax1,True,True)
    ax1.legend(frameon=False,fontsize=20)


    ax2.plot(dataB["t"]/1000,dataB["V"],color=nrncolor,linestyle="solid",linewidth=lw)
    ax2.plot(snnap_data["t"],snnap_data["VB"],color=snnapcolor,linestyle="dashed",linewidth=lw) 
    ax2.set_ylim((-80,40))
    # ax2.set_ylabel("Neuron B",rotation=0,fontsize=20)
    ax2.set_xlabel("Time (s)", fontsize=fs)
    ax2.set_xlim((0,10))
    ax2.set_xticks([0,0.5])
    remove_axes(ax2,False,True)
    plot_vertical_scalebar(ax2,scalebar_length=20,bar_width=0.025,\
            xoffset=0.1,yoffset=10)
                           #plot_vertical_scalebar(ax2)
    plt.show() 
    fig.savefig(os.path.join(figpath,f"{fig_prefix}_es.jpg"),bbox_inches="tight",dpi=300)
