"""
This file is part of neuronpyxl.

The Cell class treats each cell in NEURON as a custom object. Each Cell
comes with a NEURON section property, as well as other useful properties,
such as I-V recordings and current clamps.

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
from typing import List
import numpy as np

class Cell:
    
    _next_gid = 1 # to give each new Cell instance a gid
    
    def __init__(self, name: str, current_mechs: List[str], other_mechs=[], cm=0.001, diam=500., L=100., Ra=35.4):
        """Constructor for a Cell object. Each cell has biophysical properties, ion current and concentration mechanisms, current injections, and recordings.

        Args:
            name (str): name of the cell
            current_mechs (List[str]): ion current mechanisms inserted into the cell
            other_mechs (list, optional): other mechanisms to be inserted. Defaults to [].
            cm (float, optional): membrane capacitance (uF). Defaults to 0.001.
            diam (_type_, optional): diameter of the cell. Defaults to 500.0 um.
            L (_type_, optional): length of the cell. Defaults to 100.0 um.
            Ra (float, optional): cytoplasmic resistivity of the cell. Defaults to 35.4 Ohm*cm.
        """
        # Set up name and gid of the Cell
        self.name = name
        self._gid = Cell._next_gid # automatically assign a gid to each cell, incrementing by 1 for each additional cell, and starting at 1.
        Cell._next_gid += 1
        
        # Topology
        self.section = h.Section(name=name, cell=self)
        # Geometry
        self.section.L = L
        self.section.diam = diam
        # Not really sure that this is necessary because there is no compartment-based modeling in SNNAP, but it's here if this should be incorporated in the future.
        self.section.nseg = int((L/(0.1*h.lambda_f(100, self.section))+.999)/2)*2 + 1 # d_lambda rule, see NEURON docs
        self.area = self.section(0.5).area()*1e-8
        
        # Biophysical properties
        self.section.Ra = Ra
        self.section.cm = cm/self.area # set the specific membrane capacitance according to the area at 0.5 as a convention
        
        # Insert mechanisms
        self.current_mechs = current_mechs
        if len(self.current_mechs) > 0:
            self.load_mechanisms(self.current_mechs)
        self.other_mechs = other_mechs # Pretty sure this is deprecated.
        if len(other_mechs) > 0:
            self.load_mechanisms(self.other_mechs)
        
        self.recording = {}
    
    
    def __repr__(self) -> str:
        """Representation of the cell includes its id and name.

        Returns:
            str: _description_
        """
        return f"Cell(gid={self._gid}, name={self.name})"
    
    
    def load_mechanisms(self, mechs: List[str]):
        """_summary_

        Args:
            mechs (List[str]): _description_
        """
        for m in mechs:
            try:
                self.section.insert(m)
            except ValueError:
                print(f"{m} is not a valid mechanism for cell {self.name}.")
                raise
            
            
    def iclamp(self, delay: float, dur: float, amp: float, loc=0.5):
        """Creates an iclamp given the parameters in neuron.

        Args:
            delay (float): when IClamp starts injecting current.
            dur (float): how long to inject current.
            amp (float): how much current (nA)
            loc (float, optional): Location in the cell. Defaults to 0.5.

        Returns:
            h.IClamp: the IClamp hoc object
        """
        ic = h.IClamp(self.section(loc))
        if delay is not None:
            ic.delay = delay
        if dur is not None:
            ic.dur = dur
        if amp is not None:
            ic.amp = amp
        return ic
    
    
    def get_attribute(self, loc: float, mech: str, attr: str) -> float:
        """Gets an attribute from this Cell.

        Args:
            loc (float): location in cell
            mech (str): mechanism to access (e.g. Ka, Napp, HCN)
            attr (str): attribute of interest (e.g. g, e, th1, tmaxA) \
                        (see RANGE variables in mod files for all attributes)

        Returns:
            float: the value of the attribute
        """
        return getattr(self.section(loc), f"{attr}_{mech}")
    
    
    def get_reference(self, loc: float, attr: str) -> any:
        """Get the reference (hoc object/pointer) of the mechanism provided

        Args:
            loc (float): location in cell
            attr (str): attribute of to get

        Returns:
            any: hoc pointer to the hoc object
        """
        return getattr(self.section(loc), f"_ref_{attr}")
    
    
    def set_attribute(self, loc: float, attr: str, val: float):
        """Set the value of an attribute

        Args:
            loc (float): location in cell
            attr (str): attribute (e.g. g_neuronpyxl_na) (see mod files)
            val (float): value to set it to
        """
        setattr(self.section(loc), attr, val)


    def current_density_to_nA(self, ivec) -> iter:
        """Unit conversion helper function to convert distributed currents to absolute units.

        Args:
            ivec (): distributed current vector
            loc (float, optional): Location in the cell. Defaults to 0.5.

        Returns:
            iter: _description_
        """
        return ivec*self.area*1e6


    def set_iv_recording(self):
        """Set up recording of currents and voltage in the cell.
        """
        loc = 0.5
        self.recording = {}
        self.recording["V"] = h.Vector().record(self.section(loc)._ref_v) # record potential
        
        self.recording["I"] = {} # record all currents
        for m in self.current_mechs:
            self.recording["I"][m] = h.Vector().record(self.get_reference(loc, f"i_{m}"))
        self.recording["I"]["cap"] = h.Vector().record(self.section(loc)._ref_i_cap)


    def set_other_recording(self, mech: str, attr: str):
        self.recording[attr] = h.Vector().record(self.get_reference(0.5, f"{attr}_{mech}"))
    
    
    def get_data(self) -> dict:
        """Recursively get data from the recording dictionary. Used by the Network.

        Returns:
            dict: Dictionary with all of the recordings. Direct key-val mapping depth of 1.
        """
        def flatten_dict(d, parent_key='', sep='_'):
            items = {}
            for k, v in d.items():
                new_key = f'{parent_key}{sep}{k}' if parent_key else k
                if isinstance(v, dict):
                    items.update(flatten_dict(v, new_key, sep=sep))
                elif isinstance(v,list):
                    items["I_app"] = np.sum([r.as_numpy() for r in self.recording["iclamps"]],axis=0)
                else:
                    items[new_key.replace("neuronpyxl_", "")] = v.as_numpy()
            return items
        return flatten_dict(self.recording)
