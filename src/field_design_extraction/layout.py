"""Experimental design: turn the block ranges of a field map into one row per plot."""

import re

import pandas as pd

from .workbook import range_cells, range_inside, read_cells


# --- which map cells count as plots (a layout or a block can override any key)
DEFAULT_UNIT_RULES = {
    # kinds of value a plot cell may hold (see workbook.classify_value)
    "value_types": ["numeric", "numeric_text", "alphanumeric"],
    # True: only merged cells; False: only single cells; None: both
    "merged": None,
    # True: only the top-left cell of a merged range; None: any
    "anchor": None,
    # True: empty cells are plots too (e.g. every tree of an orchard map)
    "include_empty": False,
    # plot_number from the cell "value", or the cell "coordinate" (e.g. 'E18')
    "unit_id": "value",
}

DESIGN_COLUMNS = [
    "plot_key", "block_id", "block_label", "plot_number", "row", "column",
]


def normalize_plot_number(value):
    """Plot number as text: 503714, 503714.0 and '503714.0' all become '503714'."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    if isinstance(value, int):
        return str(value)

    text = str(value).strip()

    if not text:
        return None

    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]

    return text


def make_plot_key(block_id, plot_number, row, column):
    """Unique plot identifier: block, plot number and map position (row, column)."""
    return f"{block_id}:{plot_number}:{row}:{column}"


def _unit_mask(cells, rules):
    """Cells that satisfy the plot-cell rules."""
    if rules.get("include_empty"):
        mask = pd.Series(True, index=cells.index)
    else:
        mask = cells["value"].notna()

    if rules.get("value_types") is not None:
        allowed = list(rules["value_types"]) + (["empty"] if rules.get("include_empty") else [])
        mask &= cells["value_type"].isin(allowed)

    if rules.get("merged") is True:
        mask &= cells["is_merged"]
    elif rules.get("merged") is False:
        mask &= ~cells["is_merged"]

    if rules.get("anchor") is True:
        mask &= cells["is_anchor"]
    elif rules.get("anchor") is False:
        mask &= ~cells["is_anchor"]

    return mask


def build_design(layout_id, layout, cells=None):
    """Design table of one layout (field map), one row per plot.

    layout: dict with workbook, sheet, region, blocks and optional unit_rules
            (see the README for every key).
    cells:  output of read_cells, when already read.
    """
    if cells is None:
        cells = read_cells(layout["workbook"], layout["sheet"], layout.get("region"))

    region = layout.get("region")
    layout_rules = {**DEFAULT_UNIT_RULES, **layout.get("unit_rules", {})}
    positions = pd.Series(list(zip(cells["row"], cells["column"])), index=cells.index)

    parts = []
    attribute_columns = []

    for block in layout["blocks"]:
        block_id = block["block_id"]
        rules = {**layout_rules, **block.get("unit_rules", {})}

        inside = set()

        for block_region in block["regions"]:
            if region is not None and not range_inside(block_region, region):
                print(
                    f"WARNING: {layout_id} / {block_id}: range {block_region} "
                    f"extends beyond the layout region {region}; "
                    f"cells outside it are ignored"
                )
            inside |= range_cells(block_region)

        units = cells.loc[
            positions.isin(inside) & _unit_mask(cells, rules),
            ["row", "column", "value", "coordinate"],
        ].copy()

        if units.empty:
            print(f"WARNING: {layout_id} / {block_id}: no plot cells found")
            continue

        if rules.get("unit_id") == "coordinate":
            units["value"] = units["coordinate"]

        units["block_id"] = block_id
        units["block_label"] = block.get("label", block_id)

        # --- block-level attributes (e.g. treatment) become columns
        for name, value in block.get("attributes", {}).items():
            units[name] = value
            if name not in attribute_columns:
                attribute_columns.append(name)

        parts.append(units)

    if not parts:
        raise ValueError(f"{layout_id}: no plot cells found in any block")

    units = pd.concat(parts, ignore_index=True)

    # --- a plot cell must belong to only one block
    blocks_per_cell = units.groupby(["row", "column"])["block_id"].unique()
    overlaps = blocks_per_cell[blocks_per_cell.apply(len) > 1]

    if not overlaps.empty:
        cell_list = "\n".join(
            f"  row {row}, column {column}: {list(blocks)}"
            for (row, column), blocks in overlaps.head(20).items()
        )
        raise ValueError(
            f"\n{layout_id}: {len(overlaps)} plot cells belong to more than one block.\n"
            f"Check the block 'regions'.\n\n{cell_list}"
        )

    units["plot_number"] = units["value"].apply(normalize_plot_number)
    units["plot_key"] = [
        make_plot_key(*key)
        for key in zip(units["block_id"], units["plot_number"], units["row"], units["column"])
    ]

    return units[DESIGN_COLUMNS + attribute_columns].reset_index(drop=True)


def report_design(layout_id, design):
    """Print plots per block and plot numbers that occur more than once in a block."""
    print()
    print("=" * 80)
    print(f"DESIGN — {layout_id}: {len(design)} plots")
    print("=" * 80)
    print(design.groupby("block_id", sort=False).size().to_string())

    repeated = design[design.duplicated(["block_id", "plot_number"], keep=False)]

    if not repeated.empty:
        print()
        print(
            "NOTE: plot numbers that occur more than once in the same block "
            "(ratings for them cannot be linked to a single plot):"
        )
        print(
            repeated[["block_id", "plot_number", "row", "column"]]
            .sort_values(["block_id", "plot_number"])
            .to_string(index=False)
        )
