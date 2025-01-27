"""
This file is part of pySNNAP.

The Cell class treats each cell in NEURON as a custom object. Each Cell comes with a NEURON Section
object, as well as other useful properties, such as I-V recordings and current clamps. This structure
enables the NetworkBuilder class to seem more like a network, rather than leaving the cells as sections only.

Copyright (C) 2024 Uri Dickman, Curtis Neveu, Hillel Chiel, Peter Thomas

pySNNAP is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

pySNNAP is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pySNNAP. If not, see <https://www.gnu.org/licenses/>.
"""

from neuron import h
from typing import List

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
        self.section.nseg = int((L/(0.1*h.lambda_f(100, self.section))+.999)/2)*2 + 1 # d_lambda rule, see NEURON docs
        self.area = {seg.x: self.section(seg.x).area()*1e-8 for seg in self.section} # maps area of cell at each location available in the cell. 0.5 is always a location in the cell
        
        # Biophysical properties
        self.section.Ra = Ra
        self.section.cm = cm/self.area[0.5] # set the specific membrane capacitance according to the area at 0.5 as a convention
        
        # Insert mechanisms
        self.current_mechs = current_mechs
        if len(self.current_mechs) > 0:
            self.load_mechanisms(self.current_mechs)
        self.other_mechs = other_mechs
        if len(other_mechs) > 0:
            self.load_mechanisms(self.other_mechs)
        
        self.recording = {}
    
    
    def __repr__(self) -> str:
        """_summary_

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
        """_summary_

        Args:
            delay (float): _description_
            dur (float): _description_
            amp (float): _description_
            loc (float, optional): _description_. Defaults to 0.5.

        Returns:
            _type_: _description_
        """
        ic = h.IClamp(self.section(loc))
        if delay is not None:
            ic.delay = delay
        if dur is not None:
            ic.dur = dur
        if amp is not None:
            ic.amp = amp
        return ic
    
    
    def vclamp(self, loc=0.5, dur=100.0, amp=1.0, r=1.0, i=1.0):
        vc = h.SEClamp(self.section(loc))
        vc.dur1 = dur
        vc.amp1 = amp
        vc.rs = r
        vc.i = i
        return vc


    def get_attribute(self, loc: float, mech: str, attr: str) -> any:
        return getattr(self.section(loc), f"{attr}_{mech}")
    
    
    def get_reference(self, loc: float, attr: str) -> any:
        return getattr(self.section(loc), f"_ref_{attr}")
    
    
    def set_attribute(self, loc: float, attr: str, val: float):
        setattr(self.section(loc), attr, val)


    def current_density_to_nA(self, ivec: iter, loc=0.5) -> iter:
        """_summary_

        Args:
            ivec (iter): _description_
            loc (float, optional): _description_. Defaults to 0.5.

        Returns:
            iter: _description_
        """
        return ivec*self.area[loc]*1e6


    def set_iv_recording(self, loc: float):
        """_summary_

        Args:
            loc (float): _description_
        """
        self.recording[loc] = {}
        self.recording[loc]["V"] = h.Vector().record(self.section(loc)._ref_v) # record potential
        
        self.recording[loc]["I"] = {} # record all currents
        for m in self.current_mechs:
            self.recording[loc]["I"][m] = h.Vector().record(self.get_reference(loc, f"i_{m}"))
        self.recording[loc]["I"]["cap"] = h.Vector().record(self.section(loc)._ref_i_cap)


    def set_other_recording(self, loc: float, mech: str, attr: str):
        self.recording[loc][attr] = h.Vector().record(self.get_reference(loc, f"{attr}_{mech}"))
    
    
    def get_data(self, loc=0.5) -> dict:
        """_summary_

        Args:
            loc (float, optional): _description_. Defaults to 0.5.

        Returns:
            dict: _description_
        """
        def flatten_dict(d, parent_key='', sep='_'):
            items = {}
            for k, v in d.items():
                new_key = f'{parent_key}{sep}{k}' if parent_key else k
                if isinstance(v, dict):
                    items.update(flatten_dict(v, new_key, sep=sep))
                else:
                    items[new_key.replace("pysnnap_", "")] = v.as_numpy()
            return items
        return flatten_dict(self.recording[loc])


    def reset_recordings(self):
        """_summary_
        """
        def resize_recordings(d):
            for v in d.values():
                if isinstance(v, dict):
                    resize_recordings(v)
                elif isinstance(v, list):
                    for e in v:
                        e.resize(0)
                else:
                    v.resize(0)
        resize_recordings(self.recording)