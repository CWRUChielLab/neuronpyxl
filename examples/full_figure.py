import pandas as pd
import scienceplots
import matplotlib.pyplot as plt
import sys
import numpy as np
import os
import pandas as pd
plt.style.use(["no-latex", "notebook"])
datapath = os.path.join("OptimizedData")
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

tick_fontsize = 12
label_fontsize = 14
title_fontsize=14
legend_fontsize=12

fig = plt.figure(figsize=(14,8),constrained_layout=True)
sfigs = fig.subfigures(1,2, width_ratios=(1.25,2))
ax1 = sfigs[0].subplots(1,1)
ax2 = sfigs[1].subplots(3,2,sharey=True,sharex=True)

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
    Patch(facecolor="white", edgecolor=ec, hatch="//", label="CPG"),  # Solid blue
    # Patch(facecolor="white", edgecolor=ec, hatch="x", label="SNNAP"),  # Solid blue
    Patch(facecolor="white", edgecolor=ec, label="Expmt.")  # Striped red,
]

ax1.legend(handles=legend_patches,loc="upper left",frameon=False)
remove_axes1(ax1)
sfigs[0].supxlabel("BMP phase",fontsize=label_fontsize,x=0.55)

############################### ALIGNED ####################################


data_control = pd.read_csv(os.path.join(datapath, f"data_test_control.csv")).drop(["Unnamed: 0"], axis=1)
tcontrol = data_control["t"]
data_test_l = pd.read_csv(os.path.join(datapath, f"data_test_loaded.csv")).drop(["Unnamed: 0"], axis=1)
ttest_l = data_test_l["t"]

data_test_ul = pd.read_csv(os.path.join(datapath, f"data_test_unloaded.csv")).drop(["Unnamed: 0"], axis=1)
ttest_ul = data_test_ul["t"]

tvec = np.arange(0,np.max(tcontrol),0.01)
vc_B31a = np.interp(tvec,tcontrol,data_control["V_B31a"])
vc_B64a = np.interp(tvec,tcontrol,data_control["V_B64a"])

vt_B31a_l = np.interp(tvec,ttest_l,data_test_l["V_B31a"])
vt_B64a_l = np.interp(tvec,ttest_l,data_test_l["V_B64a"])

vt_B31a_ul = np.interp(tvec,ttest_ul,data_test_ul["V_B31a"])
vt_B64a_ul = np.interp(tvec,ttest_ul,data_test_ul["V_B64a"])

def get_tend(v):
    return np.where(np.diff(np.signbit(v)))[0][-1]
def get_tstart(v):
    return np.where(np.diff(np.signbit(v)))[0][0]

def get_t(tvec,v, pos):
    if pos == "end":
        return (tvec-tvec[get_tend(v)])/1000
    if pos == "start":
        return (tvec-tvec[get_tstart(v)])/1000
    
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

ax2[0,0].plot(get_t(tvec,vc_B31a, "end"),vc_B31a, c=colors["protraction"])
ax2[0,0].set_ylabel("Control", fontsize=label_fontsize,rotation=0)
ax2[0,0].set_title("Protraction", fontsize=title_fontsize)
remove_axes2(ax2[0,0])

ax2[1,0].plot(get_t(tvec,vt_B31a_l, "end"),vt_B31a_l, c=colors["protraction"])
ax2[1,0].set_ylabel("Loaded", fontsize=label_fontsize,rotation=0)
remove_axes2(ax2[1,0])

ax2[2,0].plot(get_t(tvec,vt_B31a_ul, "end"),vt_B31a_ul, c=colors["protraction"])
ax2[2,0].set_ylabel("Unloaded", fontsize=label_fontsize,rotation=0)
remove_axes2(ax2[2,0],x=True)

ax2[0,1].plot(get_t(tvec,vc_B64a, "start"),vc_B64a, c=colors["retraction"])
ax2[0,1].set_title("Retraction", fontsize=title_fontsize)
remove_axes2(ax2[0,1])

ax2[1,1].plot(get_t(tvec,vt_B64a_l, "start"),vt_B64a_l, c=colors["retraction"])
remove_axes2(ax2[1,1])

ax2[2,1].plot(get_t(tvec,vt_B64a_ul, "start"),vt_B64a_ul, c=colors["retraction"])
remove_axes2(ax2[2,1],x=True)

plot_vertical_scalebar(ax2[2,1],scalebar_length=50,bar_width=0.15,yoffset=20)

sfigs[1].supxlabel("Aligned time (s)",fontsize=label_fontsize,x=0.53)
############################### PLOT ####################################

sfig_labels = ['A', 'B']

for subfig, label in zip(sfigs, sfig_labels):
    # Add label to the upper left of each subfigure
    subfig.suptitle(label, x=0.0, y=1.04, ha='left', va='top', fontsize=22, fontweight='bold')

# plt.show()
sfigs[1].align_ylabels()
plt.show()
fig.savefig(os.path.join(figpath,f"{fig_prefix}_bar.jpg"), bbox_inches="tight",dpi=300)
