"""Example 2 — one cell per plot, one ratings sheet per trial (column names on row 7).

    python examples/create_example_workbooks.py     (once: creates examples/data)
    python examples/example_2_one_sheet_per_trial.py

The workbook stands in for a field file typed by hand: a field map with four trials
side by side (sheet field_map) and one ratings sheet per trial (Trial_1 ... Trial_4),
each with a few lines of notes above the table. The settings below describe how THIS
workbook is organised; for another workbook, the same keys get the sheets, cells and
columns of that file.

Outputs: examples/output/example_2/ (CSV tables and figures/).
"""

from pathlib import Path

import field_design_extraction as fde

HERE = Path(__file__).resolve().parent
WORKBOOK = HERE / "data" / "example_2_one_sheet_per_trial.xlsx"
FIGURES = HERE / "output" / "example_2" / "figures"


# =============================================
# 1. LOOK AT THE INPUT WORKBOOK
# =============================================

# --- pictures of the sheets as they look in Excel
fde.save_figure(
    fde.plot_sheet(WORKBOOK, "field_map", "A1:AA11", title="Input workbook — sheet field_map"),
    FIGURES / "input_field_map.png", dpi=150,
)
fde.save_figure(
    fde.plot_sheet(WORKBOOK, "Trial_1", "A1:C14", title="Input workbook — sheet Trial_1 (first rows)"),
    FIGURES / "input_ratings_trial_1.png", dpi=150,
)


# =============================================
# 2. DESCRIBE THE WORKBOOK IN THE SETTINGS
# =============================================

# --- where each trial's plots are on the map (the coloured areas)
trials = {"TRIAL_1": "B4:F11", "TRIAL_2": "G4:J11", "TRIAL_3": "K4:T11", "TRIAL_4": "U4:Z11"}

layouts = {
    "example_2_design": {
        # --- the field map: sheet field_map, trial names and plots in B3:Z11
        "workbook": WORKBOOK,
        "sheet": "field_map",
        "region": "B3:Z11",
        "output_folder": HERE / "output" / "example_2",

        # --- one plot number per (unmerged) cell
        "unit_rules": {"value_types": ["numeric"], "merged": False},

        # --- notes on row 2 of the map, each typed to the right of its label:
        #     they become columns of the design table
        "sheet_values": {
            "site": "Site:",
            "cultivar": "Cultivar:",
        },

        "blocks": [
            {"block_id": trial, "label": trial.replace("_", " ").title(), "regions": [region]}
            for trial, region in trials.items()
        ],

        "figure": {
            "title": "Example 2 — experimental design",
            "names": {trial: trial.replace("_", " ").title() for trial in trials},
            "legend_title": "Trials",
            "plot_size": (1.3, 1.8),
            "label_rotation": 90,
        },
    },
}

rating_sources = {
    "example_2_severity": {
        "layout_id": "example_2_design",
        "disease": "leaf_blotch",
        "workbook": WORKBOOK,

        # --- the column names are on row 7; of the table, keep Plot and Severity (%)
        "header_row": 7,
        "plot_column": "Plot",
        "value_columns": {"Severity (%)": "severity"},

        # --- notes above the table (rows 1-3), label in column A, value to its right:
        #     read on every trial sheet, they become columns of the ratings
        "sheet_values": {
            "growth_stage": "Growth stage:",
            "assessed_area": "Assessed area:",
        },

        # --- no block column: each sheet holds one trial, named in "block"
        "block_column": None,
        "assessments": {
            trial: {"sheet": trial.title(), "date": "Date 1", "block": trial}
            for trial in trials
        },

        "figure": {
            "value": "severity",
            "title": "Example 2 — disease severity",
            "legend_title": "Severity [%]",
            "map_title": "Example 2 — disease severity, {date}",
            "bins": list(range(0, 101, 10)),
        },
    },
}


# =============================================
# 3. RUN: TABLES AND FIGURES
# =============================================

designs = fde.build_designs(layouts)
ratings = fde.build_ratings(rating_sources, designs)
fde.export(layouts, rating_sources, designs, ratings)
fde.save_figures(layouts, rating_sources, designs, ratings, which=["design", "distribution", "maps"])
