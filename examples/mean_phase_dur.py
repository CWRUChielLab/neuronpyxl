import sys
sys.path.append("../neuronpyxl/")
from neuronpyxl import network
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
excelpath = "/home/udickman/Desktop/projects/CWRU/neuronpyxl/Excel_files"
figpath = "/home/udickman/Desktop/projects/CWRU/neuronpyxl/figs"
datapath = "/home/udickman/Desktop/projects/CWRU/neuronpyxl/OptimizedData"

param1 = "vdg_g_B64s_kpp"
param2 = "cs_g_B30_B63_fast"
filename = "results.csv"
noise = None
#noise = (100,1e-5,15)
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


def durations(x,y):
    try:
        crossings = np.where(np.diff(np.signbit(y)))[0]
        x_zero = []
        for i in crossings:
            x_zero.append(np.interp(0, [y[i], y[i+1]], [x[i], x[i+1]]))
        
        x_zero = np.array(x_zero)
        dx = np.diff(x_zero)
        break_inds = np.where(dx > 4000)[0]
    except IndexError:
        return np.nan
        
    indices = []
    indices.append(0)
    for b in break_inds:
        indices.append(b)
        indices.append(b+1)
    if len(indices) == 1:
        return np.nan
    durs = x_zero[indices[1::2]] - x_zero[indices[:-1:2]]
    meandur = np.mean(durs)
    stddur = np.std(durs)
    return np.nan if meandur > 10000 else (meandur,stddur,len(durs))
"""
def durations(x,y):
    try:
        crossings = np.where(np.diff(np.signbit(y)))[0]
        x_zero = []
        for i in crossings:
            x_zero.append(np.interp(0, [y[i], y[i+1]], [x[i], x[i+1]]))
        
        x_zero = np.array(x_zero)
        dx = np.diff(x_zero)
        break_inds = np.where(dx > 4000)[0]
    except IndexError:
        return np.nan
        
    indices = []
    indices.append(0)
    for b in break_inds:
        indices.append(b)
        indices.append(b+1)
    if len(indices) == 1:
        return np.nan
    durs = x_zero[indices[1::2]] - x_zero[indices[:-1:2]]
    meandur = np.mean(durs)
    stddur = np.std(durs)
    return np.nan if meandur > 10000 else (meandur,stddur,len(durs))
"""
def set_params(nb:network.NetworkBuilder,v1,v2):
    nb.cells["B64s"].section(0.5).g_neuronpyxl_kpp = v1
    nb.chemical_synapses["fast"]["B30"]["B63"]["synapse"].g = v2

folder = "OptimizedData"
params = get_params()

#params = {'loaded': {'vdg_g_B64s_kpp': np.float64(0.8084745762711865), 'cs_g_B30_B63_fast': np.float64(2.4898305084745767)}, 'unloaded': {'vdg_g_B64s_kpp': np.float64(1.3152542372881355), 'cs_g_B30_B63_fast': np.float64(1.6203389830508474)}}
params["control"] = {param1:0.35,param2:0.25}

print(params)

results = {}
for condition, vals in params.items():
    results.setdefault(condition,{"protraction": {},"retraction":{}})

    nb = network.NetworkBuilder(
        params_file=os.path.join(excelpath,"control_updated.xlsx"),
        sim_name="BMP",noise=noise,dt=-1,integrator=2,atol=1e-5,
        eq_time=10000,simdur=120000,seed=True
        )
    set_params(nb,vals[param1],vals[param2])
    nb.run(voltage_only=True)
    
    prot_data = nb.get_cell_data("B31a")
    ret_data = nb.get_cell_data("B64a")
    prot_result = durations(prot_data["t"],prot_data["V"])
    ret_result = durations(ret_data["t"],ret_data["V"])

    trace_data = {"t": prot_data["t"],
                  "V_B64a": ret_data["V"],
                  "V_B31a": prot_data["V"]}

    pd.DataFrame(trace_data).to_csv(os.path.join(datapath,f"data_test_{condition}.csv"))

    results[condition]["protraction"]["dur"],results[condition]["protraction"]["err"],\
            results[condition]["protraction"]["n"] = prot_result
    results[condition]["retraction"]["dur"],results[condition]["retraction"]["err"],\
            results[condition]["retraction"]["n"] = ret_result
    del nb

df = pd.DataFrame.from_dict({(level1, level2, level3): value
                             for level1, inner_dict in results.items()
                             for level2, inner_inner_dict in inner_dict.items()
                             for level3, value in inner_inner_dict.items()}, orient='index')

# Set MultiIndex
df.index = pd.MultiIndex.from_tuples(df.index)
df.to_csv(os.path.join(datapath,f"meandur{'_nonoise' if noise is None else ''}.csv"))
