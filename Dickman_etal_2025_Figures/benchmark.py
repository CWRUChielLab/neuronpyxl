import sys
sys.path.append("../neuronpyxl/")
from neuronpyxl import network
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import time
excelpath = "/home/uri/my-files/projects/cwru/neuronpyxl/Excel_files"

noise = (50,1e-5,25)
simdur = 40000
n = 10
noiseless_times = []
noisy_times = []

for _ in range(n):
    t0 = time.time()
    nw = network.Network(
            params_file=os.path.join(excelpath,"fig10.xlsx"),
            sim_name="BMP",noise=None,dt=-1,integrator=2,atol=1e-5,
            eq_time=10000,simdur=simdur,seed=False
            )
    nw.run(record_none=True)
    noiseless_times.append(time.time() - t0)


for _ in range(n):
    t0 = time.time()
    nw = network.Network(
            params_file=os.path.join(excelpath,"fig10.xlsx"),
            sim_name="BMP",noise=noise,dt=-1,integrator=2,atol=1e-5,
            eq_time=10000,simdur=simdur,seed=False
            )
    nw.run(record_none=True)
    noisy_times.append(time.time() - t0)

pd.DataFrame({
    "noisy": np.array(noisy_times),
    "noiseless": np.array(noiseless_times)
    }).to_csv("/home/uri/my-files/projects/cwru/neuronpyxl/Data/t-test/nrn_data.csv")


