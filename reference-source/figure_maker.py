import os
import matplotlib.pyplot as plt
import numpy as np
import json
import tkinter as tk
import matplotlib.patches as mpatches

from tkinter import filedialog
from matplotlib import font_manager

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

fig, axs = plt.subplots(2, 2)
fig.set_size_inches(12, 8)

#Set titles
full_title = 'Mutation rates, no epistasis'
graph1_title = '1%'
graph2_title = '0.1%'
graph3_title = '0.01%'
graph4_title = '0.001%'

plot_label_size = 16
titles_size = 18 

# Create patches for the legend
cheaters_patch = mpatches.Patch(color='red', label='Cheater alleles')
resistors_patch = mpatches.Patch(color='blue', label='Resistor alleles')

#Plot graph 1
axs[0, 0].plot(data_file['x_axis_values'], data_file['mean_ch'], color = "red", label = 'Cheaters')
axs[0, 0].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_ch'])-np.array(data_file['ch_ci'])), (np.array(data_file['mean_ch'])+np.array(data_file['ch_ci'])), color='red', alpha=.1)
axs[0, 0].plot(data_file['x_axis_values'], data_file['mean_res'], color = "blue", label='Resistors')
axs[0, 0].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)
axs[0, 0].set_title(graph1_title, fontsize=plot_label_size)

# Plot lines indicating sexual cycles
if data_file["parameters"]["i_macrocyst"][0] != 0:
    for i in data_file["parameters"]["i_macrocyst"]:
        axs[0, 0].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)
else:
    for i in data_file["sex_cycle_list"]:
        axs[0, 0].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)

# Get next file from user
filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
with open(filepath, 'r') as file:
    data_file = json.load(file)

#Plot graph 2
axs[0, 1].plot(data_file['x_axis_values'], data_file['mean_ch'], color = "red")
axs[0, 1].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_ch'])-np.array(data_file['ch_ci'])), (np.array(data_file['mean_ch'])+np.array(data_file['ch_ci'])), color='red', alpha=.1)
axs[0, 1].plot(data_file['x_axis_values'], data_file['mean_res'], color = "blue")
axs[0, 1].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)
axs[0, 1].set_title(graph2_title, fontsize=plot_label_size)

# Add the legend to the far right
axs[0, 1].legend(handles=[cheaters_patch, resistors_patch], loc="upper right")

# Plot lines indicating sexual cycles
if data_file["parameters"]["i_macrocyst"][0] != 0:
    for i in data_file["parameters"]["i_macrocyst"]:
        axs[0, 1].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)
else:
    for i in data_file["sex_cycle_list"]:
        axs[0, 1].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)

# Get next file from user
filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
with open(filepath, 'r') as file:
    data_file = json.load(file)

#Plot graph 3
axs[1, 0].plot(data_file['x_axis_values'], data_file['mean_ch'], color = "red")
axs[1, 0].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_ch'])-np.array(data_file['ch_ci'])), (np.array(data_file['mean_ch'])+np.array(data_file['ch_ci'])), color='red', alpha=.1)
axs[1, 0].plot(data_file['x_axis_values'], data_file['mean_res'], color = "blue")
axs[1, 0].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)
axs[1, 0].set_title(graph3_title, fontsize=plot_label_size)

# Plot lines indicating sexual cycles
if data_file["parameters"]["i_macrocyst"][0] != 0:
    for i in data_file["parameters"]["i_macrocyst"]:
        axs[1, 0].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)
else:
    for i in data_file["sex_cycle_list"]:
        axs[1, 0].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)

# Get next file from user
filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
with open(filepath, 'r') as file:
    data_file = json.load(file)

# Plot graph 4
axs[1, 1].plot(data_file['x_axis_values'], data_file['mean_ch'], color = "red")
axs[1, 1].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_ch'])-np.array(data_file['ch_ci'])), (np.array(data_file['mean_ch'])+np.array(data_file['ch_ci'])), color='red', alpha=.1)
axs[1, 1].plot(data_file['x_axis_values'], data_file['mean_res'], color = "blue")
axs[1, 1].fill_between(data_file['x_axis_values'], (np.array(data_file['mean_res'])-np.array(data_file['res_ci'])), (np.array(data_file['mean_res'])+np.array(data_file['res_ci'])), color='blue', alpha=.1)
axs[1, 1].set_title(graph4_title, fontsize=plot_label_size)

# Plot lines indicating sexual cycles
if data_file["parameters"]["i_macrocyst"][0] != 0:
    for i in data_file["parameters"]["i_macrocyst"]:
        axs[1, 1].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)
else:
    for i in data_file["sex_cycle_list"]:
        axs[1, 1].axvline(x = i, color = "b", linestyle = "dashed", alpha = 0.05)

# Hide x labels and tick labels for top plots and y ticks for right plots.
for ax in axs.flat:
    ax.set_ylim([0, 1])

# Adding a single x-axis label and y-axis label
fig.text(0.5, 0.04, 'Developmental Cycles', ha='center', va='center', fontsize=titles_size)
fig.text(0.06, 0.5, 'Proportion of possible alleles', ha='center', va='center', rotation='vertical', fontsize=titles_size)

plt.subplots_adjust(hspace=0.3)
fig.suptitle(full_title, fontsize=titles_size)

plt.show()