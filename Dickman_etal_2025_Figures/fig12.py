import numpy as np
import sys
import os
import pandas as pd
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import scienceplots
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D  # For legend
plt.style.use(["no-latex", "notebook"])
datapath = os.path.join(os.getcwd(),"Dickman_etal_2025_Figures/Data/fig12-13")
sys.path.append(datapath)
figpath = "./figs"
sys.path.append(figpath)
fig_prefix = "Dickman_etal_Results"
xfontsize = 14
yfontsize = 14
titlefont_size = 16
param1 = "vdg_g_B64s_kpp"
param2 = "cs_g_B30_B63_fast"
filename = "results.csv"
#####################################################################

chiel_data = pd.read_csv(os.path.join(datapath, "gillchiel_2020_data.csv"), header=[0,1,2])
bmp_dur = {"retraction": {"loaded":chiel_data[("loaded","retraction","dur")].mean(), \
                          "unloaded": chiel_data[("unloaded","retraction","dur")].mean()},\
           "protraction": {"loaded":chiel_data[("loaded","protraction","dur")].mean(), \
                           "unloaded": chiel_data[("unloaded","protraction","dur")].mean()}\
           }
def mindur(param1, param2, df, d1_col, d2_col, d1target, d2target):
    errors = np.sqrt((df[d1_col] - d1target) ** 2 + (df[d2_col] - d2target) ** 2)
    min_idx = errors.idxmin()  # Get index of minimum error
    row = df.iloc[min_idx]
    print(row)
    return {param1: row[param1], param2: row[param2]}

def get_params():
    # if speed == "fast":

    file = os.path.join(datapath, filename)
    df = pd.read_csv(file, header=0).dropna(axis=0) 
    d1target = bmp_dur["protraction"]["loaded"]*1000
    d2target = bmp_dur["retraction"]["loaded"]*1000
    md_loaded = mindur(param1, param2, df,"protraction","retraction",d1target,d2target)

    d1target = bmp_dur["protraction"]["unloaded"]*1000
    d2target = bmp_dur["retraction"]["unloaded"]*1000
    md_unloaded = mindur(param1, param2, df,"protraction","retraction",d1target,d2target)
    
    return {"loaded": md_loaded, "unloaded": md_unloaded}


params = get_params()
print(params)
file = os.path.join(datapath, filename)
# file = os.path.join(datapath, f"results_noisy1.csv")
df = pd.read_csv(file, header=0).dropna(axis=0)
# df = df[df[xcol] < 1.8] 
df["protraction"] /= 1000
df["retraction"] /= 1000
df["std1"] /= 1000
df["std2"] /= 1000

df["cv1"] = df["std1"] / df["protraction"]
df["cv2"] = df["std2"] / df["retraction"]

# df = df.loc[df['vdg_g_B64s_kpp'] <= 1.0]

def plot_ax(bmp, ax, sigma, delta, ylabel=True, contour=True,cv=False):
    xcol = param1
    ycol = param2
    
    x = df[xcol].to_numpy()
    y = df[ycol].to_numpy()
    z = df[bmp].to_numpy()

    if contour:
        vmax = max(max(df["protraction"]), max(df["retraction"]))
        vmin = min(min(df["protraction"]), min(df["retraction"]))
    elif cv:
        vmax = max(max(df["cv1"]), max(df["cv2"]))
        vmin = max(min(df["cv1"]), min(df["cv2"]))
    else:
        vmax = max(max(df["std1"]), max(df["std2"]))
        vmin = max(min(df["std1"]), min(df["std2"]))

    #####################################################################

    df_pivot = df.pivot_table(index=ycol, columns=xcol, values=bmp)

    #####################################################################

    xlen = 100
    numpoints = 2*xlen
    x_range = np.linspace(x.min(), x.max(), numpoints)
    y_range = np.linspace(y.min(), y.max(), numpoints)
    Xg, Yg = np.meshgrid(x_range, y_range)  # Create a 2D grid for X, Y
    Zg = griddata((x, y), z, (Xg, Yg), method='cubic')
    Zg_smoothed = gaussian_filter(Zg, sigma=sigma)
    #####################################################################

    mesh = ax.pcolormesh(df_pivot.columns, df_pivot.index, df_pivot.values,\
                         cmap="coolwarm", shading="auto", vmin=vmin, vmax=vmax)
    if contour:
        loaded_cont = bmp_dur[bmp]["loaded"]
        unloaded_cont = bmp_dur[bmp]["unloaded"]
        dcontour = delta
        contour_values = zip([loaded_cont, unloaded_cont],['springgreen', 'magenta'])
        contour_values = sorted(contour_values, key=lambda x: x[0])
        levels = [p[0] for p in contour_values]
        levels2 = [p[0]-dcontour for p in contour_values]
        levels3 = [p[0]+dcontour for p in contour_values]
        colors = [p[1] for p in contour_values] 

        ax.contourf(Xg, Yg, Zg_smoothed, levels=[levels2[0], levels3[0]], colors=colors[0], alpha=0.4)
        ax.contourf(Xg, Yg, Zg_smoothed, levels=[levels2[1], levels3[1]], colors=colors[1], alpha=0.4)
        ax.contour(Xg, Yg, Zg_smoothed, levels=levels, colors="black", linewidths=1)
        ax.contour(Xg, Yg, Zg_smoothed, levels=levels2, colors="black", linewidths=1, linestyles=["--"])
        ax.contour(Xg, Yg, Zg_smoothed, levels=levels3, colors="black", linewidths=1, linestyles=["--"])
        
    # ax.set_xlabel(f"{xcol} (uS)", fontsize=xfontsize)
    # if ylabel:
    #     ax.set_ylabel(f"{ycol} (uS)", fontsize=yfontsize)
        ax.set_title(bmp.capitalize(), fontsize=titlefont_size)
        
        ax.scatter([params["unloaded"][xcol]], [params["unloaded"][ycol]], marker="*", c="magenta",\
                   edgecolors="white", s=300, linewidths=1.5,alpha=1,zorder=2)
        ax.scatter([params["loaded"][xcol]], [params["loaded"][ycol]], marker="*", c="springgreen",\
                   edgecolors="white", s=300, linewidths=1.5,alpha=1,zorder=2)
    return mesh

fig,ax1 = plt.subplots(1,2,figsize=(14,10), constrained_layout=True)

# PLOT BMP DURATIONS
pc11 = plot_ax("protraction", ax1[0], 1.4, 0.2,True,True,False)
pc21 = plot_ax("retraction", ax1[1], 1.5, 0.2, False,True,False)

#ax1[0].set_xticklabels([])
# ax1[1].set_xticklabels([])
ax1[1].set_yticklabels([])
#ax2[1].set_yticklabels([])

ax1[0].set_ylabel(r"$\bar{g}$ of B30 to B63 connection ($\mu$S)")
# PLOT STANDARD ERRORS

error = "cv"
"""
pc12 = plot_ax(f"{error}1", ax2[0], 1.5, 0.1,True,False,False if error == "std" else True)
pc22 = plot_ax(f"{error}2", ax2[1], 2.5, 0.1, False,False,False if error == "std" else True)
"""
ax1[0].set_xlabel(r"$\bar{g}$ of slow potassium in B64s ($\mu$S)",fontsize=16)
ax1[0].set_ylabel(r"$\bar{g}$ of B30 to B63 connection ($\mu$S)",fontsize=16)
ax1[1].set_xlabel(r"$\bar{g}$ of slow potassium in B64s ($\mu$S)",fontsize=16)
ax1[0].tick_params(axis="x",labelsize=16)
ax1[1].tick_params(axis="x",labelsize=16)
ax1[0].tick_params(axis="y",labelsize=16)

orientation = "vertical"
location = "right"
label = "Standard deviation (s)" if error == "std" else "Coefficient of Variation"
#fig.colorbar(pc12, ax=ax2, shrink=0.9, location=location,\
        #       pad=0.05,orientation=orientation,label=label)
fig.colorbar(pc11, ax=ax1, shrink=0.77, location=location,\
        pad=0.05,orientation=orientation,label="Phase duration (s)")

legend_labels = ["Loaded", "Unloaded"]
legend_handles = [Line2D([0], [0], color=color, lw=4) for color in ["springgreen", 'magenta']]
plt.legend(legend_handles, legend_labels, title="Contour Levels")

for ax_group in [ax1]:
    for ax in ax_group:
        ax.set(adjustable='box', aspect=1.0/ax.get_data_ratio())
plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.001, hspace=0)
plt.show()
fig.savefig(os.path.join(figpath,f"{fig_prefix}_heatmap.jpg"),bbox_inches="tight",dpi=300)
