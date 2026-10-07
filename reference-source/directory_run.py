import os
import subprocess
import argparse

# Set up argument parsing
parser = argparse.ArgumentParser(description='Run a command on all .json files in a specified directory.')
parser.add_argument('directory', type=str, help='The path to the directory containing the .json files')

args = parser.parse_args()

# Define the directory and command template
directory1 = "c:/Users/tehch/OneDrive/Documents/GitHub/DictySimulator"
python_exe = os.path.join(directory1, ".conda", "python.exe")
script = os.path.join(directory1, "dicty_sim_test_env.py")

# Iterate over all files in the directory
for filename in os.listdir(args.directory):
    if filename.endswith(".json"):
        json_file = os.path.join(args.directory, filename)
        command = f'"{python_exe}" "{script}" --param "{json_file}"'
        
        # Run the command
        subprocess.run(command, shell=True)