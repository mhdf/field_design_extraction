"""Example 1 — plots in merged cells, ratings table with a block column, two dates.

    python examples/create_example_workbooks.py     (once: creates examples/data)
    python examples/example_1_merged_plots.py

The workbook stands in for a field file typed by hand: a field map (sheet field_map)
and one ratings sheet per assessment date (date_1, date_2). The settings below
describe how THIS workbook is organised; for another workbook, the same keys get
the sheets, cells and columns of that file.

Outputs: examples/output/example_1/ (CSV tables and figures/).
"""

from pathlib import Path

import field_design_extraction as fde

HERE = Path(__file__).resolve().parent
WORKBOOK = HERE / "data" / "example_1_merged_plots.xlsx"
FIGURES = HERE / "output" / "example_1" / "figures"


# =============================================
# 1. LOOK AT THE INPUT WORKBOOK
# =============================================

# --- pictures of the sheets as they look in Excel
fde.save_figure(
    fde.plot_sheet(WORKBOOK, "field_map", "A1:Z24", title="Input workbook — sheet field_map"),
    FIGURES / "input_field_map.png", dpi=150,
)
fde.save_figure(
    fde.plot_sheet(WORKBOOK, "date_1", "A1:D24", title="Input workbook — sheet date_1 (first rows)"),
    FIGURES / "input_ratings_date_1.png", dpi=150,
)


# =============================================
# 2. DESCRIBE THE WORKBOOK IN THE SETTINGS
# =============================================

layouts = {
    "example_1_design": {
        # --- the field map: sheet field_map, plots and block labels in B3:Y23
        "workbook": WORKBOOK,
        "sheet": "field_map",
        "region": "B3:Y23",
        "output_folder": HERE / "output" / "example_1",

        # --- each plot number sits in the top cell of a 2-cell merged range
        "unit_rules": {"merged": True, "anchor": True},

        # --- where each block's plots are (the coloured areas of the map)
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
            "plot_size": (1.3, 1.8),
            "label_rotation": 90,
        },
    },
}

rating_sources = {
    "example_1_score": {
        "layout_id": "example_1_design",
        "disease": "leaf_spot",
        "workbook": WORKBOOK,

        # --- ratings sheets: column names on row 1 (the default); the plot number,
        #     its block and the values to keep are in these columns
        "plot_column": "plot",
        "block_column": "block",
        "value_columns": {"score": "score", "evaluator": "evaluator"},

        # --- one sheet per assessment; "date": a real date (2025-08-15) or a label, as here
        "assessments": {
            "first": {"sheet": "date_1", "date": "Date 1"},
            "second": {"sheet": "date_2", "date": "Date 2"},
        },

        # --- blocks are written "BLOCK A" in the ratings, "BLOCK_A" in the layout
        "block_mapping": {"BLOCK A": "BLOCK_A", "BLOCK B": "BLOCK_B", "BLOCK C": "BLOCK_C", "BLOCK D": "BLOCK_D"},

        "figure": {
            "value": "score",
            "title": "Example 1 — disease score per date",
            "legend_title": "Disease score [0-100]",
            "map_title": "Example 1 — disease score, {date}",
            "coverage_title": "Example 1 — plots assessed, {date}",
            "bins": list(range(0, 101, 10)),
            # --- distribution chart: narrower, with larger text
            "width": 8.5,
            "font_size": 12,
        },
    },
}


# =============================================
# 3. RUN: TABLES AND FIGURES
# =============================================

designs = fde.build_designs(layouts)
ratings = fde.build_ratings(rating_sources, designs)
fde.export(layouts, rating_sources, designs, ratings)
fde.save_figures(layouts, rating_sources, designs, ratings, which=["design", "distribution", "maps", "coverage"])
