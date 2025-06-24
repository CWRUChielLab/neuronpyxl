#!/usr/bin

homedir="/home/udickman/Desktop/Projects/CWRU/neuronpyxl"

if [[ -d "$homedir" ]]; then

  cat "$homedir exists"

else

  echo "Error: File $homedir not found"

fi
# Activate python environment
mamba activate neuronpyxl-env

# Save data
python $homedir/Examples/heatmap.py
#python $homedir/save_noisy_data.py
python $homedir/Examples/mean_phase_dur.py
python $homedir/Examples/bar.py

