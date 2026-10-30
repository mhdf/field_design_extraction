"""Draw a worksheet as it looks in Excel: column letters, row numbers, fills, values, merged cells."""

import colorsys
import datetime as dt

from openpyxl.styles.colors import COLOR_INDEX
from openpyxl.utils import get_column_letter

from .workbook import get_sheet, parse_range

# --- Office default theme: theme index → colour (index 0/1 = background/text, 4-9 = accents)
THEME_COLORS = [
    "FFFFFF", "000000", "E7E6E6", "44546A", "4472C4",
    "ED7D31", "A5A5A5", "FFC000", "5B9BD5", "70AD47",
]
GRID_COLOR = "#D4D4D4"
HEADER_FILL = "#EFEFEF"
HEADER_TEXT = "#555555"
DEFAULT_WIDTH = 8.43        # characters
DEFAULT_HEIGHT = 15.0       # points


def _apply_tint(hex_rgb, tint):
    """Excel tint: positive values lighten, negative values darken."""
    r, g, b = (int(hex_rgb[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l * (1 + tint) if tint < 0 else l * (1 - tint) + tint
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"


def excel_color(color):
    """openpyxl colour (rgb, theme or indexed, with tint) → '#RRGGBB'; None when it has no colour."""
    if color is None:
        return None

    if color.type == "rgb" and isinstance(color.rgb, str) and len(color.rgb) >= 6:
        rgb = color.rgb[-6:]
    elif color.type == "theme" and color.theme is not None and color.theme < len(THEME_COLORS):
        rgb = THEME_COLORS[color.theme]
    elif color.type == "indexed" and color.indexed is not None and color.indexed < len(COLOR_INDEX):
        rgb = COLOR_INDEX[color.indexed][-6:]
    else:
        return None

    return _apply_tint(rgb, color.tint or 0.0)


def _cell_fill(cell):
    fill = cell.fill
    if fill is None or not fill.fill_type:
        return None
    return excel_color(fill.fgColor)


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d") if not (value.hour or value.minute) else value.isoformat(" ")
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value)


def _dimensions(ws, min_col, max_col, min_row, max_row):
    """Column widths and row heights in pixels (as Excel draws them at 100% zoom)."""
    default_width = ws.sheet_format.defaultColWidth or DEFAULT_WIDTH
    default_height = ws.sheet_format.defaultRowHeight or DEFAULT_HEIGHT
    widths = {c: default_width for c in range(min_col, max_col + 1)}

    for dim in ws.column_dimensions.values():
        if dim.width and dim.min is not None:
            for column in range(dim.min, (dim.max or dim.min) + 1):
                if column in widths:
                    widths[column] = dim.width

    heights = {}
    for row in range(min_row, max_row + 1):
        dim = ws.row_dimensions.get(row) if hasattr(ws.row_dimensions, "get") else None
        heights[row] = dim.height if dim is not None and dim.height else default_height

    col_px = {c: w * 7 + 5 for c, w in widths.items()}
    row_px = {r: h * 96 / 72 for r, h in heights.items()}
    return col_px, row_px


def plot_sheet(path, sheet, region=None, title=None, scale=1.0, show_headers=True):
    """Picture of a worksheet as Excel shows it (100% zoom), for documenting or checking an input file.

    region: Excel range to draw (e.g. "A1:Z24"); default: the used area of the sheet.
    scale:  1.0 draws cells at their size on screen; use less for very large sheets.
    Formula cells show the value Excel saved for them. Theme colours follow the default Office
    theme, so a workbook with its own colour theme may look slightly different than in Excel.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    ws, ws_values = get_sheet(path, sheet)

    if region is None:
        min_row, max_row, min_col, max_col = 1, ws.max_row, 1, ws.max_column
    else:
        min_row, max_row, min_col, max_col = parse_range(region)

    col_px, row_px = _dimensions(ws, min_col, max_col, min_row, max_row)
    header_w = 34 if show_headers else 0
    header_h = 20 if show_headers else 0

    x0 = {}
    x = header_w
    for column in range(min_col, max_col + 1):
        x0[column] = x
        x += col_px[column]
    total_w = x

    y0 = {}
    y = header_h
    for row in range(min_row, max_row + 1):
        y0[row] = y
        y += row_px[row]
    total_h = y

    # --- merged ranges inside the drawn area: anchor → (last row, last column)
    merged, covered = {}, set()
    for rng in ws.merged_cells.ranges:
        if rng.max_row < min_row or rng.min_row > max_row or rng.max_col < min_col or rng.min_col > max_col:
            continue
        r1, c1 = max(rng.min_row, min_row), max(rng.min_col, min_col)
        r2, c2 = min(rng.max_row, max_row), min(rng.max_col, max_col)
        merged[(rng.min_row, rng.min_col)] = (r1, c1, r2, c2)
        covered |= {(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)}

    # --- the figure is at least as wide as the title; the sheet sits on the left
    dpi = 96
    title_h = 40 if title else 0
    fig_w = max(total_w, len(title) * 8.5 + 20 if title else 0)
    fig = plt.figure(figsize=(fig_w * scale / dpi, (total_h + title_h) * scale / dpi))
    ax = fig.add_axes([0, 0, total_w / fig_w, total_h / (total_h + title_h)])
    ax.set_xlim(0, total_w)
    ax.set_ylim(total_h, 0)
    ax.axis("off")
    font = 8 * scale

    def is_empty(row, column):
        return (row, column) not in covered and ws.cell(row, column).value is None

    def draw_cell(cell, r1, c1, r2, c2):
        left, top = x0[c1], y0[r1]
        width = sum(col_px[c] for c in range(c1, c2 + 1))
        height = sum(row_px[r] for r in range(r1, r2 + 1))
        fill = _cell_fill(cell)
        ax.add_patch(Rectangle((left, top), width, height, facecolor=fill or "white",
                               edgecolor=GRID_COLOR, linewidth=0.5 * scale))

        value = ws_values.cell(cell.row, cell.column).value if cell.data_type == "f" else cell.value
        text = _cell_text(value)
        if not text:
            return

        alignment = cell.alignment
        rotation = alignment.text_rotation or 0
        rotation = 90 if rotation == 255 else (rotation if rotation <= 90 else 90 - rotation)
        horizontal = alignment.horizontal or ("right" if isinstance(value, (int, float)) else "left")
        if horizontal not in ("left", "right", "center"):
            horizontal = "center"

        if rotation or horizontal == "center":
            tx, ha = left + width / 2, "center"
        elif horizontal == "right":
            tx, ha = left + width - 3, "right"
        else:
            tx, ha = left + 3, "left"

        r, g, b = (int(fill[i:i + 2], 16) / 255 for i in (1, 3, 5)) if fill else (1, 1, 1)
        color = "white" if 0.299 * r + 0.587 * g + 0.114 * b < 0.45 else "black"

        # --- as in Excel: left-aligned text runs on over empty cells to its right,
        #     otherwise it is cut at the cell border
        clip_right = left + width
        if ha == "left" and not rotation:
            column = c2 + 1
            while column <= max_col and is_empty(r1, column):
                clip_right += col_px[column]
                column += 1

        label = ax.text(tx, top + height / 2, text, ha=ha, va="center", rotation=rotation,
                        fontsize=font, fontweight="bold" if cell.font and cell.font.b else "normal",
                        color=color, zorder=3)
        label.set_clip_path(Rectangle((left, top), clip_right - left, height, transform=ax.transData))
        label.set_clip_on(True)

    for row in range(min_row, max_row + 1):
        for column in range(min_col, max_col + 1):
            if (row, column) in covered and (row, column) not in merged:
                continue
            cell = ws.cell(row, column)
            r1, c1, r2, c2 = merged.get((row, column), (row, column, row, column))
            draw_cell(cell, r1, c1, r2, c2)

    # --- merged ranges whose anchor lies outside the drawn area
    for (row, column), (r1, c1, r2, c2) in merged.items():
        if row < min_row or column < min_col:
            draw_cell(ws.cell(row, column), r1, c1, r2, c2)

    if show_headers:
        ax.add_patch(Rectangle((0, 0), total_w, header_h, facecolor=HEADER_FILL, edgecolor=GRID_COLOR, linewidth=0.5))
        ax.add_patch(Rectangle((0, 0), header_w, total_h, facecolor=HEADER_FILL, edgecolor=GRID_COLOR, linewidth=0.5))
        for column in range(min_col, max_col + 1):
            ax.add_patch(Rectangle((x0[column], 0), col_px[column], header_h, fill=False,
                                   edgecolor=GRID_COLOR, linewidth=0.5))
            ax.text(x0[column] + col_px[column] / 2, header_h / 2, get_column_letter(column),
                    ha="center", va="center", fontsize=font, color=HEADER_TEXT)
        for row in range(min_row, max_row + 1):
            ax.add_patch(Rectangle((0, y0[row]), header_w, row_px[row], fill=False,
                                   edgecolor=GRID_COLOR, linewidth=0.5))
            ax.text(header_w / 2, y0[row] + row_px[row] / 2, str(row),
                    ha="center", va="center", fontsize=font, color=HEADER_TEXT)

    if title:
        fig.text(8 / fig_w, 1 - 20 / (total_h + title_h), title, ha="left", va="center", fontsize=10 * scale)

    fig.fixed_size = True
    return fig
