"""
This file is part of neuronpyxl.

The Network class is the central class for neuronpyxl. It takes the
simplified results from the ExcelReader and generates the entire network
from that information, assuming that the correctly-named mod files are
already compiled (see ModBuilder). It also has capabilities to run simulations
and record the data directly from NEURON. These functions can be accessed
either through cmd_util.py or by creating a Network object and running the
simulations from another .py file.

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

from neuron import h
import numpy as np
import pandas as pd
import copy
import os
import time
from scipy.interpolate import CubicSpline
from .cell import Cell
from .reader import ExcelReader
from typing import Tuple

class Network:
    def __init__(
            self,
            params_file : str,
            sim_name    : str,
            noise       : tuple,
            dt          : float,
            integrator  : int,
            atol        : float,
            eq_time     : float,
            simdur      : float,
            seed        : bool=False
        ):
        """Network is the main class in NEURONpyxl.
        It is used for interfacing with NEURON and loading the Excel files.
        It also handles simulation control and data saving.

        Args:
            params_file (str): Filepath of Excel file to read in.
            sim_name (str): sheet in the spreadsheet to run.
            noise (tuple): noise parameters tuple (frequency, weight, tau)
            dt (float): timestep. If not provided, will use variables timestep and CVODE.
            integrator (int): 1 -> Backwards Euler, 2 -> Crank-Nicholson if dt is constant.
            atol (float): absolute error tolerance
            eq_time (float): equilibration time
            simdur (float): simulation duration (ms)
            seed (bool): if True, uses deterministic seed (not working).
        """

        self.cwd = os.getcwd()
        h.load_file("stdrun.hoc")       # Necessary for NEURON run procedures
        
        ############# Initialize Network Data Structures #############

        self.cells = {}                 # Dict[cell name -> Cell object] (see cell.py)

        # Electrical synapse dictionary
        # Dict[presynaptic cell name -> Dict[postsynaptic cell name -> PointProcess]]
        self.electrical_synapses = {}

        # Dict[synapse type -> Dict[presynaptic cell name ->
        #                      Dict[postsynaptic cell name ->
        #                      Dict["synapse" -> PointProcess, "netcon" -> NetCon]]]]
        self.chemical_synapses = {"fast": {}, "slow": {}}

        # This is not used, but a function exists to compute if necessary
        self.input_resistance = {} # Dict[name -> resistance]

        # Define noise parameters
        # Rate (Hz): firing frequency, defines Poisson interval
        # Scale (uS): synaptic weight
        # Tau (ms): time constant
        if noise is not None:
            self.noise = {"rate": noise[0], "scale": noise[1], "tau": noise[2]}
        else:
            self.noise = None
        # Noise connections for 
        # Tuple of 2 dicts structured as:
        #       Dict["netstim" -> PointProcess
        #            "syn" -> PointProcess
        #            "netcon" -> PointProcess]
        # First syn is excitatory, second is inhibitory
        self.noise_cons = {}
        self.seed = seed

        # There can be multiple iclamps at the same location.
        self.current_clamps = {}        # Dict[cell name -> List[h.IClamp]]
        self.v0 = {}                    # Initial voltages

        # List of ion pools active in each cell
        self.pools_active = {}          # Dict[cell name -> List[str]]
    
        # Create a 0 reference in case there are unused hoc pointers
        # We use the 0 reference so they can still be added without changing the value.
        # This is used in the ion pool mechanism.
        self.zero_ref = h.Vector(1)
        self.zero_ref.x[0] = 0  # Set the first element to zero
        
        # Prefix for each of the NEURONpyxl NMODL mechanisms:
        self.mech_prefix = "neuronpyxl_"


        ############ Simulation setup parameters #############
        self.dt = dt                    # Timestep
        self.integrator = integrator    # 1: Backwards Euler, 2: Crank-Nicholson, 3: CVODE
        match self.integrator:
            case 1:
                self.secondorder = 0
            case 2:
                self.secondorder = 2
            case 3:
                self.secondorder = 2
        self.atol = atol
        self.interp = 0.005             # Interpolation timestep default
        
        self.eq_time = eq_time          # Relaxation time before recording
        if noise is not None:
            self.noise_eq_time = 1000
        else:
            self.noise_eq_time = 0
        self.simdur = simdur            # Total duration to record after relaxation 
        self.temp = 6.3                 # None of the mechanisms use this
        self.record_synaptic_currents = False

        self.sim_name = sim_name
        self.params_file = params_file

        # Set up recording dictionary -- populated during run step
        # Dict["t" -> time recording, cell name -> Cell recordings for cell in cells]
        self.recording = {} 
        self.synaptic_currents_recording = {}
        self.ran_before = False

        ############ Build the network #############
        self.setup(params_file)         # Load in all parameters to NEURON
    
    
    def add_cell(self, cell: Cell):
        """Function to add a cell to the network.

        Args:
            cell (Cell): a Cell object
        """
        self.cells[cell.name] = cell
    
    
    def print_cell_section(self, name: str, loc: float):
        """Given a cell name, prints all of the mechanisms and parameter \
        values in the provided cell name and location.

        Args:
            name (str): name of the cell to print
            loc (float): location at which to print
        """
        h.psection(self.cells[name].section(loc))


    ############ Define getters and setters for parameter values #############
    ############ within the network to interface with NMODL      #############

    def get_mech_parameter(self, name: str, param: str) -> float:
        """Set the value of a parameter from an ion channel/pool mechanism

        Args:
            name (str): cell name
            param (str): parameter name (see spreadsheet)

        Returns:
            float: value of the parameter
        """
        return getattr(self.cells[name].section(0.5), param)
    
    
    def get_cs_parameter(self, pre: str, post: str, cstype: str, param: str) -> float:
        """Set the value of a parameter of a chemical synapse

        Args:
            pre (str): presynaptic cell name
            post (str): postsynaptic cell name
            cstype (str): chemical synapse type (either fast or slow)
            param (str): parameter name (see spreadsheet csg,cse,csfat)

        Returns:
            float: value of the parameter
        """
        return getattr(self.chemical_synapses[cstype][pre][post]["synapse"], param)
    
    
    def get_es_parameter(self, pre: str, post: str, param: str) -> float:
        """Set the value of a parameter of an electrical synapse

        Args:
            pre (str): presynaptic cell name
            post (str): postsynaptic cell name
            param (str): paramter name (see spreadsheet es)

        Returns:
            float: value of the parameter
        """
        return getattr(self.electrical_synapses[pre][post], param)
    

    def set_mech_parameter(self, name: str, param: str, val: float) -> None:
        """Set the value of a parameter from an ion channel/pool mechanism

        Args:
            name (str): cell name
            param (str): parameter name (see spreadsheet)
            val (float): new parameter value
        """
        setattr(self.cells[name].section(0.5), param, val)
    
    
    def set_cs_parameter(self, pre: str, post: str, cstype: str, param: str, val: float) -> None:
        """Set the value of a parameter of a chemical synapse

        Args:
            pre (str): presynaptic cell name
            post (str): postsynaptic cell name
            cstype (str): chemical synapse type (either fast or slow)
            param (str): parameter name (see spreadsheet csg,cse,csfat)
            val (float): new parameter value
        """
        setattr(self.chemical_synapses[cstype][pre][post]["synapse"], param, val)
    
    
    def set_es_parameter(self, pre: str, post: str, param: str, val:float) -> None:
        """Set the value of a parameter of an electrical synapse

        Args:
            pre (str): presynaptic cell name
            post (str): postsynaptic cell name
            param (str): paramter name (see spreadsheet es)
            val (float): new parameter value
        """
        setattr(self.electrical_synapses[pre][post], param, val)


    def setup(self, file):
        """Calls all of the initialization functions in order to build the network from
        the provided Excel file.

        Args:
            file (pd.ExcelFile): an Excel file read in by Pandas.
        """
        self.reader = ExcelReader(file, self.sim_name, 21)
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
        """Adds all cells present in the model into the network, along with their
        corresponding mechanisms. Sets all parameter values of each mechanism in
        each cell according to those present in the spreadsheet.
        """
        cell_data = self.reader.cells_data
        mechs_data = (
            self.reader.mechs_data[self.reader.mechs_data.index != 0]
            .dropna(axis=0, how="all")
        )
        mechs = [
            m for m in mechs_data.columns.levels[0]
            if "Unnamed" not in m and "File" not in m
        ]
        self.all_mechs = []

        assert not mechs_data.empty and not cell_data.empty, \
            "You must run a simulation with at least one cell."

        for name, row in mechs_data.iterrows():
            vdg_parameters = {}
            cm = cell_data.loc[name]["cm"]

            for m in mechs:
                if m not in row:
                    continue

                r = row[m]

                if r["vdg"].isna().to_numpy().all():
                    continue

                key = m.lower().strip().replace("_", "")

                if key not in self.all_mechs:
                    self.all_mechs.append(key)

                vdg_parameters[key] = {
                    "g": r["vdg"]["g"],
                    "e": r["vdg"]["E"],
                }

                if key == "leak":
                    continue

                if "p" in r["vdg"].index:
                    vdg_parameters[key]["p"] = r["vdg"]["p"]

                if not pd.isna(r["A"]).all():
                    self._set_activation_parameters(vdg_parameters, key, r, "A")
                    if not pd.isna(r["B"]).all():
                        self._set_activation_parameters(vdg_parameters, key, r, "B")
                    else:
                        vdg_parameters[key]["numbtaus"] = 0
                else:
                    vdg_parameters[key]["numataus"] = 0
                    vdg_parameters[key]["numbtaus"] = 0

            mechs_with_prefix = [self.mech_prefix + m for m in vdg_parameters]
            c = Cell(name=name, current_mechs=mechs_with_prefix, cm=cm)

            for mech, d in vdg_parameters.items():
                for param, val in d.items():
                    setattr(c.section(0.5), f"{param}_{self.mech_prefix}{mech}", val)

            self.add_cell(c)
            print(f"Added {c} to the network.")
              

    def _set_activation_parameters(self, vdg_parameters, key, r, var):
        """Helper function to set activation parameters of ion channel mechanisms.\
        A and B are identical sets of equations, so this function sets all parameter \
        values accounting for every possible variable combination that exists within \
        the SNNAP model.

        Args:
            vdg_parameters (dict): main parameter dictionary (see below)
            r (pd.Series): row of the df
            key (str): ion channel mechanism
            var (str): A or B
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

    
    def feed_pools_from_reader(self):
        """Sets up the ion pool feeding mechanism from Python according to the implementation in NMODL.
        If a channel feeds into a pool, then it has a STATE variable for that concentration 
        contribution (e.g. cai_state). Then, the ion pool accumulator mechanism is added into the 
        cell and reads in all the state variables which feed into the pool as pointers. The sum of
        those concentrations becomes the total concentration of the ion pool, which is set by the 
        accumulator and not the channel mechanism.
        """
        possible_ions = ["ca", "na", "k", "cl"]
        max_channels = {}
        for m in self.all_mechs:
            for ion in possible_ions:
                if m.startswith(ion):
                    max_channels.setdefault(ion, 0)
                    max_channels[ion] += 1

        df = (
            self.reader.cond_to_ion_data
            [self.reader.cond_to_ion_data.index != 0]
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
        )
        if df.empty:
            return

        for name, row in df.iterrows():
            pools_data = self.reader.ion_pools_data.loc[name]
            pools_data = pools_data[pools_data.index != 0]
            pools = {}

            for ion_key, k1_key, k2_key in [
                ("ion", "K1", "K2"),
                ("ion_1", "K1_1", "K2_1"),
                ("ion_2", "K1_2", "K2_2"),
            ]:
                ion_value = pools_data[ion_key]
                if isinstance(ion_value, str):
                    pool = ion_value.lower().strip()
                    if pool not in pools:
                        pools[pool] = {"k1": pools_data[k1_key], "k2": pools_data[k2_key]}

            cell : Cell = self.cells[name]
            ions = {}

            for i in range(4):
                ch_col = f"ch_{i}" if i > 0 else "ch"
                ion_col = f"ion_{i}" if i > 0 else "ion"
                if ch_col in df.columns and ion_col in df.columns:
                    if isinstance(row[ch_col], str) and isinstance(row[ion_col], str):
                        ch = row[ch_col].lower().strip()
                        ion = row[ion_col].lower().strip()
                        self.pools_active.setdefault(name, set()).add(ion)
                        ions.setdefault(ion, []).append(ch)

            cell.load_mechanisms([f"{self.mech_prefix}{ion}pool" for ion in self.pools_active[name]])

            for ion, l in ions.items():
                for j, ch in enumerate(l):
                    chmech = getattr(cell.section(0.5), f"{self.mech_prefix}{ion}pool")
                    ref = getattr(cell.section(0.5), f"_ref_i_{self.mech_prefix}{ch}")
                    h.setpointer(ref, f"i{j+1}", chmech)

                if j < max_channels[ion] - 1:
                    for k in range(j + 1, max_channels[ion] - j):
                        h.setpointer(
                            self.zero_ref._ref_x[0],
                            f"i{k+1}",
                            getattr(cell.section(0.5), f"{self.mech_prefix}{ion}pool"),
                        )

            setattr(cell.section(0.5), f"k1_{self.mech_prefix}{ion}pool", pools[ion]["k1"])
            setattr(cell.section(0.5), f"k2_{self.mech_prefix}{ion}pool", pools[ion]["k2"])
                      

    def add_iclamps_from_reader(self):
        """Sets up current clamps to the network, if provided in the spreadsheet.
        """
        if self.reader.iclamp_data.empty:
            return
        for name, row in self.reader.iclamp_data.iterrows():
            self.attach_iclamp(name, delay=row["start"]*1000,
                               dur=(row["stop"]-row["start"])*1000, amp=row["magnitude"]
            )
        
        
    def add_synapses_from_reader(self):
        """Function to add all of the synaptic connections to the network.

        Raises:
            ValueError: raised if a nonexistent ion is listed as facilitating.
        """
        #### Electrical synapses
        df_esg = self.reader.esg_data
        if not df_esg.empty:
            esg_stacked = df_esg[df_esg != 0].stack().dropna()
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
                    
        # Add chemical synapses to network
        df_csg = self.reader.csg
        df_cse = self.reader.cse
        df_cs_params_fast = self.reader.csfat_params_fast
        df_cs_params_slow = self.reader.csfat_params_slow
        self._add_cs(df_csg, df_cse, df_cs_params_fast, "fast")
        self._add_cs(df_csg, df_cse, df_cs_params_slow, "slow")
        

    def _set_attr_cs_params(self, d, syn):
        """Helper method to recursively set values of all
        params in below dictionaries

        Args:
            d (dict): dictionary
            syn (hoc object): synapse, a point process
        """
        for k, v in d.items():
            if isinstance(v, dict):
               self._set_attr_cs_params(v, syn)
            else:
                setattr(syn, k, v)


    def _add_cs(self, dfg, dfe, dfparams, type):
        """Add chemical synapses to a network

        Args:
            dfg (pd.DataFrame): df with synaptic conductances (csg in spreadsheet)
            dfe (pd.DataFrame): df with reversal potentials (esg in spreadsheet)
            dfparams (pd.DataFrame): df with parameters for CS mechanism (cs_fat in spreadsheet)
            type (str): either fast or slow

        Raises:
            ValueError: _description_
        """
        if any(len(df) == 0 for df in [dfg, dfe, dfparams]):
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
                for k, v in dfparams[pre][post].dropna().to_dict().items():
                    params.setdefault(k[0], {})[k[1]] = v

                params["g"] = g
                params["e"] = dfe[type][pre][post]

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
                    ion = params["facilitation"]["ion"].lower().strip()
                    pre_sec = presyn.section(0.5)
                    match ion:
                        case "ca": syn._ref_mod = pre_sec._ref_cai
                        case "na": syn._ref_mod = pre_sec._ref_nai
                        case "k":  syn._ref_mod = pre_sec._ref_ki
                        case "cl": syn._ref_mod = pre_sec._ref_cli
                        case _:
                            raise ValueError(f"{ion} is not a valid facilitation ion. Must be one of Ca, Na, K, or Cl.")
                    params["facilitation"]["u"] *= 1000
                    params["facilitation"]["ion"] = 1

                self._set_attr_cs_params(params, syn)

                nc = h.NetCon(presyn.section(0.5)._ref_v, syn, sec=presyn.section)
                nc.threshold = 0.0
                nc.delay = 0.0
                nc.weight[0] = 0

                self.chemical_synapses[type].setdefault(pre, {})[post] = {"synapse": syn, "netcon": nc}

    
    def add_regulation_from_reader(self):
        """Function to set up ion regulation from an ion pool.

        Raises:
            ValueError: throws a value error if the ion regulator is not
                        one of Ca, Na, K or Cl.
        """
        unitconv = {
            "p1": {1: 1000, 2: 1e-6, 3: 1, 4: 1e6, 5: 1e-6},
            "p2": 1000,
        }
        ions = ["ca", "na", "k", "cl"]
        df = (
            self.reader.ion_to_cond_data
            [self.reader.ion_to_cond_data.index != 0]
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
        )
        if df.empty:
            return

        for name, row in df.iterrows():
            cell = self.cells[name]
            for i in range(4):
                suffix = f"_{i}" if i > 0 else ""
                ch_col = f"ch{suffix}"
                ion_col = f"ion{suffix}"

                if ch_col not in df.columns or ion_col not in df.columns:
                    continue

                ch = row[ch_col].lower().strip()
                ion = row[ion_col].lower().strip()
                opt1 = row[f"opt1{suffix}"]
                opt2 = row[f"opt2{suffix}"]
                p1 = row[f"p1{suffix}"]
                p2_col = f"p2{suffix}"
                b_col = f"b{suffix}"

                try:
                    ion_num = ions.index(ion) + 1
                except ValueError:
                    raise ValueError(f"{ion} is not a valid regulatory ion. Must be one of Ca, Na, K, or Cl.")

                sec = cell.section(0.5)
                setattr(sec, f"region_{self.mech_prefix}{ch}", ion_num)
                setattr(sec, f"opt1_{self.mech_prefix}{ch}", opt1)
                setattr(sec, f"opt2_{self.mech_prefix}{ch}", opt2)
                setattr(sec, f"p1_{self.mech_prefix}{ch}", p1 * unitconv["p1"][opt2])

                if p2_col in df.columns:
                    setattr(sec, f"p2_{self.mech_prefix}{ch}", row[p2_col] * unitconv["p2"])

                if b_col in df.columns:
                    setattr(sec, f"b_{self.mech_prefix}{ch}", row[b_col])
    
    
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

    
    def compute_input_resistance(self):
        """
        Function to compute the imput resistance of each cell in the network.
        """
        for name, cell in self.cells.items():
            z = h.Impedance()
            z.loc(0.5, sec=cell.section)  # Measure impedance at the center of the soma
            z.compute(0)                  # Compute impedance at frequency f=0 (DC)
            self.input_resistance[name] = z.input(0.5, sec=cell.section) 
    
            
    def add_noise(self):
        """
        Function to add noise inthe form of 2 netstims with equal driving force.
        """
        e1 = 60
        e2 = -90
        rate = self.noise["rate"] / 1000 # 1 / ms
        
        def spike_num(rate, simdur):
            return rate*simdur
        
        h.finitialize()
        #h.continuerun(self.noise_eq_time)
        for name, cell in self.cells.items():
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
            # Package the objects together and add it to the class object
            self.noise_cons[name] = (
                {"netstim": ns1, "syn": syn1, "netcon": nc1},
                {"netstim": ns2, "syn": syn2, "netcon": nc2}
            )
        
        self.set_seed()
    
    
    def set_seed(self):
        """
       Doesnt seem to be working yet.
       Intended functionality: deterministically set the seed number as a test for noisy simulations.
        """
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
    
    
    def attach_iclamp(self, name: str, delay:float=None, dur:float=None, amp:float=None):
        """Add an iclamp to the network

        Args:
            name (str): name of cell to insert iclamp
            delay (float, optional): delay of start of current inejction (ms). Defaults to None.
            dur (float, optional): duration of current injection (ms). Defaults to None.
            amp (float, optional): amplitude of current injection (nA). Defaults to None.

        Returns:
            _type_: A hoc current clamp object
        """
        assert name in self.cells, f"Cell name '{name}' not found in cells dict"
        delaytime = delay+self.eq_time+self.noise_eq_time if delay is not None else None
        ic = self.cells[name].iclamp(delaytime, dur, amp, 0.5)
        self.current_clamps.setdefault(name, []).append(ic)
        return ic

    
    def remove_iclamp(self, name: str, index: int):
        """Remove an IClamp from the network

        Args:
            name (str): name of clamp to remove
            index (int): index in the list of clamp to remove (in order of time added)
        """
        assert name in self.current_clamps, \
            f"Cell '{name}' must be the name of a cell in the Network, and the IClamp must already exist"
        if name in self.recording:
            del self.recording[name]["iclamps"][index]
        del self.current_clamps[name][index]
    
    
    def record_voltage_only(self):
        """Record only the voltage traces of the cells in the network
        """
        self.voltage_only = True
        self.recording["t"] = h.Vector().record(h._ref_t)
        for name, cell in self.cells.items():
            cell.recording = {"V": h.Vector().record(cell.section(0.5)._ref_v)}
            self.recording[name] = cell.recording
            if name in self.current_clamps:
                self.recording[name]["iclamps"] = []
                for clamp in self.current_clamps[name]:
                    self.recording[name]["iclamps"].append(h.Vector().record(clamp._ref_i))


    def record_all(self):
        """Records time, membrane potential, currents from all mechanisms, and ion pool
        concentrations if available. Also records injected voltage and current if available.
        """
        self.voltage_only = False
        self.recording["t"] = h.Vector().record(h._ref_t)

        for name, cell in self.cells.items():
            cell.set_iv_recording()

            if name in self.pools_active:
                sec = cell.section(0.5)
                for ion in self.pools_active[name]:
                    cell.recording[f"{ion}i"] = h.Vector().record(getattr(sec, f"_ref_{ion}i"))

            if self.noise is not None:
                cell.recording["noise1"] = h.Vector().record(self.noise_cons[name][0]["syn"]._ref_i)
                cell.recording["noise2"] = h.Vector().record(self.noise_cons[name][1]["syn"]._ref_i)

            self.recording[name] = cell.recording

            if name in self.current_clamps:
                self.recording[name]["iclamps"] = [
                    h.Vector().record(clamp._ref_i)
                    for clamp in self.current_clamps[name]
                ]

        if self.record_synaptic_currents:
            if self.chemical_synapses:
                self.synaptic_currents_recording["chemical"] = {}
            if self.electrical_synapses:
                self.synaptic_currents_recording["electrical"] = {}

            for speed, d1 in self.chemical_synapses.items():
                for pre, d2 in d1.items():
                    for post, d3 in d2.items():
                        self.synaptic_currents_recording["chemical"].setdefault(speed,{})\
                            [f"{pre}_2_{post}"] = \
                            h.Vector().record(d3["synapse"]._ref_i
                        )

            for pre, d in self.electrical_synapses.items():
                for post, syn in d.items():
                    self.synaptic_currents_recording["electrical"][f"{pre}_2_{post}"] = \
                        h.Vector().record(syn._ref_i)

            self.synaptic_currents_recording["t"] = h.Vector().record(h._ref_t)


    def record_other(self, name: str, ref: str):
        """Record a custom hoc pointer."""
        key = ref.replace("_ref_", "")
        self.recording.setdefault(name, {})[key] = h.Vector().record(
            getattr(self.cells[name].section(0.5), ref)
        )


    def record(self, voltage_only: bool):
        """Main function to record hoc pointers

        Args:
            voltage_only (bool): if passed in, only records the voltage
        """
        if voltage_only:
            self.record_voltage_only()
        else:
            self.record_all()


    def setup_run(self, record_none: bool = False, voltage_only: bool = False):
        for name, c in self.cells.items():
            for seg in c.section:
                seg.v = self.v0[name]

        if self.dt > 0:
            h.dt = self.dt
        if self.integrator == 3:
            h.cvode.active(True)
            h.cvode.atol(self.atol)
            h.cvode.maxstep(10)

        h.celsius = self.temp
        h.secondorder = self.secondorder

        if not record_none:
            self.record(voltage_only)


    def run(self, voltage_only: bool = False, record_none: bool = False):
        """Run the NEURON simulations --> record and call the correct solvers
        Prioritizes record_none first.

        Args:
            voltage_only (bool, optional): records only the voltage. Defaults to False.
            record_none (bool, optional): doesn't record anhything. Defaults to False.
        """
        self.setup_run(record_none=record_none, voltage_only=voltage_only)
        print("Running simulation...")
        start_time = time.time()
        h.finitialize()
        h.continuerun(self.eq_time + self.noise_eq_time + self.simdur)
        self.simtime = time.time() - start_time
        self.ran_before = True


    def get_synaptic_current_data(self) -> Tuple[dict]:
        """Returns current data from electrical and chemical synapses, if present.
        If one is not present, it is returned as None.

        Returns:
            Tuple[dict]: chemical synapse data, electrical synapse data
        """
        t = self.synaptic_currents_recording["t"].as_numpy() + self._adjust_t()

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


    def get_cell_data(self, name: str) -> dict:
        """Returns all data from a cell, including ion channel currents, applied current
        injections, membrane potential, and ion concentrations.

        Args:
            name (str): name of the cell whose data to return.

        Returns:
            dict: all of the cell's recorded data.
        """
        adjust_t = self._adjust_t()
        c = self.cells[name]
        cell_data = c.get_data()
        cell_data["t"] = self.recording["t"].as_numpy()

        indices = np.where(cell_data["t"] > (self.eq_time + self.noise_eq_time - adjust_t))[0]

        if self.noise is not None and not self.voltage_only:
            cell_data["noise"] = cell_data.pop("noise1") + cell_data.pop("noise2")

        for k, v in cell_data.items():
            if k[0] == "I" and k != "I_app":
                cell_data[k] = c.current_density_to_nA(v)

        for k in cell_data:
            cell_data[k] = cell_data[k][indices]

        cell_data["t"] -= self.eq_time + self.noise_eq_time + adjust_t

        return copy.deepcopy(cell_data)


    def _adjust_t(self) -> float:
        """Returns the time adjustment for the current secondorder setting."""
        if self.dt > 0:
            if self.secondorder == 1:
                return self.dt / 2
            if self.secondorder == 2:
                return -self.dt / 2
        return 0
            
   
    def interpolate_data(self,tvec:np.array,t:np.array,y:np.array):
        # Remove duplicates and ensure t is strictly increasing
        # I think there's a way to do this in NEURON but I havne't figured it out yet.
        # This way is janky.
        t_sorted, unique_indices = np.unique(t, return_index=True)
        y_sorted = y[unique_indices]
        cs = CubicSpline(t_sorted, y_sorted)
        return cs(tvec)


    def get_interpolated_cell_data(self, name: str, tvec: np.array) -> dict:
        """Returns an the cell data linearly interpolated to a time vector.

        Args:
            name (str): cell name to get
            tvec (iter): time vector to interpolate to.

        Returns:
            dict: dictionary of all of the interpolated data
        """
        cell_data = self.get_cell_data(name)
        t = cell_data["t"]
        cell_interp = {"t": tvec}
        
        for k, v in cell_data.items():
            if k != "t":
                cell_interp[k] = self.interpolate_data(tvec, t, v)
        return cell_interp
    
    
    def get_interpolated_syn_data(self, tvec: iter) -> Tuple[dict]:
        """Same as Network.get_interpolated_cell_data but interpolates synapse data

        Args:
            tvec (iter): time vector to interpolate to

        Returns:
            Tuple[dict]: interpolated electrical data, chemical data
        """
        chem_data, elec_data = self.get_synaptic_current_data()
        if chem_data is not None:
            chem_interp = {"t": tvec}
            tchem = chem_data["t"]
            for k, v in chem_data.items():
                if k != "t":
                    chem_interp[k] = self.interpolate_data(tvec, tchem, v)
        else:
            chem_interp = None
        if elec_data is not None:
            elec_interp = {"t": tvec}
            telec = elec_data["t"]
            for k, v in elec_data.items():
                if k != "t":
                    elec_interp[k] = self.interpolate_data(tvec, telec, v)
        else:
            elec_interp = None
        return chem_interp, elec_interp

    
    def save_state(self,filename:str="state.bin"):
        """ Saves the state of the current neuron simulation.
        
        Args:
            filename (str): filename of the state file to save to

        """
        ss = h.SaveState()
        ss.save()
        sf = h.File(filename)
        ss.fwrite(sf)


    def restore_state(self,filename:str):
        """ Restores the state of the simulation. In order for this to work, the simulation
        must be set up exactly the same as when the state file was saved.

        Args:
            filename (str): name of the state file to restore.

        """
        h.stdinit()
        ss = h.SaveState()
        sf = h.File(filename)
        ss.fread(sf)
        ss.restore()


    def generate_metadata(self,voltage_only,folder):
        """Interpolate metadata and information regarding the simulation.
        Includes NEURON runtime, storage location, integration method, tiemstep and more.
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
            2: "Crank-Nicholson",
            3: "CVODE"
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
            metadata["Noise"] = f"rate = {self.noise['rate']} Hz, \
                                scale = {self.noise['scale']} uS, tau = {self.noise['tau']} ms"
        
        with open(os.path.join(self.cwd, os.path.join(folder,"info.txt")), 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")