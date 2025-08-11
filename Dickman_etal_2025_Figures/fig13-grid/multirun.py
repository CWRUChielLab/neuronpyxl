import numpy as np
from neuronpyxl import network
import os
import time
from itertools import product
from math import prod
import multiprocessing as mp
from copy import deepcopy

class MultiRun:
    def __init__(self, filename: str, simname: str, simdur, data0: dict, paramgrid: dict, error_funcs, numprocs: int = os.cpu_count(), timeout: int = 300):
        self.filename = filename
        self.simname = simname
        self.cwd = os.getcwd()
        self.t0_global = time.time()
        self.pgrid_size = prod([l[2] for l in paramgrid.values()])
        self.additional_cols = ["protraction", "retraction", "std1", "std2", "n1", "n2"]
        self.columns = list(paramgrid.keys())
        self.data0 = data0 # this doesn't really do anything but I don't want to refactor
        self.simdur = simdur
        self.num_simulations, self.pgrid = self.create_pgrid(paramgrid)
        self.error_funcs = error_funcs
        self.numprocs = numprocs
        self.TIMEOUT = timeout
        self.prefix = "neuronpyxl_"
        self.log_path = os.path.join(self.cwd, "sim_log.txt")
        self.results_path = os.path.join(self.cwd, "results.csv")
        self._initialize_files()
        

    def _initialize_files(self):
        with open(self.log_path, "w"):
            print(f"Cleared file '{self.log_path}'")
        
        with open(self.results_path, "w") as results:
            print(f"Cleared file '{self.results_path}'")
            results.write(",".join(self.columns+self.additional_cols) + "\n")


    def error_function(self,x0,y0,x,y):
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
    def error_function(self, x1, y1, x2, y2):
        
        err = 0
        for func_tuple in self.error_funcs:
            f, w = func_tuple[0], func_tuple[1]  # Function and weight
            args = func_tuple[2] if len(func_tuple) > 2 else {}  # Check for additional arguments
            err += f(x1, y1, x2, y2, **args) * w
        return err
        return durations(x1,y1,x2,y2)
    """
    
    def create_pgrid(self, pgrid_input):
        ranges = []
        length = 1
        for param_range in pgrid_input.values():
            ranges.append(np.linspace(param_range[0], param_range[1], param_range[2]).tolist())
            length *= len(ranges[-1])
        return length, product(*ranges)

    def create_obj_list(self, nb: network.NetworkBuilder):
        """
        Function to parse the variable names and convert to a NetworkBuilder Object
        """
        obj_list = []
        params = [c for c in self.columns if c not in self.additional_cols]
        for param in params:
            split_param = param.split(sep="_")
            ptype = split_param[0]
            match ptype:
                case "cs":
                    obj = nb.chemical_synapses[split_param[4]][split_param[2]][split_param[3]]["synapse"]
                case "es":
                    obj = nb.electrical_synapses[split_param[2]][split_param[3]]
                case "vdg":
                    obj = getattr(nb.cells[split_param[2]].section(0.5), f"{self.prefix}{split_param[3]}")
                case _:
                    raise ValueError(f"Parameter type '{ptype}' is invalid in paramgrid. Must be one of 'cs', 'es', or 'vdg'.")
            obj_list.append((obj, split_param[1]))
        return obj_list


    def set_param_values(self, object_list, values_list):
        """Sets parameter values for given set of parameters.

        Args:
            object_list (List[tuple]): List of tuples. The first element is a Hoc object and the second element is a string that corresponds to a parameter.
            values_list (List[float]): List of values that for each of those objects to be set to.
        """
        for (obj, param), v in zip(object_list, values_list):
            setattr(obj, param, v)
            

    def total_err(self, i, values_list, data0) -> float:
        """Computes the total error

        Args:
            i (_type_): Simulation number
            values_list (_type_): List of values to be passed into self.set_param_values()
            data0 (_type_): Testing dataset

        Returns:
            float: L2 norm of the errors corresponding to each cell.
        """
        t0 = time.time()
        total_err = []
        total_std = []
        total_n = []
        nb = network.NetworkBuilder(params_file=self.filename, sim_name=self.simname,\
                                    noise=None, dt=-1, atol=1e-3, eq_time=10000, integrator=2,\
                                    simdur=self.simdur,seed=True)

        object_list = self.create_obj_list(nb)
        self.set_param_values(object_list, values_list)

        nb.run()
        t1 = time.time()
        with open(self.log_path, "a") as log:
            log.write(f"Simulation {i} took {t1 - t0} seconds\n")

        for cell_name, (x0, y0) in data0.items():
            data = nb.get_cell_data(cell_name)
            try: # match the time range of the testing data
                indices = np.where(data["t"] > x0[0])
                x = data["t"][indices]
                y = data["V"][indices]
            except TypeError: # If x0 and y0 are int, then take the entire timeseries
                x = data["t"]
                y = data["V"]
            err,std,n = self.error_function(x0, y0, deepcopy(x), deepcopy(y))
            total_err.append(err)
            total_std.append(std)
            total_n.append(n)
        # return np.sqrt(total_err)
        return total_err,total_std,total_n

    def worker(self, i, values_list, data0):
        print(f"Starting process {i + 1}")
        err,std,n = self.total_err(i + 1, values_list, data0)
        values_list = values_list + err + std + n

        with open(self.results_path, "a") as results:
            results.write(",".join(map(str, values_list)) + "\n")

    def all_tasks_done(self):
        t1 = time.time()
        with open(self.results_path, "rbU") as f:
            num_results = sum(1 for _ in f) - 1
        with open(self.log_path, "a") as log:
            log.write(f"{self.num_simulations} simulations took {(t1 - self.t0_global) / 60:.2f} minutes to complete.\n")
            log.write(f"{self.num_simulations - num_results} simulations were unstable and took longer than {self.TIMEOUT} seconds.\n")

    
    def main(self):
        mp.set_start_method('spawn')
        procs = []
        batch_size = self.numprocs  # Use the maximum number of workers as the batch size
        params_list = list(self.pgrid)  # Convert the product generator to a list for slicing

        for i in range(0, self.pgrid_size, batch_size):
            # Submit a batch of tasks
            for j, params in enumerate(params_list[i:i + batch_size]):
                process = mp.Process(target=self.worker, args=(i + j, list(params), self.data0))
                process.start()
                procs.append(process)
                # Wait for the current batch to complete before proceeding to the next batch
            for process in procs:
                process.join(timeout=self.TIMEOUT)
                if process.is_alive():  # Kill if still running after timeout
                    process.terminate()
                    print(f"Process {process.pid} timed out and was terminated.")
            
            # Clear completed futures for the next batch
            procs.clear()
        
        self.all_tasks_done()
