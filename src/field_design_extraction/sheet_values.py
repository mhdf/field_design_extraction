"""Single values written on a sheet outside the tables (site, cultivar, planting date, growth stage...).

A field is found either by its cell ("B2") or by the label written next to it:
{"label": "Growth stage:", "direction": "right"} takes the first filled cell to the
right of the cell holding that label; "left", "below" and "above" look the other ways.
"""

import datetime as dt
import re

from .workbook import get_sheet

CELL = re.compile(r"[A-Za-z]{1,3}[1-9]\d*")
DIRECTIONS = {"right": (0, 1), "left": (0, -1), "below": (1, 0), "above": (-1, 0)}
MAX_STEPS = 50


def _normalize(text):
    """Label text for comparison: no surrounding spaces, no trailing colon, any case."""
    return str(text).strip().rstrip(":").strip().casefold()


def _clean(value):
    if isinstance(value, dt.datetime):
        return value.date().isoformat() if not (value.hour or value.minute) else value.isoformat(" ")
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return value.strip()
    return value


def _spec(spec):
    """"B2" → {"cell": "B2"}; any other text → {"label": text}; dicts stay as they are."""
    if isinstance(spec, dict):
        return spec
    if CELL.fullmatch(str(spec)):
        return {"cell": str(spec)}
    return {"label": str(spec)}


def find_value(path, sheet, spec):
    """Value of one field on a sheet (formulas: the value Excel saved); None when not found."""
    spec = _spec(spec)
    _, ws = get_sheet(path, spec.get("sheet", sheet))

    if "cell" in spec:
        return _clean(ws[spec["cell"]].value)

    label = _normalize(spec["label"])
    direction = spec.get("direction", "right")

    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {list(DIRECTIONS)}, got {direction!r}")

    d_row, d_col = DIRECTIONS[direction]

    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and _normalize(cell.value) == label:
                for step in range(1, MAX_STEPS + 1):
                    row, column = cell.row + d_row * step, cell.column + d_col * step
                    if row < 1 or column < 1:
                        break
                    value = ws.cell(row, column).value
                    if value is not None and str(value).strip() != "":
                        return _clean(value)
                return None

    print(f"WARNING: label {spec['label']!r} not found on sheet {spec.get('sheet', sheet)!r}")
    return None


def read_sheet_values(path, sheet, fields):
    """{name: value} for every field in `fields` ({name: cell, label or spec})."""
    return {name: find_value(path, sheet, spec) for name, spec in (fields or {}).items()}
