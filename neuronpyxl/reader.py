"""
This file is part of neuronpyxl.

The ControlReader is a helper class to read in the parameters from the Excel
spreadsheet models. FYI: This code was taylored to the exact format of the Excel
spreadsheets, so adding new features requires significant refactoring of code.

Copyright (C) 2026 Uri Dickman, Curtis Neveu, Hillel Chiel, Peter Thomas

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
import xlsxwriter
import warnings
warnings.simplefilter(action='ignore', category=UserWarning)

class ExcelReader:
    def __init__(self, filename, sim_name, nrows):
        """Helper class to handle reading the "control.xlsx" spreadsheet for \
            running SNNAP simulations via the Network class. The spreadsheet \
                must be used in the exact format provided to be read in properly without errors.
        Args:
            filename (str): name of the control file. Must be a *.xlsx file.
            sim_name (str): name of the sheet (sim_name.smu) to retrieve the current injection information from.
            nrows (int): number of rows to look at (number of cells in the network).
        """
        self.nrows = nrows # Currently hard coding the number of cells
        self.usecols_neurons = f"{xlsxwriter.utility.xl_col_to_name(1)}:{xlsxwriter.utility.xl_col_to_name(nrows+1)}"
        self.sim_name = sim_name
        self.read_data(filename) # read in all of the data
        # TODO: self.detect_num_cells(filename)
        
        
    def detect_num_cells(self,filename) -> int:
        """Doesn't work.
        """
        nrows = 0

        xls = open(pd.ExcelFile(filename,engine='openpyxl'),"rb")
        df_tmp = pd.read_excel(xls, sheet_name="Neu")
        start_row = 2 + df_tmp.index[df_tmp.iloc[:, 3] == "cm"][0]
        print("nrows = ",df_tmp.iloc[[start_row]])

        return nrows


    def read_data(self,filename):
        """Reads in all of the data from the Excel spreadsheet and saves it as dataframes in class variables.
        """
        xls = open(pd.ExcelFile(filename,engine='openpyxl'),"rb")
        #### neu
        df_neu = pd.read_excel(xls, 'Neu', header=[0,1,2], index_col=0, nrows=self.nrows)
        self.mechs_data = df_neu.iloc[:, 3:] # Reads in all of the mechanism names
        df_cells = pd.read_excel(xls, 'Neu', header=2, index_col=0, nrows=self.nrows)
        self.cells_data = df_cells.iloc[:, [0,2]] # Biophysical properties from each cell (name and Cm)
        
        #### ion pools
        df_tmp = pd.read_excel(xls, sheet_name="Neu")
        
        start_row_pools = 2 + df_tmp.index[df_tmp.iloc[:, 3] == "Ion pools"][0]
        df_pools = pd.read_excel(xls, sheet_name="Neu", 
                                header=start_row_pools, index_col=0, nrows=self.nrows, usecols="D:M")
        self.ion_pools_data = self.rename_df_cols(df_pools) # All of the ion pools present in the model.

        #### conductance to ion
        start_row_cond = 2 + df_tmp.index[df_tmp.iloc[:, 14] == "Conductance to ion"][0]
        df_cond = pd.read_excel(xls, sheet_name="Neu",
                                header=start_row_cond, index_col=0, nrows=self.nrows, usecols="O:W")
        # In each cell, maps which ion channels feed the ion pools.
        self.cond_to_ion_data = self.rename_df_cols(df_cond)

        #### ion to conductance
        start_row_ion = 2 + df_tmp.index[df_tmp.iloc[:, 25] == "Ion to conductance"][0]
        df_ion = pd.read_excel(xls, sheet_name="Neu",
                               header=start_row_ion, index_col=0, nrows=self.nrows, usecols="Z:BB")
        # In each cell, determines which ion channels are regulated by ion pools (e.g. Kcas).
        self.ion_to_cond_data = self.rename_df_cols(df_ion)

        #### initial voltage
        start_row_v0 = 2 + df_tmp.index[df_tmp.iloc[:, 55] == "Initial voltage"][0]
        df_v0 = pd.read_excel(xls, sheet_name="Neu",
                              header=start_row_v0, index_col=0, nrows=self.nrows, usecols="BD:BE")
        self.initial_voltage_data = df_v0.copy() # Reads initial voltages of each cell.
        
        #### cs_g
        df_csg = pd.read_excel(xls, 'cs_g',
                               header=1, index_col=0, nrows=self.nrows*2, usecols=self.usecols_neurons)
        df_csg.index = pd.Series(df_csg.index).ffill()
        # This one is complicated. Reads in the conductances from the CS matrix.
        self.csg = {"fast": {}, "slow": {}}
        for i, (presyn, row) in enumerate(df_csg.iterrows()):
            for postsyn, val in row.dropna().items():
                if i % 2 == 0:
                    self.csg["fast"].setdefault(presyn, {})[postsyn] = val
                else:
                    self.csg["slow"].setdefault(presyn, {})[postsyn] = val
        
        #### cs_e
        df_cse = pd.read_excel(xls, 'cs_E',
                               header=1, index_col=0, nrows=self.nrows*2, usecols=self.usecols_neurons)
        df_cse.index = pd.Series(df_cse.index).ffill()
        self.cse = {"fast": {}, "slow": {}} # Reads reversal potentials of the CS matrix.
        for i, (presyn, row) in enumerate(df_cse.iterrows()):
            for postsyn, val in row.dropna().items():
                if i % 2 == 0:
                    self.cse["fast"].setdefault(presyn, {})[postsyn] = val
                else:
                    self.cse["slow"].setdefault(presyn, {})[postsyn] = val
        
        #### cs_fat
        df_csfat_nums = pd.read_excel(xls, 'cs_FAT',
                                      header=1, index_col=0, nrows=self.nrows*2, usecols=self.usecols_neurons)
        df_csfat_nums.index = pd.Series(df_csfat_nums.index).ffill()
        # Reads in the number corresponding to the type of chemical synapse.
        self.csfat_nums = {"fast": {}, "slow": {}}
        for i, (presyn, row) in enumerate(df_csfat_nums.iterrows()):
            for postsyn, val in row.dropna().items():
                # Even rows are fast, odd rows are slow (1st row is 0)
                if i % 2 == 0:
                    self.csfat_nums["fast"].setdefault(presyn, {})[postsyn] = val
                else:
                    self.csfat_nums["slow"].setdefault(presyn, {})[postsyn] = val

        df_csfat_params = pd.read_excel(xls, sheet_name='cs_FAT', index_col=25, header=[0,1])
        df_csfat_params = df_csfat_params.iloc[:, 25:35]
        # Fills in the parameter values according to the number from csfat_nums. Distinguishes fast and slow
        self.csfat_params_fast = {}
        self.csfat_params_slow = {}

        # Access the parameter based on the num from self.csfat_nums
        for presyn, d in self.csfat_nums["fast"].items():
            for postsyn, num in d.items():
                self.csfat_params_fast.setdefault(presyn, {})[postsyn] = df_csfat_params.loc[num]
        for presyn, d in self.csfat_nums["slow"].items():
            for postsyn, num in d.items():
                self.csfat_params_slow.setdefault(presyn, {})[postsyn] = df_csfat_params.loc[num]
        
        #### es
        df_esg = pd.read_excel(xls, 'es',
                               header=1, index_col=0, nrows=self.nrows*2, usecols=self.usecols_neurons)
        df_esg.index = pd.Series(df_esg.index).ffill()
        self.esg_data = df_esg.copy() # Reads conductances for electrical synapses
        self.esg_data = self.clean_table(self.esg_data)

        #### current injection
        df_tmp = pd.read_excel(xls, f"{self.sim_name}.smu")
        start_row_clamp = 2 + df_tmp.index[df_tmp.iloc[:, 1] == "Current injection"][0]
        df_clamps = pd.read_excel(xls, sheet_name=f"{self.sim_name}.smu",
                                  header=start_row_clamp, index_col=0, usecols="B:E")
        self.iclamp_data = df_clamps.copy() # Reads in IClamp data based on the sim_name.

        xls.close()

        
    def clean_table(self, df):
        df_tmp = df.loc[:, ~((df.isna() | (df == 0)).all())]
        return df_tmp.loc[:, [isinstance(c, str) for c in df_tmp.columns]]

    def rename_df_cols(self, df):
        """Helper method to rename duplicate column names in a systematic way.

        Args:
            df (pd.DataFrame): a Pandas DataFrame

        Returns:
            pd.DataFrame: copy of df with relabeled duplicate columns of the form "{colname}_{numduplicates}". \
                        If there aren't any duplicates, the column name won't change.
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
