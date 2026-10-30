"""Figures from the consolidated tables: design schematics, rating maps and rating distributions.

Style taken from the wheat (2025/2026) figure scripts: monospace font, pastel fills with dark edges,
legends below the plot.
"""

from pathlib import Path

import numpy as np
import pandas as pd

FONT_FAMILY = "DejaVu Sans Mono"
FONT_SIZE = 10
EDGE_COLOR = "#303030"
NOT_RATED_COLOR = "#EDEDED"
TRANSITION_FILL = "#F7F7F7"

# --- block palette of the wheat design figures, in order of use
QUALITATIVE = [
    "#3F88C5", "#43B97F", "#D4C93D", "#F28E2B", "#8757B5",
    "#36A9D6", "#8BC34A", "#F2B134", "#E85D3F", "#D94F70",
]

# --- disease scale of the wheat score figures (low → high), fills and edges
SCORE_FILLS = ["#C7D9EA", "#B5D5C3", "#E5D8A8", "#E6B69E", "#D89B9B"]
SCORE_EDGES = ["#718FAE", "#6E9A7C", "#9E8F5D", "#A76F5B", "#975D5D"]


def _style():
    import matplotlib.pyplot as plt

    return plt.rc_context({
        "font.family": FONT_FAMILY,
        "font.size": FONT_SIZE,
        "axes.titlesize": FONT_SIZE + 2,
        "legend.fontsize": FONT_SIZE,
        "legend.title_fontsize": FONT_SIZE,
    })


# =============================================
# COLORS
# =============================================

def _is_numeric(values):
    values = pd.Series(values).dropna()
    return len(values) > 0 and pd.to_numeric(values, errors="coerce").notna().all()


def _interpolate(anchors, t):
    """Color at position t (0-1) along a list of hex colors."""
    from matplotlib.colors import to_hex, to_rgb

    rgb = np.array([to_rgb(c) for c in anchors])
    position = t * (len(anchors) - 1)
    i = min(int(position), len(anchors) - 2)
    return to_hex(rgb[i] + (rgb[i + 1] - rgb[i]) * (position - i))


def score_classes(values, bins=None, max_classes=12):
    """Numbers with many different values (e.g. % severity) → classes such as '10–20'.

    bins: class edges; by default 10-unit classes for values within 0-100.
    Returns (values or class labels, ordered class labels or None when not binned).
    """
    values = pd.Series(values)

    if not _is_numeric(values):
        return values, None

    numbers = pd.to_numeric(values, errors="coerce")

    if bins is None:
        if numbers.nunique() <= max_classes:
            return values, None

        low, high = numbers.min(), numbers.max()
        step = 10.0 if low >= 0 and high <= 100 else float(f"{(high - low) / 8:.1g}")
        edges = list(np.arange(np.floor(low / step) * step, high + step, step))

        if edges[-1] <= high:
            edges.append(edges[-1] + step)
    else:
        edges = list(bins)

    labels = [f"{a:g}–{b:g}" for a, b in zip(edges[:-1], edges[1:])]
    classes = pd.cut(numbers, edges, right=False, labels=labels).astype(object)

    return classes.where(numbers.notna()), labels


def group_other_values(values, keep, label="others", order=None):
    """Values not in `keep` become one class, e.g. 'others (gummosis, dead, missing)'.

    order: order in which the grouped values are listed (default: as they occur).
    Returns (values, label of the grouped class or None when nothing was grouped).
    """
    values = pd.Series(values)
    present = list(values.dropna().unique())
    others = [v for v in (order or []) if v in present and v not in keep]
    others += [v for v in present if v not in keep and v not in others]

    if not others:
        return values, None

    full_label = f"{label} ({', '.join(str(v).replace('_', ' ') for v in others)})"

    return values.where(values.isin(keep) | values.isna(), full_label), full_label


def value_styles(values, colors=None, order=None, scale=False):
    """{value: (fill, edge, hatch)} for the categories in `values`.

    Numbers follow the disease scale (low = blue, high = red); when integers and
    in-between values (e.g. 1.5) occur together, the in-between ones are hatched.
    scale=True: categories in `order` (e.g. score classes) also follow the disease scale.
    Other values get `colors` (dict) or the block palette.
    """
    present = list(pd.Series(values).dropna().unique())

    if colors is None and scale and order:
        ordered = [v for v in order if v in present]
        n = max(len(order) - 1, 1)
        return {
            v: (_interpolate(SCORE_FILLS, order.index(v) / n), _interpolate(SCORE_EDGES, order.index(v) / n), None)
            for v in ordered
        }

    if colors is None and _is_numeric(present):
        numbers = sorted(float(v) for v in present)
        low, high = numbers[0], numbers[-1]
        mixed = any(n.is_integer() for n in numbers) and not all(n.is_integer() for n in numbers)
        styles = {}

        for value in present:
            number = float(value)
            t = 0.0 if high == low else (number - low) / (high - low)
            edge = _interpolate(SCORE_EDGES, t)

            if mixed and not number.is_integer():
                styles[value] = (TRANSITION_FILL, edge, "///")
            else:
                styles[value] = (_interpolate(SCORE_FILLS, t), edge, None)

        return dict(sorted(styles.items(), key=lambda item: float(item[0])))

    if order is None:
        order = list(colors) if colors else present

    ordered = [v for v in order if v in present] + [v for v in present if v not in order]
    colors = colors or {}
    palette = iter(QUALITATIVE * (len(ordered) // len(QUALITATIVE) + 1))

    return {
        value: (colors[value] if value in colors else next(palette), EDGE_COLOR, None)
        for value in ordered
    }


# =============================================
# POSITIONS ON THE SCHEMATIC
# =============================================

def schematic_positions(
    df, plot_size=(1.0, 1.8), gaps=(0.25, 0.20), rotate=None, gap_rule="any", gap_min_pairs=2,
):
    """x, y (top-left corner) of each plot: empty map rows/columns removed, gaps between blocks.

    gaps:     (horizontal, vertical) gap size, in plot-width units.
    gap_rule: "any" — gap between two neighbouring rows (columns) where at least gap_min_pairs
              plots and their neighbours belong to different blocks (the gap runs across the
              whole figure, so it may also cut other blocks); "disjoint" — only when the two
              rows (columns) share no block at all.
    rotate:   None, "clockwise" or "counterclockwise" (plot width and height swap).
    """
    if gap_rule not in ("any", "disjoint"):
        raise ValueError("gap_rule must be 'any' or 'disjoint'")

    df = df.copy()
    row, column = df["row"].astype(int), df["column"].astype(int)
    width, height = plot_size

    if rotate == "clockwise":
        row, column = column, row.max() - row
        width, height = height, width
    elif rotate == "counterclockwise":
        row, column = column.max() - column, row
        width, height = height, width
    elif rotate is not None:
        raise ValueError("rotate must be None, 'clockwise' or 'counterclockwise'")

    def axis_positions(index, other, size, gap):
        """Positions along one axis; `other` is the perpendicular coordinate."""
        values = sorted(index.unique())
        lines = {
            value: dict(zip(other[index == value], df.loc[index == value, "block_id"]))
            for value in values
        }
        positions, current = {}, 0.0

        for i, value in enumerate(values):
            positions[value] = current
            current += size

            if i == len(values) - 1:
                continue

            here, there = lines[value], lines[values[i + 1]]

            if gap_rule == "disjoint":
                split = set(here.values()).isdisjoint(there.values())
            else:
                split = sum(here[k] != there[k] for k in here.keys() & there.keys()) >= gap_min_pairs

            if split:
                current += gap

        return index.map(positions)

    df["x"] = axis_positions(column, row, width, gaps[0])
    df["y"] = axis_positions(row, column, height, gaps[1])
    df.attrs["plot_size"] = (width, height)

    return df


# =============================================
# SCHEMATIC MAP
# =============================================

def plot_design(
    df,
    color_by="block_id",
    colors=None,
    names=None,
    order=None,
    label_column="plot_number",
    show_labels=None,
    hatch=None,
    hatch_label=None,
    rotate=None,
    plot_size=(1.0, 1.8),
    gaps=(0.25, 0.20),
    gap_rule="any",
    gap_min_pairs=2,
    label_rotation=None,
    block_outlines=False,
    legend_title=None,
    title=None,
    bins=None,
):
    """Schematic map: one rectangle per plot, colored by a column (block, treatment, score, status).

    df:          design table (optionally joined with ratings).
    colors:      {value: color}; numbers default to the disease scale, others to the block palette.
    names:       {value: legend text}.
    hatch:       column name or True/False Series: hatched plots (legend text: hatch_label).
    show_labels: plot numbers inside the plots (default: when there are at most 1500 plots).
    label_rotation: angle of the plot numbers (e.g. 0 or 90); default: 90 in tall plots, else 0.
    gaps, gap_rule: space between blocks (see schematic_positions).
    bins:        class edges for numbers with many values (see score_classes).
    Plots with no value in `color_by` are drawn light grey ("not rated").
    """
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch, Rectangle

    df = schematic_positions(df, plot_size, gaps, rotate, gap_rule, gap_min_pairs)
    width, height = df.attrs["plot_size"]

    classes, class_order = score_classes(df[color_by], bins)
    if class_order is not None:
        df["_class"], color_by, order = classes.values, "_class", class_order

    styles = value_styles(df[color_by], colors, order, scale=class_order is not None)
    names = names or {}

    if isinstance(hatch, str):
        hatch = df[hatch].astype(bool)
    hatched = (
        pd.Series(False, index=df.index) if hatch is None
        else pd.Series(hatch, index=df.index).fillna(False).astype(bool)
    )

    if show_labels is None:
        show_labels = len(df) <= 1500

    max_x = df["x"].max() + width
    max_y = df["y"].max() + height

    with _style():
        fig, ax = plt.subplots(figsize=(
            max(8, min(18, max_x * 0.65)),
            max(6, min(16, max_y * 0.42)),
        ))

        for is_hatched in (False, True):
            part = df[hatched == is_hatched]
            if part.empty:
                continue

            fills, edges, patches = [], [], []

            for x, y, value in zip(part["x"], part["y"], part[color_by]):
                fill, edge, value_hatch = styles.get(value, (NOT_RATED_COLOR, EDGE_COLOR, None))
                patches.append(Rectangle((x, y), width, height))
                fills.append(fill)
                edges.append(EDGE_COLOR if value_hatch is None else edge)

            ax.add_collection(PatchCollection(
                patches,
                facecolors=fills,
                edgecolors=edges,
                linewidths=0.7 if len(df) <= 1500 else 0.1,
                hatch="///" if is_hatched else None,
                zorder=2,
            ))

        # --- in-between scores: hatched fill, drawn on top
        transition = df[[styles.get(v, (None, None, None))[2] is not None for v in df[color_by]]]
        if not transition.empty:
            ax.add_collection(PatchCollection(
                [Rectangle((x, y), width, height) for x, y in zip(transition["x"], transition["y"])],
                facecolors=[styles[v][0] for v in transition[color_by]],
                edgecolors=[styles[v][1] for v in transition[color_by]],
                linewidths=0.7,
                hatch="///",
                zorder=2,
            ))

        if show_labels:
            if label_rotation is None:
                label_rotation = 90 if height > width else 0

            for x, y, label, value in zip(df["x"], df["y"], df[label_column], df[color_by]):
                if pd.isna(label):
                    continue

                # --- white text on dark fills
                fill = styles.get(value, (NOT_RATED_COLOR,))[0]
                r, g, b = to_rgb(fill)
                text_color = "white" if 0.299 * r + 0.587 * g + 0.114 * b < 0.45 else "black"

                ax.text(
                    x + width / 2, y + height / 2, str(label),
                    ha="center", va="center", rotation=label_rotation,
                    fontsize=7, color=text_color, zorder=4,
                )

        if block_outlines:
            for block_id, block in df.groupby("block_id", sort=False):
                x0, y0 = block["x"].min(), block["y"].min()
                x1, y1 = block["x"].max() + width, block["y"].max() + height
                ax.add_patch(Rectangle(
                    (x0, y0), x1 - x0, y1 - y0,
                    fill=False, edgecolor=EDGE_COLOR, linewidth=1.5, zorder=5,
                ))
                ax.text(
                    (x0 + x1) / 2, (y0 + y1) / 2, str(block_id),
                    ha="center", va="center", fontsize=FONT_SIZE, zorder=6,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1.5},
                )

        ax.set_xlim(-0.6, max_x + 0.6)
        ax.set_ylim(max_y + 0.6, -0.5)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        if title:
            ax.set_title(title, pad=15)

        # --- legends below the map
        handles = [
            Patch(facecolor=fill, edgecolor=edge, hatch=value_hatch, label=names.get(value, _format(value)))
            for value, (fill, edge, value_hatch) in styles.items()
        ]
        if df[color_by].isna().any():
            handles.append(Patch(facecolor=NOT_RATED_COLOR, edgecolor=EDGE_COLOR, label="not rated"))

        legends = [ax.legend(
            handles=handles,
            title=color_by if legend_title is None else legend_title,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.01),
            ncol=_legend_columns(len(handles)),
            frameon=True,
        )]

        if hatched.any() and hatch_label:
            ax.add_artist(legends[0])
            legends.append(ax.legend(
                handles=[Patch(facecolor="#E5E5E5", edgecolor=EDGE_COLOR, hatch="///", label=hatch_label)],
                loc="upper center",
                bbox_to_anchor=(0.5, -0.01 - 0.045 * (2 + (len(handles) - 1) // _legend_columns(len(handles)))),
                frameon=False,
            ))

        fig.legends_below = legends

    return fig


def _legend_columns(n):
    """One legend row up to 6 entries, otherwise 5 columns."""
    return n if n <= 6 else 5


def _format(value):
    if isinstance(value, float) and value.is_integer():
        return f"{value:g}"
    return str(value)


# =============================================
# DISTRIBUTION PER DATE
# =============================================

def plot_distribution(
    ratings,
    value="score",
    by="date",
    colors=None,
    names=None,
    order=None,
    title=None,
    legend_title=None,
    xlabel="Frequency of plots [%]",
    bins=None,
    segment_labels="count",
):
    """Horizontal 100% stacked bars: share of plots in each class (score or status), one bar per date.

    bins:           class edges for numbers with many values (see score_classes).
    segment_labels: text inside each segment: "count" (number of plots), "percent" or None.
    """
    if segment_labels not in ("count", "percent", None):
        raise ValueError("segment_labels must be 'count', 'percent' or None")

    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    data = ratings[ratings[value].notna()].copy()

    classes, class_order = score_classes(data[value], bins)
    if class_order is not None:
        data["_class"], value_column, order = classes.values, "_class", class_order
    else:
        value_column = value

    styles = value_styles(data[value_column], colors, order, scale=class_order is not None)
    names = names or {}

    counts = data.groupby([by, value_column]).size().unstack(fill_value=0)
    counts = counts[[v for v in styles if v in counts.columns]]
    percent = counts.div(counts.sum(axis=1), axis=0) * 100
    groups = list(percent.index)

    with _style():
        height = 2.2 + 0.45 * len(groups)
        fig, ax = plt.subplots(figsize=(9, height))
        fig.subplots_adjust(left=0.2, right=0.97, top=1 - 0.6 / height, bottom=1.0 / height)
        y_positions = np.arange(len(groups))[::-1] * 0.6

        for y, group in zip(y_positions, groups):
            left = 0.0
            for category, (fill, edge, hatch) in styles.items():
                share = percent.loc[group].get(category, 0)
                if share <= 0:
                    continue
                ax.barh(y, share, left=left, height=0.5, color=fill, edgecolor=edge,
                        linewidth=1.0, hatch=hatch, zorder=3)
                if segment_labels and share >= 5:
                    text = (
                        f"{int(counts.loc[group, category]):,}" if segment_labels == "count"
                        else f"{share:.1f}"
                    )
                    ax.text(left + share / 2, y, text, ha="center", va="center",
                            color="#303030", fontsize=FONT_SIZE - 1)
                left += share

        ax.set_xlim(0, 100)
        ax.set_ylim(y_positions.min() - 0.4, y_positions.max() + 0.4)
        ax.set_yticks(
            y_positions,
            [f"{group}\n[n = {int(counts.loc[group].sum()):,}]" for group in groups],
        )
        ax.tick_params(axis="y", length=0)
        ax.set_xticks(np.arange(0, 101, 20))
        ax.set_xlabel(xlabel, labelpad=8)
        ax.grid(axis="x", linestyle="--", linewidth=0.7, alpha=0.35, zorder=0)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("#333333")
            spine.set_linewidth(1.2)
        if title:
            ax.set_title(title, pad=14)

        handles = [
            Patch(facecolor=fill, edgecolor=edge, hatch=hatch, label=names.get(v, _format(v)))
            for v, (fill, edge, hatch) in styles.items()
        ]
        axes_height = height * (ax.get_position().y1 - ax.get_position().y0)
        fig.legends_below = [ax.legend(
            handles=handles,
            title=legend_title or value,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.75 / axes_height),
            ncol=_legend_columns(len(handles)),
            frameon=True,
            fancybox=False,
            edgecolor="#555555",
        )]

    return fig


# =============================================
# INCIDENCE OVER TIME, PER GROUP
# =============================================

def plot_incidence(
    ratings,
    design,
    status="hlb",
    group="treatment",
    colors=None,
    names=None,
    exclude=None,
    title=None,
    ylabel=None,
):
    """Share of plots with `status` per date, one line per group (e.g. treatment).

    exclude: statuses left out of the total (e.g. ["no_tree"]).
    """
    import matplotlib.pyplot as plt

    data = ratings.merge(design[["plot_key", group]], on="plot_key", how="left")
    if exclude:
        data = data[~data["status"].isin(exclude)]

    data = data.assign(has_status=data["status"] == status, date=pd.to_datetime(data["date"]))
    incidence = data.groupby(["date", group])["has_status"].mean().unstack() * 100
    styles = value_styles(list(incidence.columns), colors)
    names = names or {}

    with _style():
        fig, ax = plt.subplots(figsize=(9, 5))

        for value, (fill, edge, _) in styles.items():
            line_color = edge if fill.upper() in ("#FFFFFF", "WHITE") else fill
            ax.plot(incidence.index, incidence[value], marker="o", markersize=4, linewidth=1.6,
                    color=line_color, markeredgecolor=EDGE_COLOR, markeredgewidth=0.5,
                    label=names.get(value, _format(value)))

        ax.set_ylabel(ylabel or f"Plots with {status} [%]")
        ax.set_ylim(0, max(5, incidence.max().max() * 1.08))
        ax.grid(linestyle="--", linewidth=0.7, alpha=0.35)
        for spine in ax.spines.values():
            spine.set_color("#333333")
        if title:
            ax.set_title(title, pad=14)
        fig.legends_below = [ax.legend(
            title=group, loc="upper center", bbox_to_anchor=(0.5, -0.12),
            ncol=min(6, len(styles)), frameon=True, fancybox=False, edgecolor="#555555",
        )]
        fig.autofmt_xdate()

    return fig


# =============================================
# SAVE
# =============================================

def save_figure(fig, path, dpi=300, show=False):
    """Save as PNG (white background, legends included); close unless show=True."""
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path, dpi=dpi, bbox_inches="tight", pad_inches=0.2, facecolor="white",
        bbox_extra_artists=getattr(fig, "legends_below", None),
    )

    if show:
        plt.show()
    else:
        plt.close(fig)

    return path
