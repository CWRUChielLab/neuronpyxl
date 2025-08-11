#!/bin/bash
#SBATCH --time=36:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=16
#SBATCH --cpus-per-task=1
#SBATCH --mem=64G
#SBATCH -o logs/job.o%j
#SBATCH --mail-type=all
#SBATCH --mail-user=uxd25@case.edu

module load Python/3.10.8-GCCcore-12.2.0
source /home/uxd25/home/MultiRun/venv/bin/activate

yes | neuronpyxl -f gen_mods --file /home/uxd25/home/MultiRun/Excel_files/control_updated.xlsx
python main.py
