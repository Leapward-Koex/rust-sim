"""Legacy graph presentation, independent of the Tk event loop."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Patch


def sex_markers(result: dict) -> list:
    explicit = result["parameters"]["i_macrocyst"]
    if not explicit:
        return []
    # Preserve legacy string behavior, including iteration over its characters.
    return list(explicit) if explicit[0] != 0 else result["sex_cycle_list"]


def make_figure(result: dict) -> Figure:
    figure = Figure(figsize=(12, 8))
    axes = figure.subplots(2)
    x = result["x_axis_values"]
    groups = (
        (("mean_ch", "ch_ci", "red", "Cheater alleles"),
         ("mean_res", "res_ci", "blue", "Resistor alleles"),
         ("mean_wild", "wild_ci", "black", "Wild-type alleles")),
        (("mean_mt1", "mt1_ci", "red", "Type 1"),
         ("mean_mt2", "mt2_ci", "blue", "Type 2"),
         ("mean_mt3", "mt3_ci", "green", "Type 3")),
    )
    for axis, series in zip(axes, groups):
        handles = []
        for mean_key, ci_key, color, label in series:
            mean = np.asarray(result[mean_key], dtype=float)
            halfwidth = np.asarray(result[ci_key], dtype=float)
            axis.plot(x, mean, color=color)
            axis.fill_between(x, mean - halfwidth, mean + halfwidth, color=color, alpha=0.1)
            handles.append(Patch(color=color, label=label))
        axis.set_ylabel("Ratio")
        axis.set_ylim([0, 1])
        axis.set_xlabel("Development cycles")
        axis.grid()
        axis.legend(handles=handles)
        for cycle in sex_markers(result):
            axis.axvline(x=cycle, color="b", linestyle="dashed", alpha=0.05)
    axes[0].set_title("Allele frequency over time")
    figure.tight_layout()
    return figure
