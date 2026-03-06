"""
This file is part of neuronpyxl.

This is a command-line utility for generating mod files and 
running single simulations based on models described by an
Excel spreadsheet (see examples). This file must be used to
generate the mod files. For running simulations in a .py file
or notebook, see the examples.

Copyright (C) 2026 Uri Dickman, Peter J. Thomas, Hillel J. Chiel, John H. Byrne,
and Curtis L. Neveu.

neuronpyxl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

neuronpyxl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with neuronpyxl. If not, see <https://www.gnu.org/licenses/>.
"""

###################################################################
from . import ModBuilder, Network
import argparse
import subprocess
import os
import argparse
import numpy as np
import pandas as pd
import shutil
import sys
from pathlib import Path

cwd = os.getcwd()

def add_arguments():
    """Adds arguments to the command line argument parser.

    Returns:
        
    """

    parser = argparse.ArgumentParser(description="Process NEURON simulation arguments.")
    parser.add_argument('-f', required=True, type=str, choices=['gen_mods', 'run_sim'],
                        help="Function to run. The options are 'gen_mods' or 'run_sim'.")
    parser.add_argument('--file', required=True, type=str,
                        help="File name of the control excel sheet describing the simulation.")
    parser.add_argument('--name', type=str,
                        help="Name of the simulation.")
    parser.add_argument('--folder', type=Path,
                        help="Folder name to save data to.")
    parser.add_argument('--duration', type=float, default=10000.0,
                        help="Duration of the simulations in ms. Default is 30000.")
    parser.add_argument('--noise', type=float, nargs=3, default=None,
                        help="Noise parameters for an Exponential Synapse noise model.\
                        noise[0] = rate (Hz), noise[1] = weight (nS), noise[2] = tau (ms).")
    parser.add_argument('--seed', action='store_true',
                        help="Sets a seed for all of the NetStims so that simulations are deterministic.\
                        If not provided, chooses a different random seed for each stim. \
                        In both cases, the NetStims are independent.")
    parser.add_argument('--method', type=int, choices=[1, 2, 3], default=3,
                        help="Method of integration. 1 -> Backwards Euler, 2 -> Crank-Nicholson, 3 -> CVODE (default).")
    parser.add_argument('--step', type=float, default=-1.,
                        help="Time step of the integration in ms. If not provided, \
                            will default to variable timestep Crank-Nicholson.")
    parser.add_argument('--atol', type=float, default=1e-5,
                        help="Absolute error tolerance of integration. Default is 1e-5.")
    parser.add_argument('--interp', type=float, default=-1.,
                        help="Linear interpolate to constant size time step provided (in ms)\
                            (exclusive of 0 and inclusive of duration to match SNNAP's output).\
                                If not provided, will return the variable timestepped data.")
    parser.add_argument('--syn', action='store_true',
                        help="If --syn is entered, will record synaptic currents if they are available.")
    parser.add_argument('--vonly', action='store_true',
                        help="If --vonly is entered, will only record membrane potentials of each cell and the time.\
                              If both --syn and --vonly are passed, will default to --vonly.")
    parser.add_argument('--teq', type=float, default=1000.0,
                        help="Sets equilibration time to provided value. Defaults to 1000.0 ms.")
    args = parser.parse_args()

    ##################################
    # Ensure that required arguments #
    # for each function are provided #
    ##################################

    required_args = {
        "gen_mods": ["f", "file"],
        "run_sim": ["f", "file", "name", "duration"]
    }
    missing_args = [arg for arg in required_args.get(args.f, []) if getattr(args, arg) is None]
    if missing_args:
        parser.error(f"Arguments {', '.join(missing_args)} are required when -f is '{args.f}'.")

    return args

####################
# Define functions #
####################

def gen_mods(file):
    """Function to generate mod files by calling
    run from the ModBuilder class.

    Args:
        file (Path): path to an Excel file
    """
    mb = ModBuilder(file)
    mb.run()
    # Run NEURON's nrnivmodl executable
    subprocess.run("nrnivmodl mod", shell=True, check=True)


def clear_dir(dir_path):
    """Function to clear a data directory before populating it.

    Args:
        dir_path (Path): path of a directory to clear
    """
    if os.path.exists(dir_path):
        # If directory exists, empty it
        del_dir = input(f"Clear out contents of {dir_path}? (y/n) ") == "y"
        if not del_dir:
            sys.exit()
        shutil.rmtree(dir_path,ignore_errors=True)
        os.makedirs(dir_path)
    else:
        # Directory does not exist, create it
        os.makedirs(dir_path)


def run_sim(
            name        : str,
            file        : str, 
            folder      : Path   =None, 
            step        : float =-1.,
            duration    : float =10000.,
            method      : int   =2,
            atol        : float =1e-5,
            interp      : float =-1,
            syn         : bool  =False,
            vonly       : bool  =False,
            noise       : tuple =None,
            teq         : float =1000.,
            seed        : bool  =False
    ):
    """Runs a simulation from the provided file and simulation name (before .smu in Excel),
        provided that the mod files are properly compiled.

    Args:
        name (str): Function to run. The options are 'gen_mods' or 'run_sim'.
        file (str): File name of the control excel sheet describing the simulation.
        step (float, optional): Name of the simulation. Defaults to -1..
        duration (float, optional): Duration of the simulations in ms. Defaults to 10000.
        method (int, optional): Method of integration. 1 for Backwards Euler and 2 for
                                Crank-Nicholson. Defaults to 2.
        atol (float, optional): Absolute error tolerance of integration.
                                Defaults to 1e-5.
        interp (float, optional): Cubic spline interpolation to constant size time step provided (in ms).
                                If not provided, will return the variable timestepped data. Defaults to -1.
        syn (bool, optional): If True, will record synaptic currents if they are available. Defaults to False.
        vonly (bool, optional): If True, will only record membrane potentials of each cell and the time.
                                If both syn and vonly are True, will default to recording vonly. Defaults to False.
        noise (tuple, optional): Noise parameters for an Exponential Synapse noise model. noise[0] = rate (Hz),
                                noise[1] = weight (nS), noise[2] = tau (ms). Defaults to None.
        teq (float, optional): Sets equilibration time to provided value. Defaults to 1000.0.
        seed (int, optional): Sets the seed for noisy synapses if included. (Not working)
    """

    # Ensure valid input parameters
    assert interp == -1 or interp > 0, \
        f"interp={interp} is not a valid interpolation timestep. Must be greater than 0."
    assert duration > 0, \
        f"duration={duration} is not a valid simulation duration. Must be greater than 0."
    assert step == -1 or step > 0, \
        f"step={step} is not a valid simulation timestep Must be greater than 0."
    assert 0 < atol < 1, \
        f"atol={atol} is not a valid error tolerance. Must be between 0 and 1."

    # Set up and run simulation but setting object parameters to correct values
    nb = Network(
                params_file     =   file,
                sim_name        =   name,
                noise           =   noise,
                dt              =   step,
                atol            =   atol,
                integrator      =   method,
                eq_time         =   teq,
                simdur          =   duration,
                seed            =   seed
        )
    if syn and not vonly:
        nb.record_synaptic_currents = True
        
    # Set up data directory after parameters have been loaded
    if not os.path.exists(os.path.join(cwd, "data")):
        os.makedirs(os.path.join(cwd, "data"))
    if folder is not None:
        results_folder = os.path.join(cwd, f"data/{folder}")
    else:
        results_folder = os.path.join(cwd, f"data/{name}_data")
    clear_dir(results_folder) # Clear the directory so it is clean for the fresh data
    nb.run(voltage_only=vonly) # Run the simulation, passing in vonly.
    
    # Save data
    print(f"Saving data...")
 
    data_file_name = f"{name}_data.h5"
    file = pd.HDFStore(
                os.path.join(results_folder, data_file_name),
                mode="w"
            )
    if vonly: # if only voltage and time are recorded
        data = {}
        for c in nb.cells.keys():
            if interp <= 0:
                cell_data = nb.get_cell_data(c)
            else:
                tvec = np.arange(start=0,stop=duration,step=interp)
                cell_data = nb.get_interpolated_cell_data(c, tvec)
            if "t" not in data:
                data["t"] = cell_data["t"]
            data[f"V_{c}"] = cell_data["V"]
        pd.DataFrame(data).to_hdf(
                    os.path.join(results_folder, data_file_name),
                    key="membrane", mode="a"
        )
    else:
        if syn:
            if interp <= 0:
                chemsyn_data, elecsyn_data = nb.get_synaptic_current_data()
            else:
                tvec = np.arange(start=0,stop=duration,step=interp)
                chemsyn_data, elecsyn_data = nb.get_interpolated_syn_data(tvec)
            if chemsyn_data is not None: # could be none if there are one of cs or es present
                pd.DataFrame(chemsyn_data).to_hdf(
                            os.path.join(results_folder, data_file_name),
                            key="cs", mode="a"
                )
            if elecsyn_data is not None:
                pd.DataFrame(elecsyn_data).to_hdf(
                            os.path.join(results_folder, data_file_name),
                            key="es", mode="a"
                )
        for c in nb.cells.keys():
            if interp <= 0:
                cell_data = nb.get_cell_data(c)
            else:
                tvec = np.arange(start=0,stop=duration,step=interp)
                cell_data = nb.get_interpolated_cell_data(c, tvec)
            pd.DataFrame(cell_data).to_hdf(
                        os.path.join(results_folder, data_file_name),
                        key=f"{c}", mode="a"
            )
    file.close()
    # Save metadata
    nb.generate_metadata(voltage_only=vonly,folder=results_folder)
    print(f"Simulation complete! Data has been saved to {os.path.join(results_folder,data_file_name)}.\
          \nSimulation info can be found in {os.path.join(results_folder,'info.txt')}")


def main():
    args = add_arguments()
    func = args.f
    if func == "gen_mods":
        gen_mods(args.file)
    elif func == "run_sim":
        run_sim(
                name        =   args.name,
                file        =   args.file,
                folder      =   args.folder,
                duration    =   args.duration,
                step        =   args.step,
                method      =   args.method,
                atol        =   args.atol,
                interp      =   args.interp,
                syn         =   args.syn,
                vonly       =   args.vonly,
                noise       =   args.noise,
                teq         =   args.teq,
                seed        =   args.seed
        )

#################################
# Execute when this file is run #
#################################

if __name__ == "__main__":
    main()
