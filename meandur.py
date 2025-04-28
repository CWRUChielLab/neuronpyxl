import pandas as pd
import sys
import numpy as np
import os
import pandas as pd
from neuron import h
from neuronpyxl import network
datapath = os.path.join(os.getcwd(), f"Data")
sys.path.append(datapath)
excelpath = os.path.join(os.getcwd(), f"Excel_files")
sys.path.append(excelpath)

params = {
    "loaded": {
        "vdg": 0.7645569620253164,
        "cs": 4.276404494382023
    }, "unloaded": {
        "vdg": 1.159493670886076,
        "cs": 4.316853932584269
    }
}

def set_params(nb,vals):
    nb.cells["B64s"].section.g_neuronpyxl_kpp = vals["vdg"]
    nb.chemical_synapses["slow"]["B63"]["B31s"]["synapse"].g = vals["cs"]

def durations(x, y):
    # Identify intervals where zero crossings occur
    try:
        crossings = np.where(np.diff(np.signbit(y)))[0]
        # Use root_scalar to find precise zeros
        x_zero = []
        for i in crossings:
            x_zero.append(np.interp(0, [y[i], y[i+1]], [x[i], x[i+1]]))
        
        x_zero = np.array(x_zero)
        dx = np.diff(x_zero)
        break_inds = np.where(dx > 1000)[0]
    except IndexError as e:
        return np.nan
        # raise e
        
    indices = []
    indices.append(0)
    for b in break_inds:
        indices.append(b)
        indices.append(b+1)
    indices.append(np.where(x_zero == x_zero[-1])[0][0])
    
    if len(indices) == 1:
        return np.nan
    
    durs = []
    i = 1
    while 4*i - 3 < len(indices):
        j = 4*i - 3
        durs.append(x_zero[indices[j]]-x_zero[indices[j-1]])
        i += 1
    return np.mean(durs)

results = {
    "loaded": {"B31a": [], "B63": []},
    "unloaded": {"B31a": [], "B63": []}
}
maxiter = 100
for param, vals in params.items():
    i = 0
    while i < 30 and i <= maxiter:
        nb = network.NetworkBuilder(params_file=os.path.join(excelpath, "momohara_neveu_2021_control.xlsx"), sim_name="BMP",
        noise=(50,8e-5,15), integrator=2, eq_time=5000,dt=-1,atol=1e-5,simdur=55000)
        set_params(nb,vals)
        nb.run()
        vb31 = nb.get_cell_data("B31a")
        vb63 = nb.get_cell_data("B63")

        results[param]["B31a"].append(durations(vb31["t"],vb31["V"]))
        results[param]["B63"].append(durations(vb63["t"],vb63["V"]))
        
        i += 1
        
        del nb


todf = {}

for k1, d in results.items():
    for k2,v in d.items():
        todf[(k1,k2)] = np.array(v)

df = pd.DataFrame(todf)
df.columns = pd.MultiIndex.from_tuples(df.columns)
df.to_csv("mean_duration.csv")