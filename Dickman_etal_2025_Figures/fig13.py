import pandas as pd
import scienceplots
import matplotlib.pyplot as plt
import sys
import numpy as np
import os
import pandas as pd
plt.style.use(["no-latex", "notebook"])
datapath = os.path.join(os.getcwd(),"Dickman_etal_2025_Figures/Data/fig12-13")
sys.path.append(datapath)
figpath = "figs"
sys.path.append(figpath)
fig_prefix = "Dickman_etal_Results"

def remove_axes1(ax):
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def remove_axes2(ax, x=False):
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(x)
    ax.set_yticks([])
    ax.tick_params(right=False,top=False,left=False,bottom=x)

tick_fontsize = 22
label_fontsize = 22
title_fontsize=22
legend_fontsize=22

fig = plt.figure(figsize=(14,10),constrained_layout=True)
sfigs = fig.subfigures(1,2, width_ratios=(2,1.25))
ax1 = sfigs[1].subplots(1,1)
ax2 = sfigs[0].subplots(2,2,sharey=True,sharex=True)

# FIRST RUN bmp_test.py
speed = "slow"
############################### BARCHART ####################################
chiel_data = pd.read_csv(os.path.join(datapath,"gillchiel_2020_data.csv"), header=[0,1,2])
mean_data = pd.read_csv(os.path.join(datapath,"meandur.csv"), index_col=[0,1,2]).T

groups = ["protraction","retraction"]
pairs = ["Data", "CPG"]
conditions = ["loaded","unloaded"]
colors = {"loaded": "mediumspringgreen", "unloaded": "fuchsia"}  # color by species
hatches = {"Data": "", "CPG": "//"}  # hatch by dataset
data = {}
for s in conditions:
    data.setdefault(s,{})
    for phase in groups:
        d = np.mean(chiel_data[(s,phase)]["dur"])
        e = np.sqrt(np.sum(np.square(chiel_data[(s,phase)]["err"])))
        data[s].setdefault(phase,{})
        data[s][phase] = {"dur": d,
                          "err": e}
cpg = {}
for s in conditions:
    cpg.setdefault(s,{})
    for phase in groups:
        d = np.mean(mean_data[(s,phase,"dur")])/1000
        e = np.mean(mean_data[(s,phase,"err")])/1000
        cpg[s].setdefault(phase,{})
        cpg[s][phase] = {"dur": d,
                        "err": e}

all_data = {
    "Data": data,
    "CPG": cpg
}


x = np.array([0,1])
width = 0.2
x_tick_positions = x + width / 2 - 0.1
# total_bars = len(conditions) * len(datasets)
ec = "black"
alpha = 0.7
num_datasets = len(pairs) * len(conditions)
bar_width = 0.15
group_offset = (num_datasets - 1) * bar_width / 2  # to center the bars

for i, group in enumerate(groups):  # protraction, retraction
    bar_count = 0
    for j, condition in enumerate(conditions):  # loaded, unloaded
        for k, dataset in enumerate(pairs):  # Data, CPG, SNNAP
            xpos = x[i] - group_offset + bar_count * bar_width
            ax1.bar(
                xpos,
                all_data[dataset][condition][group]["dur"],
                bar_width,
                color=colors[condition],
                hatch=hatches[dataset],
                yerr=all_data[dataset][condition][group]["err"],
                error_kw=dict(ecolor=ec, linewidth=1),
                capsize=4,
                edgecolor=ec,
                alpha=alpha
            )
            bar_count += 1
# Formatting
ax1.set_xticks(x_tick_positions)
ax1.set_xticklabels([g.capitalize() for g in groups], ha="center")
ax1.tick_params(axis='x', length=0)
ax1.set_yticks([0,1,2,3,4])
ax1.set_ylabel("Duration (s)")

from matplotlib.patches import Patch

legend_patches = [
    Patch(facecolor=colors["loaded"], edgecolor=ec,label="Loaded"),  # Solid blue
    Patch(facecolor=colors["unloaded"], edgecolor=ec, label="Unloaded"),  # Striped red,
    Patch(facecolor="white", edgecolor=ec, hatch="//", label="Simulation"),  # Solid blue
    # Patch(facecolor="white", edgecolor=ec, hatch="x", label="SNNAP"),  # Solid blue
    Patch(facecolor="white", edgecolor=ec, label="Experiment")  # Striped red,
]

ax1.legend(handles=legend_patches,loc="upper left",frameon=False)
remove_axes1(ax1)

############################### ALIGNED ####################################


#data_control = pd.read_csv(os.path.join(datapath, f"data_test_control.csv")).drop(["Unnamed: 0"], axis=1)
data_l = pd.read_csv(os.path.join(datapath, f"data_test_loaded.csv")).drop(["Unnamed: 0"], axis=1)
data_ul = pd.read_csv(os.path.join(datapath, f"data_test_unloaded.csv")).drop(["Unnamed: 0"], axis=1)


def align_time(x,y,start_time,delta=10000):
    x_shifted = x - start_time
    mask = (x_shifted >= -delta) & (x_shifted <= delta)
    return x_shifted[mask]/1000, y[mask]

def bmp_times(x,y,alignment):
    zeros = np.where(np.diff(np.signbit(y)))[0]
    zero_times = np.array(x[zeros])
    i_end = np.where(np.diff(zero_times) > 4000)[0]
    bmp_end = zero_times[i_end][1]
    bmp_start = zero_times[i_end+1][1]
    
    if alignment == "start":
        return align_time(x,y,bmp_start)
    return align_time(x,y,bmp_end)


#control = {"protraction": bmp_times(data_control["t"],data_control["V_B31a"],"end"),
#            "retraction": bmp_times(data_control["t"],data_control["V_B64a"],"start")
#           }

loaded = {"protraction": bmp_times(data_l["t"],data_l["V_B31a"],"end"),
            "retraction": bmp_times(data_l["t"],data_l["V_B64a"],"start")
           }

unloaded = {"protraction": bmp_times(data_ul["t"],data_ul["V_B31a"],"end"),
            "retraction": bmp_times(data_ul["t"],data_ul["V_B64a"],"start")
           }

def plot_vertical_scalebar(ax,scalebar_length=100,bar_width=0.25,offset=0,yoffset=10):
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
    ax.text(x_start - 1, y_start + scalebar_length / 2, f'{scalebar_length} mV',
            va='center', ha='right', color='black', fontsize=16)

colors = {"retraction": "teal", "protraction": "orangered"}

for ax in ax2.flat:
    ax.set_xlim((-10, 10))

#ax2[0,0].plot(*control["protraction"], c=colors["protraction"])
#ax2[0,0].set_ylabel("Control", fontsize=label_fontsize,rotation=0)
ax2[0,0].set_title("Protraction", fontsize=title_fontsize)
ax2[0,1].set_title("Retraction", fontsize=title_fontsize)

ax2[0,0].plot(*loaded["protraction"], c=colors["protraction"])
ax2[0,0].set_ylabel("Loaded", fontsize=label_fontsize,rotation=0)
remove_axes2(ax2[0,0])

ax2[1,0].plot(*unloaded["protraction"], c=colors["protraction"])
ax2[1,0].set_ylabel("Unloaded", fontsize=label_fontsize,rotation=0)
remove_axes2(ax2[1,0],x=True)

#ax2[0,1].plot(*control["retraction"], c=colors["retraction"])
#ax2[0,1].set_title("Retraction", fontsize=title_fontsize)
#remove_axes2(ax2[0,1])

ax2[0,1].plot(*loaded["retraction"], c=colors["retraction"])
remove_axes2(ax2[0,1])

ax2[1,1].plot(*unloaded["retraction"], c=colors["retraction"])
remove_axes2(ax2[1,1],x=True)

plot_vertical_scalebar(ax2[1,1],scalebar_length=20,bar_width=0.15,yoffset=17)

############################### PLOT ####################################

# sfig_labels = ['A', 'B']

# for subfig, label in zip(sfigs, sfig_labels):
#     # Add label to the upper left of each subfigure
#     subfig.suptitle(label, x=0.0, y=1.04, ha='left', va='top', fontsize=22, fontweight='bold')

# plt.show()
sfigs[1].align_ylabels()
plt.show()
fig.savefig(os.path.join(figpath,f"{fig_prefix}_bar.jpg"), bbox_inches="tight",dpi=300)
