"""
This file is part of neuronpyxl.

The ModBuilder class is necessary for running SNNAP-like simulations. It uses the
stencil files located in neuronpyxl/modls/ to generate the mod files. There will be
1 mod file for each ion channel, and it will use the correct ion in that channel if
notated properly (name of the ion channel has to start with either Cl, Ca, K, or Na,
not case-sensitive). These files detail the equations that can be used within the simulation,
the parameters of which are set in the NetworkBuilder class. Will use a nonspecific ion
if it does not begin with one of those ions.

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

import pandas as pd
import os
import shutil
from typing import List
import re
import sys
from importlib.resources import files

class ModBuilder:
    def __init__(self, file: str):
        """A class to automatically generate NMODL mod files that correspond to the 
        SNNAP-based model in the provided spreadsheet. Through the run() command,
        creates one mod file per current mechanism and ion pool. It also creates a file for chemical
        and electrical synapses (cs.mod and es.mod).

        Args:
            file (str): file path to a .xlsx spreadsheet.
        """
        assert file.split(sep=".")[-1] == "xlsx", f"File '{file}' must be a .xlsx file."
        self.modls_path = files("neuronpyxl.modls") # Get the files from neuronpyxl
        self.mod_path = os.path.join(os.getcwd(), "mod")
        self.xls = pd.ExcelFile(file)
        self.nrows = 21 # TODO: make this adapt to the number of cells in the spreadsheet
        self.valence = {"k": 1, 
                "ca": 2,
                "na": 1,
                "cl": -1}
        self.pools = self.read_pools() # Get the ion pools present in the model
        self.mechs = self.read_mechs() # Get the mechanisms present in the model
        
        
    def run(self, cluster: bool = False):
        """Function to generate all of the mod files.
        """
        self.clear_dir("./mod", cluster) # clear out the mod directory
        # Copy cs.mod and es.mod whether or not they are specified in the spreadsheet
        shutil.copy(self.modls_path.joinpath("cs.mod"), self.mod_path)
        shutil.copy(self.modls_path.joinpath("es.mod"), self.mod_path)
        self.gen_mech_mods() # generate current mechanism mod files
        self.gen_pool_mods() # generate ion pool mod files
            
            
    def read_pools(self) -> List[str]:
        """Function to read the ion pools available in the model described in self.xls

        Returns:
            List[str]: list of all ion pools present in the model.
        """
        def rename_df_cols(df) -> pd.DataFrame:
            """Helper function to rename the columns of a data frame with duplicate
            names in a systematic way. Ex: ["ion", "ion", "ion"] -> ["ion", "ion_1", "ion_2"]
            Args:
                df (pd.DataFrame): a dataframe with duplicate column names.

            Returns:
                pd.DataFrame: same dataframe with the adjusted names.
            """
            df.columns = df.columns.str.replace(r'\.\d+', '', regex=True)
            seen = {}
            new_columns = []
            for col in df.columns:
                if col in seen:
                    seen[col] += 1
                    new_columns.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    new_columns.append(col)
            df.columns = new_columns
            return df.copy()
        
        df = pd.read_excel(self.xls, sheet_name="Neu") # Gets the sheet with all of the paramaters
        start_row_pools = 2 + df.index[df.iloc[:, 3] == "Ion pools"][0]
        df_pools = pd.read_excel(self.xls, sheet_name="Neu", header=start_row_pools, index_col=0, nrows=self.nrows, usecols="D:M")
        ion_pools_data = rename_df_cols(df_pools) # rename the columns of the df according to above description
        ions = ion_pools_data["ion"].to_list()+ion_pools_data["ion_1"].to_list()+ion_pools_data["ion_2"].to_list()
        pools = []
        for ion in ions:
            if not pd.isna(ion):
                pool = ion.lower().strip()
                if pool not in self.valence.keys():
                    raise ValueError(f"Ion '{ion}' is not avaiable as an ion pool. \
                                     Available ions include Ca, K, Na, and Cl (not case sensitive).")
                if pool not in pools:
                    pools.append(re.sub(r'[^a-zA-Z0-9]', '', ion.lower().strip()))
        return pools
    
    
    def read_mechs(self) -> List[str]:
        """Read all of the mechanisms present in the model from the Excel spreadsheet self.xls

        Returns:
            List[str]: list of all of the current mechanisms available, lowered and stripped.
        """
        df_neu = pd.read_excel(self.xls, 'Neu', header=[0,1,2], index_col=0, nrows=self.nrows)
        df_neu.dropna(axis=1, how="all", inplace=True)
        mechs_data = df_neu.iloc[:, 3:]
        mechs = mechs_data.columns.get_level_values(0).unique().to_list() # Get mechanism names from spreadsheet
        for m in mechs:
            if bool(re.search(r'[^\w\s]', m)):
                raise ValueError(f"Current mechanism '{m}' cannot contain special characters.")
            if not m[0].isalpha():
                raise ValueError(f"Current mechanism '{m}' must start with a letter. \
                                 Numbers and special characters are not allowed.")
        return [re.sub(r'[^a-zA-Z0-9]', '', m.lower().strip()) for m in mechs]


    def clear_dir(self, dir_path: str, cluster:bool = False):
        """Function to clear a directory or create a new one if one doesn't exist.
        If dir_path does exist, prompts the user if it is okay to clear that directory
        unless cluster == True.

        Args:
            dir_path (str): path to clear out
            cluster (bool): (for running on HPC) if cluster == True, does not prompt
                            the user to clear contents of file.
        """
        if os.path.exists(dir_path):
            # Directory exists, empty it
            del_dir = True if cluster else input(f"Clear out contents of {dir_path}? (y/n) ") == "y"
            if not del_dir:
                sys.exit()
            shutil.rmtree(dir_path,ignore_errors=True)  # Remove the directory and its contents
            os.makedirs(dir_path)    # Recreate the empty directory
        else:
            # Directory does not exist, create it
            os.makedirs(dir_path)
    
    
    def gen_mech_mods(self):
        """Generates the mod files for the ion current mechanisms.
        Don't change this please.
        """
        def copy_and_modify_file(input_file: str, output_file: str, line_number: int, new_value: str) -> None:
            """Helper function for gen_mech_mods. Copies and modifies the input file.
            Replaces the line at line_number with the new_value.
            Places new file in the location of output_file.

            Args:
                input_file (str): file path of file to copy.
                output_file (str): file path of copied file.
                line_number (int): line number of the line to be replaced.
                new_value (str): new value of the line at line_number.
            """
            with open(input_file, 'r') as file:
                lines = file.readlines()
            lines[line_number] = new_value + '\n'
            with open(output_file, 'w') as file:
                file.writelines(lines)
                
        self.channels = {}
        line_number = 9
        useion = {"k": "\tUSEION k READ ki",
                "ca": "\tUSEION ca READ cai",
                "na": "\tUSEION na READ nai",
                "cl": "\tUSEION cl READ cli"}
        for ch in self.mechs:
            if ch == "leak": # copy the leak mod file if the mechanism is leak.
                shutil.copy(self.modls_path.joinpath("leak.mod"), self.mod_path)
            else:
                line12 = []
                ions = ["k", "na", "ca", "cl"]
                is_ion = False
                for ion in ions:
                    if ch.startswith(ion):
                        is_ion = True
                        line12.append("".join([useion[ion], f" WRITE i{ion} VALENCE {self.valence[ion]}"]))
                        line12.append("\n")
                        self.channels.setdefault(ion, 0)
                        self.channels[ion] += 1
                        modl_path = self.modls_path.joinpath(f"{ion}.mod")
                    elif ion in self.pools and is_ion:
                            line12.append("".join([useion[ion], f" VALENCE {self.valence[ion]}"]))
                            line12.append("\n")    
                if not is_ion:
                    for ion in ions:
                        if ion in self.pools:
                            line12.append("".join([useion[ion], f" VALENCE {self.valence[ion]}"]))
                            line12.append("\n")
                    modl_path = self.modls_path.joinpath(f"nonspec.mod")
                line12.pop(-1)
                
                copy_and_modify_file(modl_path, os.path.join(self.mod_path, f"{ch}.mod"), \
                                     line_number, f"\tSUFFIX neuronpyxl_{ch}")
                copy_and_modify_file(os.path.join(self.mod_path, f"{ch}.mod"), \
                                     os.path.join(self.mod_path, f"{ch}.mod"), 11, "".join(line12))
    
    
    def gen_pool_mods(self):
        """Generates the mod files for ion pool mechanisms.
        Don't change this.
        """
        for ch, num in self.channels.items():
            if ch not in self.pools:
                continue
            with open(self.modls_path.joinpath(f"pool.mod"), 'r') as file:
                lines = file.readlines()
            
            lines[7] = f"\tSUFFIX neuronpyxl_{ch}pool" + '\n'
            lines[8] = f"\tUSEION {ch} WRITE {ch}i VALENCE {self.valence[ch]}" + '\n'
            
            pointer_line = "\tPOINTER "
            for i in range(num):
                if i > 0:
                    pointer_line += f", i{i+1}"
                else:
                    pointer_line += f"i{i+1}"
            lines[10] = pointer_line + '\n'
            
            assigned_line = f"\tarea (um2)"
            for i in range(num):
                assigned_line += f" i{i+1} (mA/cm2)"
            lines[19] = assigned_line + '\n'
            
            state_line = f"\t{ch}i (mM)"
            lines[23] = state_line + '\n'
            
            initial_line = f"\t{ch}i = 0.0"
            lines[27] = initial_line + '\n'
            
            sum_currs = ""
            for i in range(1, num + 1):
                sum_currs = "+".join([f"i{j}" for j in range(1, i + 1)])
            lines[35] = f"\t{ch}i' = (0.001)*(k1)*(-k2*({sum_currs})*(1e-8)*(area)-{ch}i)\n"
            
            with open(os.path.join(self.mod_path, f"{ch}pool.mod"), 'w') as file:
                file.writelines(lines)