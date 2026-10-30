"""Example 1 — plots in merged cells, ratings table with a block column, two dates.

    python examples/create_example_workbooks.py     (once: creates examples/data)
    python examples/example_1_merged_plots.py

Outputs: examples/output/example_1/ (CSV tables and figures/).
"""

from pathlib import Path

import field_design_extraction as fde

HERE = Path(__file__).resolve().parent
WORKBOOK = HERE / "data" / "example_1_merged_plots.xlsx"

layouts = {
    "example_1_design": {
        "workbook": WORKBOOK,
        "sheet": "field_map",
        "region": "B3:Y23",
        "output_folder": HERE / "output" / "example_1",

        # --- each plot number sits in the top cell of a 2-cell merged range
        "unit_rules": {"merged": True, "anchor": True},

        "blocks": [
            {"block_id": "BLOCK_A", "label": "Block A", "regions": ["B4:G23"]},
            {"block_id": "BLOCK_B", "label": "Block B", "regions": ["I4:N23"]},
            {"block_id": "BLOCK_C", "label": "Block C", "regions": ["P4:Y11"]},
            {"block_id": "BLOCK_D", "label": "Block D", "regions": ["P14:Y23"]},
        ],

        "figure": {
            "title": "Example 1 — experimental design",
            "names": {"BLOCK_A": "Block A", "BLOCK_B": "Block B", "BLOCK_C": "Block C", "BLOCK_D": "Block D"},
            "colors": {"BLOCK_A": "#F2B134", "BLOCK_B": "#F28E2B", "BLOCK_C": "#43B97F", "BLOCK_D": "#36A9D6"},
            "legend_title": "Blocks",
            "plot_size": (1.0, 1.8),
            "label_rotation": 90,
        },
    },
}

rating_sources = {
    "example_1_score": {
        "layout_id": "example_1_design",
        "disease": "leaf_spot",
        "workbook": WORKBOOK,
        "plot_column": "plot",
        "block_column": "block",
        "value_columns": {"score": "score", "evaluator": "evaluator"},
        "assessments": {
            "first": {"sheet": "20250815", "date": "2025-08-15"},
            "second": {"sheet": "20250905", "date": "2025-09-05"},
        },
        # --- block label in the ratings → block_id of the layout
        "block_mapping": {"BLOCK A": "BLOCK_A", "BLOCK B": "BLOCK_B", "BLOCK C": "BLOCK_C", "BLOCK D": "BLOCK_D"},

        "figure": {
            "value": "score",
            "title": "Example 1 — disease score per date",
            "legend_title": "Disease score [0-100]",
            "map_title": "Example 1 — disease score, {date}",
            "bins": list(range(0, 101, 10)),
        },
    },
}

designs = fde.build_designs(layouts)
ratings = fde.build_ratings(rating_sources, designs)
fde.export(layouts, rating_sources, designs, ratings)
fde.save_figures(layouts, rating_sources, designs, ratings, which=["design", "distribution", "maps", "coverage"])
