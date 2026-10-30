"""Run the steps for a whole project: designs, ratings, export, figures."""

from pathlib import Path

from .export import write_design, write_ratings
from .layout import build_design, report_design
from .maps import map_value_columns, read_map_ratings, report_map_ratings
from .ratings import date_stem, link_ratings, read_ratings, report_ratings


def value_columns(source):
    """Columns written after RATING_COLUMNS for a ratings source."""
    if source.get("kind") == "map":
        return map_value_columns(source)

    return list(source.get("value_columns", {}).values())


def build_designs(layouts, verbose=True):
    """{layout_id: design table} for every layout."""
    designs = {}

    for layout_id, layout in layouts.items():
        design = build_design(layout_id, layout)

        if verbose:
            report_design(layout_id, design)

        designs[layout_id] = design

    return designs


def build_ratings(sources, designs, verbose=True):
    """{source_id: ratings table with plot_key and link_status} for every ratings source."""
    results = {}

    for source_id, source in sources.items():
        layout_id = source["layout_id"]

        if layout_id not in designs:
            raise ValueError(
                f"Ratings {source_id!r} refer to layout {layout_id!r}, "
                f"which is not in the layouts: {list(designs)}"
            )

        # --- "map": ratings marked on the field map; otherwise a ratings table
        if source.get("kind") == "map":
            linked = read_map_ratings(source, designs[layout_id])

            if verbose:
                report_map_ratings(source_id, linked, source)

        else:
            ratings = read_ratings(source)
            linked = link_ratings(ratings, designs[layout_id])

            if verbose:
                report_ratings(source_id, linked, designs[layout_id])

        results[source_id] = linked

    return results


def export(layouts, sources, designs, ratings):
    """Write every design and ratings table to the output_folder of its layout."""
    paths = []

    for layout_id, design in designs.items():
        paths.append(write_design(design, layouts[layout_id]["output_folder"], layout_id))

    for source_id, linked in ratings.items():
        source = sources[source_id]
        folder = layouts[source["layout_id"]]["output_folder"]
        paths.extend(write_ratings(linked, folder, source_id, value_columns(source)))

    print()
    print("EXPORTED")

    for path in paths:
        print(f"  {path}")

    return paths


# --- plot_design options that can be set in a layout's "figure" entry
DESIGN_FIGURE_KEYS = [
    "color_by", "colors", "names", "order", "label_column", "show_labels", "label_rotation",
    "rotate", "plot_size", "gaps", "gap_rule", "gap_min_pairs", "block_outlines", "legend_title", "title",
]

# --- layout options also used by the rating maps and coverage maps
MAP_LAYOUT_KEYS = [
    "label_column", "show_labels", "label_rotation", "rotate", "plot_size", "gaps",
    "gap_rule", "gap_min_pairs", "block_outlines",
]

FIGURE_TYPES = ("design", "distribution", "maps", "coverage", "incidence")

COVERAGE_COLORS = {"Assessed": "#111111", "Not assessed": "#FFFFFF"}


def figure_folder(layout):
    """<output_folder>/figures, unless the layout sets figure_folder."""
    return Path(layout.get("figure_folder", Path(layout["output_folder"]) / "figures"))


def save_figures(layouts, sources, designs, ratings, which=("design", "distribution"), show=False):
    """Save the selected figure types (see FIGURE_TYPES) as PNG files.

    design:       <layout_id>.png, the schematic of each layout
    distribution: <source_id>_distribution.png, classes per date
    maps:         <source_id>_<YYYYMMDD>_map.png, the schematic colored by the rating of each date
    coverage:     <source_id>_<YYYYMMDD>_coverage.png, ratings tables only: assessed vs not assessed plots
    incidence:    <source_id>_incidence.png, map ratings only: share of plots with a status per date
                  and group (needs "incidence": {"status": ..., "group": ...} in the source's "figure")

    Options: a layout's "figure" entry (plot_design keys, hatch_shared_with, hatch_label) and a
    source's "figure" entry (value, colors, names, order, bins, title, legend_title, xlabel,
    map_title with {disease} and {date}, incidence).
    """
    from .figures import group_other_values, plot_design, plot_distribution, plot_incidence, save_figure

    unknown = set(which) - set(FIGURE_TYPES)
    if unknown:
        raise ValueError(f"Unknown figure types {sorted(unknown)}; choose from {FIGURE_TYPES}")

    paths = []

    if "design" in which:
        for layout_id, design in designs.items():
            settings = layouts[layout_id].get("figure", {})
            options = {k: settings[k] for k in DESIGN_FIGURE_KEYS if k in settings}
            options.setdefault("title", f"Experimental design — {layout_id}")
            options.setdefault("legend_title", "Blocks")

            # --- hatch plots whose plot number also occurs in another layout
            other = settings.get("hatch_shared_with")
            if other in designs:
                options["hatch"] = design["plot_number"].isin(designs[other]["plot_number"])
                options["hatch_label"] = settings.get("hatch_label", f"Also in {other}")

            fig = plot_design(design, **options)
            paths.append(save_figure(fig, figure_folder(layouts[layout_id]) / f"{layout_id}.png", show=show))

    for source_id, linked in ratings.items():
        source = sources[source_id]
        layout = layouts[source["layout_id"]]
        design = designs[source["layout_id"]]
        settings = source.get("figure", {})
        folder = figure_folder(layout)
        value = settings.get("value") or (
            "status" if source.get("kind") == "map" else value_columns(source)[0]
        )
        rated = linked[linked["link_status"] == "linked"]
        style = {k: settings[k] for k in ("colors", "names", "order", "bins") if k in settings}

        # --- figures only: classes not in "keep" become one "others (...)" class
        group = settings.get("group_others")
        if group:
            rated = rated.copy()
            rated[value], others_label = group_other_values(
                rated[value], group["keep"], group.get("label", "others"),
                order=list(style.get("colors", {})),
                description=group.get("description"),
            )
            if others_label:
                colors = {k: c for k, c in style.get("colors", {}).items() if k in group["keep"]}
                colors[others_label] = group.get("color", "#9E9E9E")
                style = {**style, "colors": colors}

        if "distribution" in which:
            fig = plot_distribution(
                rated, value=value,
                title=settings.get("title", f"{source['disease']} — {source_id}"),
                legend_title=settings.get("legend_title", value),
                xlabel=settings.get("xlabel", "Frequency of plots [%]"),
                segment_labels=settings.get("segment_labels", "count"),
                **style,
            )
            paths.append(save_figure(fig, folder / f"{source_id}_distribution.png", show=show))

        if "incidence" in which and "incidence" in settings:
            options = settings["incidence"]
            fig = plot_incidence(
                rated, design,
                status=options["status"],
                group=options.get("group", "treatment"),
                colors=options.get("colors"),
                names=options.get("names"),
                exclude=options.get("exclude"),
                title=options.get("title", f"{source['disease']} incidence"),
                ylabel=options.get("ylabel"),
            )
            paths.append(save_figure(fig, folder / f"{source_id}_incidence.png", show=show))

        layout_settings = layout.get("figure", {})
        options = {k: layout_settings[k] for k in MAP_LAYOUT_KEYS if k in layout_settings}

        # --- coverage: which plots were assessed on each date (ratings tables only)
        if "coverage" in which and source.get("kind") != "map":
            for date, day in rated.groupby("date"):
                table = design.assign(
                    coverage=design["plot_key"].isin(day["plot_key"]).map(
                        {True: "Assessed", False: "Not assessed"}
                    )
                )
                fig = plot_design(
                    table, color_by="coverage", colors=COVERAGE_COLORS, legend_title="",
                    title=settings.get("coverage_title", "Assessment coverage — {date}").format(
                        disease=source["disease"], date=date,
                    ),
                    **options,
                )
                stem = f"{source_id}_{date_stem(date)}_coverage"
                paths.append(save_figure(fig, folder / f"{stem}.png", show=show))

        if "maps" in which:
            for date, day in rated.groupby("date"):
                table = design.merge(day[["plot_key", value]], on="plot_key", how="left")
                fig = plot_design(
                    table, color_by=value,
                    legend_title=settings.get("legend_title", value),
                    title=settings.get("map_title", "{disease} — {date}").format(
                        disease=source["disease"], date=date,
                    ),
                    **style, **options,
                )
                stem = f"{source_id}_{date_stem(date)}_map"
                paths.append(save_figure(fig, folder / f"{stem}.png", show=show))

    print()
    print("FIGURES")

    for path in paths:
        print(f"  {path}")

    return paths


def run(layouts, sources=None, verbose=True):
    """build_designs + build_ratings + export; returns (designs, ratings)."""
    sources = sources or {}
    designs = build_designs(layouts, verbose=verbose)
    ratings = build_ratings(sources, designs, verbose=verbose)
    export(layouts, sources, designs, ratings)

    return designs, ratings
