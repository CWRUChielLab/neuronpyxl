from multirun import MultiRun
import os
import sys
excelpath = "/home/uxd25/home/MultiRun/Excel_files"
sys.path.append(excelpath)

excel_file = "control_updated.xlsx"

simdur = 120000

paramgrid = { # Dict[param -> [minval, maxval, numvals]]
    "vdg_g_B64s_kpp": [0.5, 1.8, 70],
    "cs_g_B30_B63_fast": [1.3, 4.0, 70]
}

#functions = [(None, 1, {})] # Didn't end up using this

data0 = {"B31a": (0, 0), # Target values (0 means just report the original values)
         "B64a": (0, 0)}

N = int(os.environ['SLURM_JOB_CPUS_PER_NODE']) * int(os.environ['SLURM_NNODES']) # numprocs

print(f"Number of processes = {N}")

if __name__ == "__main__":
    mr = MultiRun(os.path.join(excelpath, excel_file),
                  "BMP",
                  simdur,
                  data0,
                  paramgrid,
                  error_funcs=[],
                  numprocs=N,
                  timeout=1200)
    mr.main()
