"""Example 2 — one cell per plot, one ratings sheet per trial (header on row 7).

    python examples/create_example_workbooks.py     (once: creates examples/data)
    python examples/example_2_one_sheet_per_trial.py

Outputs: examples/output/example_2/ (CSV tables and figures/).
"""

from pathlib import Path

import field_design_extraction as fde

HERE = Path(__file__).resolve().parent
WORKBOOK = HERE / "data" / "example_2_one_sheet_per_trial.xlsx"

trials = {"TRIAL_1": "B4:F11", "TRIAL_2": "G4:J11", "TRIAL_3": "K4:T11", "TRIAL_4": "U4:Z11"}

layouts = {
    "example_2_design": {
        "workbook": WORKBOOK,
        "sheet": "field_map",
        "region": "B3:Z11",
        "output_folder": HERE / "output" / "example_2",

        # --- one plot number per (unmerged) cell
        "unit_rules": {"value_types": ["numeric"], "merged": False},

        "blocks": [
            {"block_id": trial, "label": trial.replace("_", " ").title(), "regions": [region]}
            for trial, region in trials.items()
        ],

        "figure": {
            "title": "Example 2 — experimental design",
            "names": {trial: trial.replace("_", " ").title() for trial in trials},
            "legend_title": "Trials",
            "plot_size": (1.0, 1.0),
            "label_rotation": 0,
        },
    },
}

rating_sources = {
    "example_2_severity": {
        "layout_id": "example_2_design",
        "disease": "leaf_blotch",
        "workbook": WORKBOOK,

        # --- rows 1-5 hold date, growth stage and assessed area
        "header_row": 7,
        "plot_column": "Plot",

        # --- one sheet per trial: the block comes from each assessment
        "block_column": None,
        "value_columns": {"Severity (%)": "severity"},
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

designs = fde.build_designs(layouts)
ratings = fde.build_ratings(rating_sources, designs)
fde.export(layouts, rating_sources, designs, ratings)
fde.save_figures(layouts, rating_sources, designs, ratings, which=["design", "distribution", "maps"])
