import numpy as np
from time import time
from neuronpyxl.network import NetworkBuilder
import os

cwd = os.getcwd()

nb = NetworkBuilder(params_file=os.path.join(cwd,"Excel_files/momohara_neveu_2021_control.xlsx"),
                    sim_name="BMP", noise=None, dt=-1, integrator=2, atol=1e-5,
                    eq_time=5000, simdur=40000)

N = 15

times = np.zeros(N)

for i in range(N):
    t0 = time()
    nb.run(record_none=True)
    times[i] = time() - t0

mean = np.mean(times)
std = np.std(times)

with open(os.path.join(cwd,"result.txt"),"w") as file:
    file.write(rf"NEURON: {mean} $\pm$ {std}")


