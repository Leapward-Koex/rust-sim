import os
import matplotlib.pyplot as plt
import numpy as np
import json
import tkinter as tk
import matplotlib.patches as mpatches

from tkinter import filedialog

# Get filepath of json
# Create a root window and hide it
root = tk.Tk()
root.withdraw()

# Get the current working directory
current_directory = os.getcwd()

# Open file dialog with the current directory as the default
filepath = filedialog.askopenfilename(initialdir=current_directory, filetypes=[("JSON files", "*.json")])

# Load dictionary into 'data_file' variable
with open(filepath, 'r') as file:
    data_file = json.load(file)

fig, ax = plt.subplots(1)
fig.set_size_inches(12, 8)

#Set titles
plot_label_size = 16
titles_size = 18 

# Create patches for the legend
lowest_patch = mpatches.Patch(color='lightseagreen', label='0.001%')
low_patch = mpatches.Patch(color='teal', label='0.01%')
high_patch = mpatches.Patch(color='tab:blue', label='0.1%')
highest_patch = mpatches.Patch(color='blue', label='1%')

#Plot graph 1
ax.plot(data_file['x_axis_values'], data_file['mean_res'], color = "lightseagreen")
ax.fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)


# Get next file from user
filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
with open(filepath, 'r') as file:
    data_file = json.load(file)

#Plot graph 2
ax.plot(data_file['x_axis_values'], data_file['mean_res'], color = "teal")
ax.fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)

# Get next file from user
filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
with open(filepath, 'r') as file:
    data_file = json.load(file)

#Plot graph 3
ax.plot(data_file['x_axis_values'], data_file['mean_res'], color = "tab:blue")
ax.fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)

# Get next file from user
filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
with open(filepath, 'r') as file:
    data_file = json.load(file)

#Plot graph 4
ax.plot(data_file['x_axis_values'], data_file['mean_res'], color = "blue")
ax.fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)

# Hide x labels and tick labels for top plots and y ticks for right plots.
ax.set_ylim([0, 1])
ax.legend(handles=[highest_patch, high_patch, low_patch, lowest_patch], loc="upper right", title = "Mutation rate")

# Adding a single x-axis label and y-axis label
fig.text(0.5, 0.04, 'Developmental Cycles', ha='center', va='center', fontsize=titles_size)
fig.text(0.06, 0.5, 'Proportion of possible alleles', ha='center', va='center', rotation='vertical', fontsize=titles_size)

#fig.suptitle("Vegetative cost of allele determines stable frequency", fontsize=titles_size)

plt.show()