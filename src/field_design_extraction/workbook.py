"""Read worksheet cells with their value, merged range and fill color."""

import datetime as dt
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries


# --- each workbook is opened once per session (per file version):
#     one copy with formulas, one with the values Excel saved for them
_WORKBOOKS = {}


def open_workbook(path):
    """Return (workbook with formulas, workbook with saved values)."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    key = (str(path.resolve()), path.stat().st_mtime)

    if key not in _WORKBOOKS:
        _WORKBOOKS[key] = (
            load_workbook(path, data_only=False),
            load_workbook(path, data_only=True),
        )

    return _WORKBOOKS[key]


def get_sheet(path, sheet):
    """Return (worksheet with formulas, worksheet with saved values)."""
    wb, wb_values = open_workbook(path)

    if sheet not in wb.sheetnames:
        raise ValueError(
            f"Worksheet {sheet!r} not found in {Path(path).name}. "
            f"Available sheets: {wb.sheetnames}"
        )

    return wb[sheet], wb_values[sheet]


# =============================================
# EXCEL RANGES
# =============================================

def parse_range(text):
    """'B2:AR11' or 'I4' -> (min_row, max_row, min_column, max_column)."""
    min_col, min_row, max_col, max_row = range_boundaries(text)
    return min_row, max_row, min_col, max_col


def range_cells(text):
    """All (row, column) positions inside an Excel range."""
    min_row, max_row, min_col, max_col = parse_range(text)
    return {
        (row, column)
        for row in range(min_row, max_row + 1)
        for column in range(min_col, max_col + 1)
    }


def range_inside(inner, outer):
    """True when the Excel range `inner` lies completely inside `outer`."""
    r1, r2, c1, c2 = parse_range(inner)
    o1, o2, p1, p2 = parse_range(outer)
    return o1 <= r1 and r2 <= o2 and p1 <= c1 and c2 <= p2


# =============================================
# CELL PROPERTIES
# =============================================

def color_key(cell):
    """Fill color as short text ('FFFF0000', 'theme4+0.60', 'indexed64'); None when not filled."""
    fill = cell.fill

    if fill is None or not fill.fill_type:
        return None

    color = fill.fgColor

    if color.type == "rgb":
        key = str(color.rgb)
    elif color.type == "theme":
        key = f"theme{color.theme}"
    elif color.type == "indexed":
        key = f"indexed{color.indexed}"
    else:
        key = str(color.type)

    if color.tint:
        key += f"{color.tint:+.2f}"

    return key


def classify_value(value):
    """Kind of cell value: empty, numeric, numeric_text, decimal_text, date, alphanumeric or text."""
    if value is None:
        return "empty"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, (int, float)):
        return "numeric"

    if isinstance(value, (dt.date, dt.datetime, dt.time)):
        return "date"

    text = str(value).strip()

    if not text:
        return "empty"

    compact = text.replace(" ", "")

    if re.fullmatch(r"[+-]?\d+", compact):
        return "numeric_text"

    if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", compact):
        return "decimal_text"

    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", text):
        return "date"

    if re.search(r"[A-Za-z]", text) and re.search(r"\d", text):
        return "alphanumeric"

    return "text"


# =============================================
# WORKSHEET → CELL TABLE
# =============================================

CELL_COLUMNS = [
    "coordinate", "row", "column", "value", "formula", "value_type",
    "is_merged", "is_anchor", "merged_range", "fill",
]


def read_cells(path, sheet, region=None):
    """One row per cell of `region` (Excel range; whole sheet when None).

    Formula cells hold the value Excel saved, with the formula kept in `formula`.
    """
    ws, ws_values = get_sheet(path, sheet)

    if region is None:
        min_row, max_row, min_col, max_col = 1, ws.max_row, 1, ws.max_column
    else:
        min_row, max_row, min_col, max_col = parse_range(region)

    # --- merged-range membership of every cell
    merged = {}

    for merged_range in ws.merged_cells.ranges:
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for column in range(merged_range.min_col, merged_range.max_col + 1):
                merged[(row, column)] = merged_range

    records = []

    for row_cells in ws.iter_rows(
        min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col,
    ):
        for cell in row_cells:
            value = cell.value
            formula = None

            # --- formulas: the value Excel saved, not the formula text
            if cell.data_type == "f":
                formula = str(value)
                value = ws_values.cell(cell.row, cell.column).value

            merged_range = merged.get((cell.row, cell.column))

            records.append({
                "coordinate": cell.coordinate,
                "row": cell.row,
                "column": cell.column,
                "value": value,
                "formula": formula,
                "value_type": classify_value(value),
                "is_merged": merged_range is not None,
                "is_anchor": (
                    merged_range is not None
                    and cell.row == merged_range.min_row
                    and cell.column == merged_range.min_col
                ),
                "merged_range": None if merged_range is None else str(merged_range),
                "fill": color_key(cell),
            })

    cells = pd.DataFrame(records, columns=CELL_COLUMNS)

    # --- formulas without a saved value (workbook not saved by Excel)
    no_value = cells[cells["formula"].notna() & cells["value"].isna()]

    if not no_value.empty:
        print(
            f"WARNING: {len(no_value)} formula cells in {sheet!r} have no saved value "
            f"(open and save the workbook in Excel): "
            f"{no_value['coordinate'].head(10).tolist()}"
        )

    return cells
