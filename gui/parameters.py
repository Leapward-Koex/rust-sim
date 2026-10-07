"""Parameter editing without importing Tk or changing simulation rules."""

from __future__ import annotations

import copy
import ctypes
import json
import os
from pathlib import Path


DEFAULTS = {
    "n_runs": 10, "n_dev": 500, "i_macrocyst": [0], "sex_cycle_interval": 0,
    "vg": 10, "n": 10000, "sl": 1000, "sp": 0.8, "m_ch": 0.001,
    "m_re": 0.001, "c_ch": 0.01, "c_res": 0.01, "ch_germ": 0,
    "c_ch_res": 0, "ch_start": 0, "res_start": 0, "ch_res_dist": 1,
    "ch_eff_rc": 0, "res_eff_rc": 0, "mc_count": 100,
    "mc_germ_count": 100, "recomb_chance": 1, "mt1_start": 0.5,
    "mt2_start": 0.5, "mt3_start": 0, "output_filepath": "default_out",
    "resistance_type": 1, "gene_pairs": 3, "discrete_res": 1,
    "ch_self_cheat": 0, "confidence_interval": 0.95,
}

TOOLTIPS = {
    "n_runs": "Number of independent simulation repeats.",
    "n_dev": "Development cycles per repeat. Each contains optional sex, vegetative growth, and development.",
    "i_macrocyst": "Explicit sex cycles, e.g. [10, 20] or 10, 20. [0] enables the interval schedule. [] has no explicit events.",
    "sex_cycle_interval": "Interval schedule, used only when nonzero and the first explicit-list item is 0. Otherwise the explicit list controls sex.",
    "vg": "Vegetative growth generations per development cycle. Germination also occurs when this is zero.",
    "n": "Configured population size, restored by each vegetative generation.",
    "sl": "Cells per slug. Each development creates floor(n / sl) slugs; leftovers are discarded.",
    "sp": "Spore fraction: cells are initially assigned to prestalk with probability 1 - sp.",
    "m_ch": "Reversible mutation probability for each cheater allele per vegetative generation.",
    "m_re": "Reversible mutation probability for each resistance allele per vegetative generation.",
    "c_ch": "Vegetative cost per raw cheater allele; sexual fitness uses effective cheater alleles.",
    "c_res": "Vegetative cost per raw resistance allele; sexual fitness uses effective resistance alleles.",
    "ch_germ": "Germination penalty for any cell carrying cheater alleles; zero allows germination.",
    "c_ch_res": "Preserved parameter. Currently has no effect on the active simulation.",
    "ch_start": "Initial fraction of cheater cells, applied to all loci of each selected cell.",
    "res_start": "Initial fraction of resistance cells, applied to all loci of each selected cell.",
    "ch_res_dist": "1 selects cheater and resistance cells randomly and independently; 0 uses sequential placement with the original overlap.",
    "ch_eff_rc": "Cheater effectiveness multiplier when both alleles share a locus. Exploitation implements exact 0 and 1 cases only.",
    "res_eff_rc": "Resistance effectiveness multiplier when both alleles share a locus. Exploitation implements exact 0 and 1 cases only.",
    "mc_count": "Number of macrocyst founders selected without replacement per sexual cycle.",
    "mc_germ_count": "Number of cloned offspring produced per macrocyst.",
    "recomb_chance": "Chance of independently choosing parental alleles and mating type during sexual reproduction.",
    "mt1_start": "Initial mating-type-1 weight; initial mating types are sampled using the three weights.",
    "mt2_start": "Initial mating-type-2 weight.",
    "mt3_start": "Initial mating-type-3 weight.",
    "output_filepath": "Output basename. The literal suffix .json is appended, even if already present. Blank disables persistent saving; plots still appear.",
    "resistance_type": "Only passive resistance (1) is implemented. Other values can fail with an empty population.",
    "gene_pairs": "Number of loci per cell.",
    "discrete_res": "1 enables discrete exploitation. Other values retain every cell in each slug.",
    "ch_self_cheat": "Preserved parameter. Currently has no effect on the active simulation.",
    "confidence_interval": "Preserved in results, but the current simulation always calculates 95% confidence half-widths.",
}


class ParameterError(ValueError):
    pass


def validate_parameters(value: object) -> dict:
    if not isinstance(value, dict):
        raise ParameterError("Parameters must be a JSON object.")
    missing = [key for key in DEFAULTS if key not in value]
    if missing:
        raise ParameterError("Missing parameters: " + ", ".join(missing))
    for key in DEFAULTS:
        item = value[key]
        if key == "output_filepath":
            if not isinstance(item, str):
                raise ParameterError("output_filepath must be a string.")
        # Preserve imported JSON values. Only the engine knows whether a phase
        # accesses a field: e.g. null sexual parameters are harmless without sex.
        # Validating every numerical field here would reject valid source runs.
    return copy.deepcopy(value)


def load_parameters(path: Path) -> dict:
    return validate_parameters(json.loads(path.read_text(encoding="utf-8-sig")))


def field_text(key: str, value: object) -> str:
    return value if key == "output_filepath" else json.dumps(value, ensure_ascii=False)


def parameters_from_fields(current: dict, fields: dict[str, str]) -> dict:
    """Parse everything first; callers only replace state after this succeeds."""
    updated = copy.deepcopy(current)
    for key in DEFAULTS:
        text = fields[key].strip() if key != "output_filepath" else fields[key]
        try:
            if key == "output_filepath":
                value = text
            elif key == "i_macrocyst":
                # Keep imported legacy strings verbatim when unchanged. New bare
                # numbers and comma-separated input have the old GUI's list meaning.
                if text == field_text(key, current[key]):
                    value = copy.deepcopy(current[key])
                elif text.startswith(("[", '"')):
                    value = json.loads(text)
                else:
                    value = json.loads("[" + text + "]")
            else:
                value = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise ParameterError(f"{key}: enter valid JSON numbers or a numeric list.") from exc
        updated[key] = value
    return validate_parameters(updated)


def save_parameters(path: Path, parameters: dict) -> None:
    path.write_text(json.dumps(parameters, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def documents_directory() -> Path:
    if os.name == "nt":
        # CSIDL_PERSONAL follows the user's redirected Documents known folder.
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Documents"


def output_base_directory() -> Path:
    return documents_directory() / "Dicty Simulator"


def export_destination(parameters: dict, base: Path) -> Path | None:
    configured = parameters["output_filepath"]
    if not configured:
        return None
    path = Path(configured + ".json")
    return path if path.is_absolute() else base / path
