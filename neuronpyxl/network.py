"""
This file is part of neuronpyxl.

The NetworkBuilder class is the central class for neuronpyxl. It takes the simplified results from the
ControlReader and generates the entire network from that information, assuming that the correctly-named mod 
files are already compiled (see ModBuilder). It also has capabilities to run simulations and record
the data directly from NEURON. These functions can be accessed either through cmd_util.py or by creating
a NetworkBuilder object and running the simulations from another .py file.

Copyright (C) 2024 Uri Dickman, Curtis Neveu, Hillel Chiel, Peter Thomas

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

from neuron import h
import numpy as np
import pandas as pd
import gc
import copy
import sys
import os
import platform
import time
from scipy.interpolate import CubicSpline
from neuronpyxl import cell, reader
from typing import Tuple
import warnings

class NetworkBuilder:
    def __init__(self, params_file: str, sim_name: str, noise: tuple, dt: float, integrator: int, atol: float, eq_time: float, simdur:float, seed:bool):
        """_summary_

        Args:
            params_file (str, optional): _description_. Defaults to "".
            cells (list, optional): _description_. Defaults to [].

        Raises:
            ValueError: _description_
        """
        self.cwd = os.getcwd()
        h.load_file("stdrun.hoc")
        # if platform.uname()[0] == "Windows":
        #     h.nrn_load_dll(os.path.join(self.cwd, "nrnmech.dll"))
        self.name = "sim"
        self.cells = {} # Dict[cell name -> Cell object] (see cell.py)
        
        # To prevent garbage collection, store all necessary objects:
        self.electrical_synapses = {} # Dict[presynaptic cell name -> Dict[postsynaptic cell name -> PointProcess]]
        self.chemical_synapses = {"fast": {}, "slow": {}} # Dict[synapse type -> Dict[presynaptic cell name -> Dict[postsynaptic cell name -> Dict["synapse" -> PointProcess, "netcon" -> NetCon]]]]
        self.input_resistance = {} # stores input resistances
        if noise is not None:
            self.noise = {"rate": noise[0], "scale": noise[1], "tau": noise[2]}
            # self.noise = {"std": noise[0], "rate": noise[1]}
        else:
            self.noise = None
        self.noise_cons = {}
        self.seed = seed
        # There can be multiple clamps at the same location. This may be deprecated at some point, because this model uses 0.5 as the default and only location.
        self.current_clamps = {} # Dict[cell name -> Dict[location -> List[IClamp]]]
        self.voltage_clamps = {} # Dict[cell name -> Dict[location -> List[VClamp]]
        self.pools_active = {}
        
        self.zero_ref = h.Vector(1) # Create a 0 reference in case there are unused hoc pointers
        self.zero_ref.x[0] = 0  # Set the first element to zero
        
        self.prefix = "neuronpyxl_" # mod file
        # Simulation setup parameters
        self.dt = dt
        self.integrator = integrator # can be 1 or 2 (1: Backwards Euler, 2: Crank-Nicholson)
        match self.integrator:
            case 1:
                self.secondorder = 0
            case 2:
                self.secondorder = 2
        self.atol = atol
        self.interp = 0.005
        self.v0 = {}
        self.eq_time = eq_time
        if noise is not None:
            self.noise_eq_time = 1000
        else:
            self.noise_eq_time = 0
        self.simdur = simdur
        self.temp = 6.3
        self.record_synaptic_currents = False
        self.sim_name = sim_name
        self.params_file = params_file
        # Load in all parameters to NEURON
        self.setup(params_file)
        # Set up recording dictionary -- populated during run step
        self.recording = {} # Dict["t" -> time recording, [cell name -> all recordings for cell] for cell in cells]
        self.synaptic_currents_recording = {}
        self.ran_before = False
    
    
    def add_cell(self, cell: cell.Cell):
        """Function to add a cell to the network.

        Args:
            cell (Cell): a Cell object
        """
        self.cells[cell.name] = cell
    
    
    def setup(self, file):
        """Calls all of the functions in order to build the network from the provided Excel file.

        Args:
            file (pd.ExcelFile): an Excel file read in by Pandas.
        """
        self.reader = reader.ControlReader(file, self.sim_name, 21)
        self.add_cells_from_reader()
        print("Loading simulation parameters...")
        self.feed_pools_from_reader()
        self.add_regulation_from_reader()
        self.add_synapses_from_reader()
        self.set_up_v0_from_reader()
        if self.noise is not None:
            self.add_noise()
        self.add_iclamps_from_reader()

    
    def add_cells_from_reader(self):
        """Adds all of the cells present in the model into the network, along with their corresponding mechanisms.
        Sets all of the parameter values of each mechanism in each cell according to those present in the spreadsheet.
        """
        def set_activation_parameters(vdg_parameters, key, r, var):
            """A and B are identical sets of equations, so this function sets all parameter values
            accounting for every possible variable combination that exists within the SNNAP model.

            Args:
                vdg_parameters (_type_): main parameter dictionary (see below)
                r (_type_): row of the df
                key (_type_): ion channel mechanism
                var (_type_): A or B
            """
            if pd.isna(r[var]["tmx"]):
                vdg_parameters[key][f"{var}infonly"] = 1
            for param, val in r[var].items():
                if not pd.isna(val):
                    vdg_parameters[key][f"{param}{var}"] = val
                    if not f"{var}infonly" in vdg_parameters[key]:
                        if param == "tmx" and (r[var]["ts1"] == 0 or pd.isna(r[var]["ts1"])):
                            vdg_parameters[key][f"tmx{var}only"] = 1
                            vdg_parameters[key][f"num{var.lower()}taus"] = 1
            if not pd.isna(r[var]["ts1"]) and r[var]["ts1"] != 0:
                if pd.isna(r[var]["ts2"]) or r[var]["ts2"] == 0:
                    vdg_parameters[key][f"num{var.lower()}taus"] = 1
                else:
                    vdg_parameters[key][f"num{var.lower()}taus"] = 2
                    
        # Read all mechanisms present
        # Reads cells data, which includes cell names and membrane capacitance
        cell_data = self.reader.cells_data
        # Get mechanism parameters for each cell
        mechs_data = self.reader.mechs_data[self.reader.mechs_data.index != 0].dropna(axis=0, how="all")
        mechs = [m for m in mechs_data.columns.levels[0] if "Unnamed" not in m and "File" not in m]
        self.all_mechs = []
        assert not mechs_data.empty and not cell_data.empty, "You must run a simulation with at least one cell."

        # Set parameter values for all cells and all mechanisms
        for name, row in mechs_data.iterrows(): # Name is the cell name, row is the row in the 'Neu' sheet
            vdg_parameters = {}
            cm = cell_data.loc[name]["cm"] # get membrane capacitance
            for m in mechs:
                if m in row:
                    r = row[m] # row of the parameters df
                else:
                    continue
                if not r["vdg"].isna().to_numpy().all():
                    # key is the mechanism's name, which has no _ characters and is stripped and lowered
                    key = m.lower().strip().replace("_", "")
                    if key not in self.all_mechs:
                        self.all_mechs.append(key)
                    vdg_parameters[key] = {}
                    # Get the conductance and reversal potential
                    vdg_parameters[key]["g"] = r["vdg"]["g"]
                    vdg_parameters[key]["e"] = r["vdg"]["E"]
                    if key == "leak": # Leak will always have just g and e, so continue if this mech is leak
                        continue
                    if "p" in r["vdg"].index:
                        vdg_parameters[key]["p"] = r["vdg"]["p"]
                    if not pd.isna(r["A"]).all(): # if there are no As, there aren't any Bs.
                        set_activation_parameters(vdg_parameters, key, r, "A")
                        if not pd.isna(r["B"]).all():
                            set_activation_parameters(vdg_parameters, key, r, "B")
                        else:
                            vdg_parameters[key][f"numbtaus"] = 0
                    else:
                        vdg_parameters[key][f"numataus"] = 0
                        vdg_parameters[key][f"numbtaus"] = 0
            # Create the Cell object
            mechs_with_prefix = [self.prefix + m for m in vdg_parameters.keys()] # Need to add "neuronpyxl_" before every mechanism (see mod files)
            c = cell.Cell(name=name, current_mechs=mechs_with_prefix, cm=cm) # create a cell, which inserts mechanisms into the cell
            # Set the parameter values of the mechanisms in this cell  based on the now-filled vdg_parameters dictionary
            
            for mech, d in vdg_parameters.items():
                for param, val in d.items():
                    setattr(c.section(0.5), f"{param}_{self.prefix}{mech}", val)
            # Add the cell to the network
            self.add_cell(c)
            print(f"Added {c} to the network.")
              
    
    def feed_pools_from_reader(self):
        """Sets up the ion pool feeding mechanism from python according to the implementation in NMODL.
        If a channel feeds into a pool, then it has a STATE variable for that concentration contribution (e.g. cai_state).
        Then, the ion pool accumulator mechanism is added into the cell and reads in all the state variables which feed into the pool as pointers.
        The sum of those concentrations becomes the total concentration of the ion pool, which is set by the accumulator and not the channel mechanism.
        """
        # Read data from spreadsheet
        possible_ions = ["ca", "na", "k", "cl"]
        all_mechs = self.all_mechs
        max_channels = {}
        for m in all_mechs:
            for ion in possible_ions:
                if m.startswith(ion):
                    max_channels.setdefault(ion, 0)
                    max_channels[ion] += 1
        df = self.reader.cond_to_ion_data
        df = df[df.index != 0]
        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0,how="all")
        if df.empty:
            return
        # Populate an empty dictionary for according to the data in the spreadsheet

        for name, row in df.iterrows():
            pools_data = self.reader.ion_pools_data.loc[name]
            pools_data = pools_data[pools_data.index != 0]
            pools = {}
            for ion_key, k1_key, k2_key in \
                    [("ion", "K1", "K2"), ("ion_1", "K1_1", "K2_1"), ("ion_2", "K1_2", "K2_2")]:
                ion_value = pools_data[ion_key]
                if isinstance(ion_value, str):
                    pool = ion_value.lower().strip()
                    if pool not in pools:
                        pools[pool] = {"k1": pools_data[k1_key], "k2": pools_data[k2_key]}
            cell = self.cells[name] # Get the cell object
            ions = {}

            for i in range(0, 4):  # Loop over ch, ch_1, ch_2
                ch_col = f"ch_{i}" if i > 0 else "ch"
                ion_col = f"ion_{i}" if i > 0 else "ion"
                if ch_col in df.columns and ion_col in df.columns:
                    if isinstance(row[ch_col],str) and isinstance(row[ion_col],str):
                        ch = row[ch_col].lower().strip()
                        ion = row[ion_col].lower().strip()
                        self.pools_active.setdefault(name, set({})).add(ion)
                        ions.setdefault(ion, []).append(ch)
            # Load the ion pool mechanisms into the cell
            
            cell.load_mechanisms([f"{self.prefix}{ion}pool" for ion in self.pools_active[name]])
            for ion, l in ions.items():
                for j, ch in enumerate(l):
                    # Set up the accumulator pointers correctly
                    chmech = getattr(cell.section(0.5), f"{self.prefix}{ion}pool")
                    pointer = f"i{j+1}"
                    ref = getattr(cell.section(0.5), f"_ref_i_{self.prefix}{ch}")
                    h.setpointer(ref, pointer, chmech)
                if j < max_channels[ion]-1:
                    for k in range(j+1, max_channels[ion]-j):
                        h.setpointer(self.zero_ref._ref_x[0], f"i{k+1}", getattr(cell.section(0.5), f"{self.prefix}{ion}pool"))
            setattr(cell.section(0.5), f"k1_{self.prefix}{ion}pool", pools[ion]["k1"])
            setattr(cell.section(0.5), f"k2_{self.prefix}{ion}pool", pools[ion]["k2"])
                      

    def add_iclamps_from_reader(self):
        """Sets up current clamps to the network, if provided in the spreadsheet.
        """
        if self.reader.iclamp_data.empty:
            return
        for name, row in self.reader.iclamp_data.iterrows():
            self.attach_iclamp(name, loc=0.5, delay=row["start"]*1000, dur=(row["stop"]-row["start"])*1000, amp=row["magnitude"])
        
        
    def add_synapses_from_reader(self):
        """Function to add all of the synaptic connections to the network.

        Raises:
            ValueError: raised if a nonexistent ion is listed as facilitating.
        """
        #### Electrical synapses
        df_esg = self.reader.esg_data
        if df_esg.empty:
            return
        esg_stacked = df_esg[df_esg != 0].stack()
        for (pre, post), g in esg_stacked.items():
            presyn = self.cells[pre]
            postsyn = self.cells[post]
            syn = h.neuronpyxl_ES(postsyn.section(0.5))
            # Set max conductance
            syn.g = g
            # Set up presynaptic potential pointer (works the same as gap junction NEURON mechanism file)
            syn._ref_vpre = presyn.section(0.5)._ref_v
            # Update ES dictionary
            self.electrical_synapses.setdefault(pre, {})[post] = syn
            
        # helper method to set values of all params in below dictionaries
        def set_attr_cs_params(d, syn):
            for k, v in d.items():
                if isinstance(v, dict):
                    set_attr_cs_params(v, syn)
                else:
                    setattr(syn, k, v)
                    
        def add_cs(dfg, dfe, dfparams, type):
            # type is either slow or fast
            if any([len(dfg)==0, len(dfe)==0, len(dfparams)==0]):
                return
            for pre, d in dfg[type].items():
                if pre == 0:
                    continue
                for post, g in d.items():
                    if post == 0:
                        continue
                    presyn = self.cells[pre]
                    postsyn = self.cells[post]
                    syn = h.neuronpyxl_CS(postsyn.section(0.5))
                    params = {}
                    # Set up parameters dictionary
                    for k, v in dfparams[pre][post].dropna().to_dict().items():
                        params.setdefault(k[0], {})[k[1]] = v
                    # Get basic parameters
                    params["g"] = g
                    params["e"] = dfe[type][pre][post]
                    # Get model-dependent parameters
                    if len(params["taus"]) == 1:
                        params["taus"]["u2"] = params["taus"]["u1"]
                    params["taus"]["u1"] *= 1000
                    params["taus"]["u2"] *= 1000
                    if "Voltage dependence" in params:
                        params["voltage_dependence"] = 1
                        if "tx" not in params["Voltage dependence"] or params["Voltage dependence"]["tx"] == 0:
                            params["tx"] = -1
                        else:
                            params["Voltage dependence"]["tx"] *= 1000
                    if "depression" in params:
                        params["depress"] = 1
                        params["depression"]["ud"] *= 1000
                        params["depression"]["ur"] *= 1000
                    if "facilitation" in params:
                        # Set ion facilitation pointers
                        match params["facilitation"]["ion"].lower().strip():
                            case "ca":
                                syn._ref_mod = presyn.section(0.5)._ref_cai
                            case "na":
                                syn._ref_mod = presyn.section(0.5)._ref_nai
                            case "k":
                                syn._ref_mod = presyn.section(0.5)._ref_kai
                            case "cl":
                                syn._ref_mod = presyn.section(0.5)._ref_cli
                            case _:
                                raise ValueError(f'{params["facilitation"]["ion"]} is not a valid facilitation ion. Must be one of Ca, Na, K, or Cl.')
                        params["facilitation"]["u"] *= 1000
                        params["facilitation"]["ion"] = 1
                    set_attr_cs_params(params, syn) # Set all parameters for the given synapse
                    # Set up the NetCon
                    nc = h.NetCon(presyn.section(0.5)._ref_v, syn, sec=presyn.section)
                    nc.threshold = 0.0 # Spiking threshold set to 0 mV (same as SNNAP)
                    nc.delay = 0.0
                    nc.weight[0] = 0
                    # Add items to dictionary to avoid garbage collection
                    self.chemical_synapses[type].setdefault(pre, {})[post] = {"synapse": syn , "netcon": nc}
                    
        df_csg = self.reader.csg
        df_cse = self.reader.cse
        df_cs_params_fast = self.reader.csfat_params_fast
        df_cs_params_slow = self.reader.csfat_params_slow
        add_cs(df_csg, df_cse, df_cs_params_fast, "fast")
        add_cs(df_csg, df_cse, df_cs_params_slow, "slow")
        
    
    def add_regulation_from_reader(self):
        """Function to set up ion regulation from an ion pool.
        """
        # Unit conversions for the different parameters in the spreadsheet (these may not work)
        unitconv = {"p1": {1: 1000,
                       2: 1e-6,
                       3: 1,
                       4: 1e6,
                       5: 1e-6},
                    "p2": 1000}
        df = self.reader.ion_to_cond_data
        df = df[df.index != 0]
        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0, how="all")
        ions = ["ca", "na", "k", "cl"]
        if df.empty:
            return
        # Get parameters for each cell
        for name, row in df.iterrows():
            cell = self.cells[name]
            for i in range(0, 4):  # Loop over ch, ch_1, ch_2, ch_3
                ch_col = f"ch_{i}" if i > 0 else "ch"
                ion_col = f"ion_{i}" if i > 0 else "ion"
                opt1_col = f"opt1_{i}" if i > 0 else "opt1"
                opt2_col = f"opt2_{i}" if i > 0 else "opt2"
                p1_col = f"p1_{i}" if i > 0 else "p1"
                p2_col = f"p2_{i}" if i > 0 else "p2"
                b_col = f"b_{i}" if i > 0 else "b"
                
                if ch_col in df.columns and ion_col in df.columns:
                    ch = row[ch_col].lower().strip()
                    ion = row[ion_col].lower().strip()
                    opt1 = row[opt1_col]
                    opt2 = row[opt2_col]
                    p1 = row[p1_col]
                    # Set parameters in the mechanisms
                    try:
                        ion_num = ions.index(ion.lower().strip()) + 1
                    except ValueError:
                        raise ValueError(f'{ion} is not a valid regulatory ion. Must be one of Ca, Na, K, or Cl.')
                    setattr(cell.section(0.5), f"region_{self.prefix}{ch}", ion_num)
                    setattr(cell.section(0.5), f"opt1_{self.prefix}{ch}", opt1)
                    setattr(cell.section(0.5), f"opt2_{self.prefix}{ch}", opt2)
                    setattr(cell.section(0.5), f"p1_{self.prefix}{ch}", p1*unitconv["p1"][opt2])
                    if p2_col in df.columns:
                        p2 = row[p2_col]
                        setattr(cell.section(0.5), f"p2_{self.prefix}{ch}", p2*unitconv["p2"])
                    if b_col in df.columns:
                        b = row[b_col]
                        setattr(cell.section(0.5), f"b_{self.prefix}{ch}", b)
        
    
    def set_up_v0_from_reader(self):
        """Function to set all of the initial voltages of the cell membranes according to the spreadsheet.
        """
        df_v0 = self.reader.initial_voltage_data
        df_v0.dropna(axis=0, inplace=True)
        if df_v0.empty: # If voltages not provided, will default to -60 mV
            for c in self.cells.keys():
                self.v0[c] = -60.0
        else:
            self.v0 = df_v0[df_v0.index != 0].to_dict()["mV"]


    def print_cell_section(self, name: str, loc: float):
        """Given a cell name, prints all of the mechanisms and parameter values in the provided cell name and location.

        Args:
            name (str): name of the cell to print
            loc (float): location at which to print
        """
        h.psection(self.cells[name].section(loc))

    
    def compute_input_resistance(self):
        for name, cell in self.cells.items():
            z = h.Impedance()
            z.loc(0.5, sec=cell.section)  # Measure impedance at the center of the soma
            z.compute(0)  # Compute impedance at frequency f=0 (DC)
            self.input_resistance[name] = z.input(0.5, sec=cell.section)  # Location 0.5 is the center of the soma
    
            
    def add_noise(self):
        # self.compute_input_resistance()
        e1 = 60
        e2 = -90
        rate = self.noise["rate"] / 1000 # 1 / ms
        
        def spike_num(rate, simdur):
            return rate*simdur
        
        for name, cell in self.cells.items():
            h.finitialize()
            e0 = cell.section(0.5).v
            
            num = spike_num(rate, self.simdur+self.noise_eq_time)

            ns1 = h.NetStim()
            ns1.number = num
            ns1.start = self.eq_time
            ns1.interval = 1 / rate
            ns1.noise = 1.0
            
            ns2 = h.NetStim()
            ns2.number = num
            ns2.start = self.eq_time
            ns2.interval = 1 / rate
            ns2.noise = 1.0

            syn1 = h.ExpSyn(cell.section(0.5))
            syn1.tau = self.noise["tau"]
            syn1.e = e1
            
            syn2 = h.ExpSyn(cell.section(0.5))
            syn2.tau = self.noise["tau"]
            syn2.e = e2
            
            # Connect the NetStim to the synapse via a NetCon
            nc1 = h.NetCon(ns1, syn1)
            nc1.weight[0] = np.abs((e2 - e0) / (e1 - e0)) * self.noise["scale"]  # Synaptic weight in μS
            nc2 = h.NetCon(ns2, syn2)
            nc2.weight[0] = self.noise["scale"] # Synaptic weight in μS
            self.noise_cons[name] = (
                {"netstim": ns1, "syn": syn1, "netcon": nc1},
                {"netstim": ns2, "syn": syn2, "netcon": nc2}
            )
        
        self.set_seed()
    
    
    def set_seed(self):
        num_seeds = 2 * len(self.cells)  # 2 seeds per NetStim, 2 NetStims per cell
        if self.seed:
            seeds = np.arange(1, num_seeds+1,dtype=int)
        else:
            seeds = np.random.choice(np.arange(1, 1000,dtype=int), size=num_seeds, replace=False)
        seeds = seeds.reshape(2, len(self.cells))        

        for i, ((_, (d1, d2))) in enumerate(self.noise_cons.items()):
            seed1 = seeds[0, i]
            seed2 = seeds[1, i]
            d1["netstim"].seed(seed1)
            d2["netstim"].seed(seed2)
    
    
    def attach_iclamp(self, name: str, loc=0.5, delay=None, dur=None, amp=None):
        """_summary_

        Args:
            name (str): _description_
            loc (float, optional): _description_. Defaults to 0.5.
            delay (_type_, optional): _description_. Defaults to None.
            dur (_type_, optional): _description_. Defaults to None.
            amp (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        try:
            assert name in self.cells, f"Cell name '{name}' not found in cells dict"
            assert 0.0 <= loc <= 1.0, f"loc '{loc}' must be between 0.0 and 1.0, inclusive"
        except AssertionError:
            return h.IClamp()
        delaytime = delay+self.eq_time+self.noise_eq_time if delay is not None else None
        ic = self.cells[name].iclamp(delaytime, dur, amp, loc)
        self.current_clamps.setdefault(name, {})
        if loc in self.current_clamps[name]:
            self.current_clamps[name][loc].append(ic)
        else:
            self.current_clamps[name][loc] = [ic]
        return ic
            
            
    def attach_vclamp(self, name: str, loc=0.5, dur=100.0, amp=1.0, r=1.0, i=1.0):
        self.secondorder = 0
        print("Notice: VClamp is a stiff model. Defaulted to h.secondorder = 0 (Backwards-Euler integration)")
        vc = self.cells[name].vclamp(loc, dur, amp, r, i)
        self.current_clamps.setdefault(name, {})
        if loc in self.voltage_clamps[name]:
            self.voltage_clamps[name][loc].append(vc)
        else:
            self.voltage_clamps[name][loc] = [vc]
    
    
    def remove_iclamp(self, name: str, loc: float, index: int):
        """_summary_

        Args:
            name (str): _description_
            loc (float): _description_
        """
        assert name in self.current_clamps, f"Cell '{name}' must be the name of a cell in the Network, and the IClamp must already exist"
        if name in self.recording and loc in self.recording[name]["clamps"]["I"]:
            del self.recording[name]["clamps"]["I"][loc][index]
        del self.current_clamps[name][loc][index]
    
    
    def remove_vclamp(self, name: str, loc: float, index: int):
        assert name in self.voltage_clamps, f"Cell '{name}' must be the name of a cell in the Network, and the VClamp must already exist"
        if name in self.recording and loc in self.recording[name]["clamps"]["V"]:
            del self.recording[name]["clamps"]["V"][loc][index]
        del self.voltage_clamps[name][loc][index]


    def set_mech_parameter(self, name: str, param: str, val: float) -> None:
        setattr(self.cells[name], f"{param}", val)
    
    
    def set_cs_parameter(self, pre: str, post: str, cstype: str, param: str, val: float) -> None:
        setattr(self.chemical_synapses[cstype][pre][post]["synapse"], param, val)
    
    
    def set_es_parameter(self, pre: str, post: str, param: str, val: float) -> None:
        setattr(self.electrical_synapses[pre][post], param, val)
    
    
    def record_voltage_only(self):
        self.voltage_only = True
        self.recording["t"] = h.Vector().record(h._ref_t)
        for name, cell in self.cells.items():
            cell.recording = {0.5: {"V": h.Vector().record(cell.section(0.5)._ref_v)}}
            self.recording[name] = cell.recording
            # self.record_iclamps(0.5)
            self.recording[name]["clamps"] = {"I": {0.5: {}}, "V": {0.5: {}}}
            if name in self.current_clamps:
                for loc, clamp_list in self.current_clamps[name].items():
                    self.recording[name]["clamps"]["I"][loc] = []
                    for clamp in clamp_list:
                        self.recording[name]["clamps"]["I"][loc].append(h.Vector().record(clamp._ref_i))
            if name in self.voltage_clamps:
                for loc, clamp_list in self.voltage_clamps[name].items():
                    self.recording[name]["clamps"]["V"][loc] = []
                    for clamp in clamp_list:
                        self.recording[name]["clamps"]["V"][loc].append(h.Vector().record(clamp._ref_v))
    
    
    def record_all(self, all_locs = False, at_locs=[0.5]):
        """Records data in every location in the cell. (Might switch to just 0.5 later)
           Data recorded: time, membrane potential, currents from all current mechanisms, Ca and Na pool concentrations if available. 
           Also records injected volage and current if available.

        Args:
            all_locs (bool, optional): If true, ignores at_locs argument. Defaults to False.
            at_locs (list, optional): _description_. Defaults to [0.5].
        """
        self.voltage_only = False
        self.recording["t"] = h.Vector().record(h._ref_t)
        if all_locs:
            locs = [seg.x for seg in cell.section]
        else:
            locs = at_locs
        for name, cell in self.cells.items():
            for loc in locs:
                cell.set_iv_recording(loc)
                if name in self.pools_active.keys():
                    if "ca" in self.pools_active[name]:
                        cell.recording[loc]["cai"] = h.Vector().record(cell.section(loc)._ref_cai)
                    if "na" in self.pools_active[name]:
                        cell.recording[loc]["nai"] = h.Vector().record(cell.section(loc)._ref_nai)
                    if "k" in self.pools_active[name]:
                        cell.recording[loc]["ki"] = h.Vector().record(cell.section(loc)._ref_ki)
                    if "cl" in self.pools_active[name]:
                        cell.recording[loc]["cli"] = h.Vector().record(cell.section(loc)._ref_cli)
            if self.noise is not None:
                cell.recording[0.5]["noise1"] = h.Vector().record(self.noise_cons[name][0]["syn"]._ref_i)
                cell.recording[0.5]["noise2"] = h.Vector().record(self.noise_cons[name][1]["syn"]._ref_i)
            self.recording[name] = cell.recording
            self.recording[name]["clamps"] = {"I": {0.5: []}, "V": {0.5: []}}
            if name in self.current_clamps:
                for loc, clamp_list in self.current_clamps[name].items():
                    self.recording[name]["clamps"]["I"][loc] = []
                    for clamp in clamp_list:
                        self.recording[name]["clamps"]["I"][loc].append(h.Vector().record(clamp._ref_i))
            if name in self.voltage_clamps:
                for loc, clamp_list in self.voltage_clamps[name].items():
                    self.recording[name]["clamps"]["V"][loc] = []
                    for clamp in clamp_list:
                        self.recording[name]["clamps"]["V"][loc].append(h.Vector().record(clamp._ref_v))
        if self.record_synaptic_currents:
            if len(self.chemical_synapses) > 0:
                self.synaptic_currents_recording["chemical"] = {}
            if len(self.electrical_synapses) > 0:
                self.synaptic_currents_recording["electrical"] = {}
            for speed, d1 in self.chemical_synapses.items():
                for pre, d2 in d1.items():
                    for post, d3 in d2.items():
                        self.synaptic_currents_recording["chemical"].setdefault(speed, {})[f"{pre}_2_{post}"] = h.Vector().record(d3["synapse"]._ref_i)
            for pre, d in self.electrical_synapses.items():
                for post, syn in d.items():
                    self.synaptic_currents_recording["electrical"][f"{pre}_2_{post}"] = h.Vector().record(syn._ref_i)
            self.synaptic_currents_recording["t"] = h.Vector().record(h._ref_t)
    
    
    def record(self, voltage_only: bool, all_locs: bool, at_locs: list):
        if voltage_only:
            self.record_voltage_only()
        else:
            self.record_all(all_locs=all_locs, at_locs=at_locs)
    
    
    def setup_run(self, record_none:bool=False,all_locs:bool=False,\
                    voltage_only:bool=False, at_locs=[0.5]):
        for name, c in self.cells.items():
            for seg in c.section:
                seg.v = self.v0[name]
        if self.dt > 0:
            h.dt = self.dt
        else:
            h.cvode.active(True)
            h.cvode.atol(self.atol)
        h.celsius = self.temp
        h.secondorder = self.secondorder
        # if not self.ran_before:
        if not record_none:
            self.record(voltage_only, all_locs=all_locs, at_locs=at_locs) 
        
    
    def run(self, all_locs=False, at_locs=[0.5],voltage_only=False,record_none=False):
        """_summary_

        Args:
            temp (float, optional): Temperature to set simulation at. Defaults to 6.3 (giant squid axon model temperature).
            at_locs (List[float], optional): Provide the locations on the segment to record in every cell. Will error if a location is not on the segment. Defaults to [0.5].
            all_locs (boolean, optional): If true, will record data at every location in the segment in every cell and ignores at_locs argument. Defaults to False.
        """
        self.setup_run(record_none=record_none,voltage_only=voltage_only,all_locs=all_locs, at_locs=at_locs)
        print("Running simulation...")
        start_time = time.time()
        h.finitialize()
        h.continuerun(self.eq_time+self.noise_eq_time+self.simdur)
        end_time = time.time()
        self.simtime = end_time - start_time
        self.ran_before = True


    def reset_recordings(self):
        """Deprecated
        """
        warnings.warn("Warning: using reset_recordings is deprecated. Use h.frecord_init() or h.cvode.re_init() instead (I think?)")
        self.recording["t"].resize(0)
        if self.record_synaptic_currents:
            def resize_recording(d):
                for v in d.values():
                    if isinstance(v, dict):
                        resize_recording(v)
                    else:
                        v.resize(0)
            resize_recording(self.synaptic_currents_recording)
        for k, d in self.recording.items():
            if k != "t":
                for v in d["clamps"]["I"].values():
                    for ic in v:
                        ic.resize(0)
                for v in d["clamps"]["V"].values():
                    for vc in v:
                        vc.resize(0)
        for c in self.cells.values():
            c.reset_recordings()
        self.dt = -1
        gc.collect()
        
        
    def get_synaptic_current_data(self) -> Tuple[dict]:
        """Returns the current data from electrical and chemical synapses, if present. If one is not present, it is returned as None.

        Returns:
            Tuple[dict]: electrical synapse data, chemical synapse data
        """
        adjust_t = 0
        if self.dt > 0:
            if self.secondorder == 1:
                adjust_t = self.dt/2
            elif self.secondorder == 2:
                adjust_t = -self.dt/2
        t = self.synaptic_currents_recording["t"].as_numpy()+adjust_t
        if "chemical" in self.synaptic_currents_recording:
            chem_data = {"t": t}
            for speed, d in self.synaptic_currents_recording["chemical"].items():
                for k, v in d.items():
                    chem_data[f"I_{k}_{speed}"] = v.as_numpy()
        else:
            chem_data = None
        if "electrical" in self.synaptic_currents_recording:
            elec_data = {"t": t}
            for k, v in self.synaptic_currents_recording["electrical"].items():
                elec_data[f"I_{k}"] = v.as_numpy()
        else:
            elec_data = None
        return copy.deepcopy(chem_data), copy.deepcopy(elec_data)
        
        
    def get_cell_data(self, name: str, loc=0.5) -> dict:
        """Function to return all other data from cell, including ion channel currents, applied current injections, membrane potential, and ion concentrations.

        Args:
            name (str): name of cell's data to return.
            loc (float, optional): location within the cell. Defaults to 0.5 (should never be anything else)

        Returns:
            dict: dict of all of the cell's data. 
        """
        c = self.cells[name]
        cell_data = c.get_data(loc)
        adjust_t = 0
        if self.dt > 0:
            if self.secondorder == 1:
                adjust_t = self.dt/2
            elif self.secondorder == 2:
                adjust_t = -self.dt/2
        cell_data["t"] = self.recording["t"].as_numpy()+adjust_t
        indices = np.where(cell_data["t"] > (self.eq_time + self.noise_eq_time))[0]
        if self.noise is not None and not self.voltage_only:
            noise1 = cell_data.pop("noise1")
            noise2 = cell_data.pop("noise2")
            cell_data["noise"] = noise1 + noise2
        for k, v in cell_data.items():
            if k[0] == "I":
                cell_data[k] = c.current_density_to_nA(v, loc)
        for clamp_type, clamp_recording in self.recording[name]["clamps"].items():
            if loc in clamp_recording:
                if len(clamp_recording[loc]) > 0:
                    cell_data[f"{clamp_type}_applied_{loc}"] = np.sum([r.as_numpy() for r in clamp_recording[loc]], axis=0)
        for k in cell_data.keys():
            cell_data[k] = cell_data[k][indices]  # Modify dictionary in-place
        cell_data["t"] -= self.eq_time + self.noise_eq_time
        return copy.deepcopy(cell_data)
            
    
    def get_interpolated_cell_data(self, name: str, tvec: iter, loc=0.5) -> dict:
        """Returns an the cell data linearly interpolated to a time vector.

        Args:
            name (str): cell name to get
            tvec (iter): time vector to interpolate to.
            loc (float, optional): location within cell. Defaults to 0.5 (should never be anything else)

        Returns:
            dict: dictionary of all of the interpolated data
        """
        # cell_data = self.get_cell_data(name, loc)
        # t = cell_data["t"]
        # tu, ind = np.unique(t, return_index=True)  # get indices of unique times in case of duplicates
        # cell_interp = {"t": tvec}
        # for k, v in cell_data.items():
        #     if k != "t":
        #         # cell_interp[k] = np.interp(tvec, t, v)
        #         vu = v[ind]
        #         cs = CubicSpline(tu,vu)
        #         cell_interp[k] = cs(tvec)
        cell_data = self.get_cell_data(name, loc)
        t = cell_data["t"]
        # tu, ind = np.unique(t, return_index=True)  # get indices of unique times in case of duplicates
        cell_interp = {"t": tvec}
        for k, v in cell_data.items():
            if k != "t":
                # cell_interp[k] = np.interp(tvec, t, v)
                cs = CubicSpline(t,v)
                cell_interp[k] = cs(tvec)
                
        return cell_interp
    
    
    def get_interpolated_syn_data(self, tvec: iter) -> Tuple[dict]:
        """Same as NetworkBuilder.get_interpolated_cell_data but interpolates synapse data

        Args:
            tvec (iter): time vector to interpolate to

        Returns:
            Tuple[dict]: interpolated electrical data, chemical data
        """
        chem_data, elec_data = self.get_synaptic_current_data()
        if chem_data is not None:
            chem_interp = {"t": tvec}
            tchem = chem_data["t"]
            tu, ind = np.unique(tchem, return_index=True)
            for k, v in chem_data.items():
                if k != "t":
                    # chem_interp[k] = np.interp(tvec, tchem, v)
                    vu = v[ind]
                    cs = CubicSpline(tu,vu)
                    chem_interp[k] = cs(tvec)
        else:
            chem_interp = None
        if elec_data is not None:
            elec_interp = {"t": tvec}
            telec = elec_data["t"]
            tu, ind = np.unique(telec, return_index=True)
            for k, v in elec_data.items():
                if k != "t":
                    # elec_interp[k] = np.interp(tvec, telec, v)
                    vu = v[ind]
                    cs = CubicSpline(tu,vu)
                    elec_interp[k] = cs(tvec)
        else:
            elec_interp = None
        return chem_interp, elec_interp

    
    def save_state(self,filename:str="state.bin"):
        ss = h.SaveState()
        ss.save()
        sf = h.File(filename)
        ss.fwrite(sf)

    def restore_state(self,filename:str):
        ss = h.SaveState()
        sf = h.File(filename)
        ss.fread(sf)
        ss.restore()

    def generate_metadata(self,voltage_only,folder):
        """Interpolate metadata and information regarding the simulation. Includes NEURON runtime, storage location, integration method, tiemstep and more.
        """
        def count_syns(d):
            count = 0
            if isinstance(d, dict):
                for value in d.values():
                    count += count_syns(value)  # Recursively count in nested dictionaries
            else:
                count += 1  # Base case: when it's not a dictionary, it's a value
            return count
        
        method = {
            1: "Backwards Euler",
            2: "Crank-Nicholson"
        }
        
        def get_timestep(dt):
            if dt == -1:
                return "variable"
            else:
                return f"{dt} ms"
        
        metadata = {"Simulation name": self.sim_name,
                    "Model file": self.params_file,
                    "Data saved to": f"./Data/{self.sim_name}_data/",
                    "NEURON finished in": f"{self.simtime} s",
                    "Simulation duration": f"{self.simdur} ms",
                    "Integration method": method[self.integrator],
                    "Timestep": get_timestep(self.dt),
                    "Absolute error tolerance": self.atol,
                    "Number of cells": len(self.cells),
                    "Number of electrical synapses": int(count_syns(self.electrical_synapses)/2),
                    "Number of chemical synapses": int(count_syns(self.chemical_synapses)/2)}
        
        if voltage_only:
            metadata["Data saved to"] = f"{folder}/{self.sim_name}_data.h5"
        
        if self.noise is not None:
            metadata["Noise"] = f"rate = {self.noise['rate']} Hz, scale = {self.noise['scale']} uS, tau = {self.noise['tau']} ms"
            # metadata["Noise"] = f"rate = {self.noise['rate']} Hz, stddev = {self.noise['std']} ms"
        
        with open(os.path.join(self.cwd, os.path.join(folder,"info.txt")), 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
