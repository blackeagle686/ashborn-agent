import os
import subprocess

# Change directory to scratch_test
dir_path = 'scratch_test'
if not os.path.exists(dir_path):
    os.makedirs(dir_path)
os.chdir(dir_path)

# Execute calc.py using Python interpreter
subprocess.run(['python', 'calc.py'])
