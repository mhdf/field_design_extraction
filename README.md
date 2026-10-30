# Field trial maps and disease assessments: from spreadsheets to analysis-ready tables

<div align="justify">

Field experiments are often recorded in spreadsheets drawn for people, not for analysis: a field map
(croqui) where each cell or merged range is a plot, coloured by block, and disease ratings typed in separate
sheets, one per date or per trial, or marked directly on copies of the map. This Python package
(`field_design_extraction`) reads those workbooks as they are and turns them into two kinds of tables:

- **design** — one row per plot: `plot_key`, `block_id`, `block_label`, `plot_number`, `row`, `column`
  (`row`/`column` are the plot's cell on the map);
- **ratings** — one file per assessment date, only the rated plots: `plot_key`, `block_id`, `plot_number`,
  `date`, `disease` and the value columns you choose (e.g. `score`).

The two join on `plot_key` (`block:plot_number:row:column`; the position keeps it unique when a plot number
occurs twice). Along the way it checks the data (plots claimed by two blocks, ratings that match no plot or
more than one, plots rated twice) and can draw the field layout, the plots assessed and the ratings of each
date, and the distribution of scores over time.

## Install

In the Python environment that will run your scripts (Python 3.10 or newer; matplotlib for the figures):

```
git clone https://github.com/mhdf/field_design_extraction.git
pip install -e field_design_extraction
```

`-e` (editable) makes changes to the package code take effect without reinstalling.

## Quick start

A workbook `trial.xlsx` with two sheets:

- `map` — the field map: plot numbers in cells B3:K8, block 1 in columns B–F, block 2 in columns G–K;
- `ratings` — one row per rated plot, with the columns `plot`, `block` (`1` or `2`) and `score`.

```python
from pathlib import Path

import field_design_extraction as fde

layouts = {
    "trial": {
        "workbook": Path("trial.xlsx"),
        "sheet": "map",
        "region": "B3:K8",
        "output_folder": Path("consolidated"),
        "blocks": [
            {"block_id": "B1", "label": "Block 1", "regions": ["B3:F8"]},
            {"block_id": "B2", "label": "Block 2", "regions": ["G3:K8"]},
        ],
    },
}

rating_sources = {
    "trial_score": {
        "layout_id": "trial",
        "disease": "leaf_spot",
        "workbook": Path("trial.xlsx"),
        "plot_column": "plot",
        "block_column": "block",
        "block_mapping": {"1": "B1", "2": "B2"},
        "value_columns": {"score": "score"},
        "assessments": {"first": {"sheet": "ratings", "date": "2025-09-01"}},
    },
}

designs, ratings = fde.run(layouts, rating_sources)          # tables in consolidated/
fde.save_figures(layouts, rating_sources, designs, ratings)  # optional: consolidated/figures/
```

This writes `consolidated/trial.csv` (one row per plot) and `consolidated/trial_score_20250901.csv` (the
ratings, linked to the plots), and prints what it found. The sections below explain each setting; the
[examples](#examples) show complete scripts with figures.

## Use

A project script holds two settings dictionaries and runs the steps:

```python
import field_design_extraction as fde

designs = fde.build_designs(layouts)                    # map → design tables
ratings = fde.build_ratings(rating_sources, designs)    # ratings linked to plots
fde.export(layouts, rating_sources, designs, ratings)   # CSV files
```

Each step prints what it found: plots per block, plot numbers repeated within a block, and per date how many
ratings were linked and why the others were not.

## Examples

Two synthetic examples (made-up plots and scores, 0–100, with spatial patches) in `examples/`:

| example | field map | ratings |
|---|---|---|
| `example_1_merged_plots.py` | 4 blocks, 210 plots, each plot number in a 2-cell merged range | one sheet per date (2 dates), a block column, part of the plots rated |
| `example_2_one_sheet_per_trial.py` | 4 trials side by side, 200 plots numbered from 1 in each trial | one sheet per trial, column names on row 7, MIN/MAX rows below the table |

```
python examples/create_example_workbooks.py        # writes examples/data/*.xlsx (fixed random seed)
python examples/example_1_merged_plots.py          # writes examples/output/example_1/
python examples/example_2_one_sheet_per_trial.py   # writes examples/output/example_2/
```

### Example 1

Experimental design — four blocks of plots:

<img src="docs/images/example_1_design.png" width="49%">

Plots assessed on each date (black):

<img src="docs/images/example_1_coverage_date_1.png" width="49%"> <img src="docs/images/example_1_coverage_date_2.png" width="49%">

Disease score of each plot on each date (grey: not assessed on that date):

<img src="docs/images/example_1_map_date_1.png" width="49%"> <img src="docs/images/example_1_map_date_2.png" width="49%">

Share of the assessed plots in each score class, per date (numbers inside the bars: plots):

<p align="center"><img src="docs/images/example_1_distribution.png" width="75%"></p>

### Example 2

Experimental design — four trials, plots numbered from 1 in each trial:

<img src="docs/images/example_2_design.png" width="49%">

Disease severity of each plot (one assessment date):

<img src="docs/images/example_2_map.png" width="49%">

Share of the plots in each severity class (numbers inside the bar: plots):

<p align="center"><img src="docs/images/example_2_distribution.png" width="75%"></p>

## Settings

### layouts — one entry per field map

| key | meaning |
|---|---|
| `workbook`, `sheet` | the map |
| `region` | Excel range holding the map, e.g. `"B2:AR11"` |
| `output_folder` | where the CSV files go (e.g. `dados/avaliacao_visual/consolidated`) |
| `blocks` | list of `{block_id, label, regions}`; `regions` are the Excel ranges of the block's plots |
| `unit_rules` | which cells count as plots (optional, also per block): `value_types`, `merged` (True/False/None), `anchor` (True: top-left cell of a merged range) |

A cell inside two blocks stops the run with the list of cells. Formula cells are read through the value Excel
saved.

### rating_sources — one entry per ratings workbook

| key | meaning |
|---|---|
| `layout_id` | the layout the ratings belong to |
| `disease`, `workbook` | |
| `assessments` | `{name: {sheet, date}}`; add `block` when each sheet holds one block. `date`: a date (`2025-09-01`, `01/09/2025`) or a label such as `"Date 1"` (file names then use `date_1`) |
| `header_row` | Excel row with the column names (default 1) |
| `plot_column` | column with the plot number |
| `block_column` | column with the block label; `None` when each sheet holds one block |
| `block_mapping` | block label in the ratings → `block_id` (optional when they are equal) |
| `value_columns` | columns to keep: `{name in the sheet: name in the output}` |

Rows without a plot number (e.g. MIN/MAX rows) are dropped. Ratings that cannot be linked go to
`<source>_<date>_unlinked.csv` with the reason (`link_status`).

### Ratings marked on the map (`"kind": "map"`)

For maps where each date is a copy of the field map and the rating is written into the plot cell (e.g. an
orchard where every cell is a tree). The design then takes every cell as a plot: `unit_rules`
`{"value_types": None, "include_empty": True, "unit_id": "coordinate"}` (plot_number = cell, e.g. `E18`); block
`attributes` (e.g. `{"treatment": "A"}`) become design columns.

| key | meaning |
|---|---|
| `assessments` | `{name: {sheet, date}}`, one sheet per date |
| `status_rules` | ordered list; the first rule whose conditions all hold gives the status. Conditions: `text` (regular expression, case-insensitive), `fills` (list of fill colors as `read_cells` shows them), `empty` (True/False) |
| `default_status` | status of empty cells no rule covers (default `healthy`); non-empty cells no rule covers get `unknown` and are listed |
| `ignore_text` | text read as empty (e.g. plot labels written in tree cells) |
| `flags` | extra True/False columns from the fill, e.g. `{"new_case": ["FFFFFF00"]}` |

Output: one file per date with every plot: `status`, the flags, and the raw cell `value` and `fill`.

### Figures (optional)

```python
fde.save_figures(layouts, rating_sources, designs, ratings, which=["design", "distribution", "maps"])
```

| figure | file | what it shows |
|---|---|---|
| `design` | `<layout_id>.png` | schematic of the plots, colored by block (or any design column, e.g. treatment) |
| `distribution` | `<source>_distribution.png` | share of plots per score class or status, one bar per date; the segments show the number of plots (`segment_labels`: `"count"`, `"percent"` or `None`) |
| `maps` | `<source>_<date>_map.png` | the schematic colored by the rating of that date (grey: not rated) |
| `coverage` | `<source>_<date>_coverage.png` | ratings tables: which plots were assessed on that date |
| `incidence` | `<source>_incidence.png` | map ratings: share of plots with a status per date, one line per group (e.g. treatment) |

Files go to `<output_folder>/figures` (or the layout's `figure_folder`). Options: a `"figure"` entry in a layout
(`title`, `color_by`, `colors`, `names`, `legend_title`, `plot_size`, `rotate`, `show_labels`, `label_rotation`,
`gaps`, `gap_rule`, `block_outlines`, `hatch_shared_with` + `hatch_label`) and in a ratings source (`value`,
`title`, `colors`, `legend_title`, `xlabel`, `map_title`, `coverage_title`, `bins`, `segment_labels`,
`group_others`, `incidence`). Scores with many
values (e.g. % severity) are grouped into classes (`bins`, default 10 units); half scores (1.5, 2.5…) are hatched.

`group_others` (ratings source), e.g. `{"keep": ["healthy", "hlb"], "label": "others", "color": "#8C8C8C"}`:
in the figures, every other class becomes one class whose name lists what it contains, e.g.
`others (gummosis, dead, missing)`, or your own text with `"description": "dead, other diseases, etc."`;
the CSV files keep the detailed values.

Proportions: `plot_size` = (width, height) of each plot on the schematic, in any unit (only the ratio matters).
Make plots wider than tall when rows are farther apart than plots within a row, e.g. the real spacing
`(6.5, 2.5)` in metres; `rotate` turns the whole map by 90°.

Size: the design, coverage and map figures of a layout all have the same size and plot shapes (the map is
drawn at a fixed scale, with fixed space for the title and the legend — `legend_height`, in inches); the
distribution chart takes the same width, so the figures line up side by side.

Gaps between blocks: `gaps` = (horizontal, vertical) size; `gap_rule` `"any"` (default) puts a gap wherever
blocks meet (at least 2 neighbouring plots), but the gap crosses the whole figure and may cut other blocks;
`"disjoint"` only separates rows/columns that share no block. `label_rotation`: 0 (horizontal) or 90 (vertical).

### Checking the block ranges

`fde.read_cells(workbook, sheet, region)` returns every cell with value, merged range and fill color;
`fde.color_summary(cells)` groups them by color; `fde.plot_cells(cells, design)` draws the map with the plots of
each block marked.

## Tests

```
python -m unittest discover -s tests -t tests
```

GitHub runs the same tests (Python 3.10 and 3.12, Linux) on every change to `main` and on every pull request.

## License

MIT — see [LICENSE](LICENSE).

</div>
