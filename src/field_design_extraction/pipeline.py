"""Run the steps for a whole project: designs, ratings, export."""

from .export import write_design, write_ratings
from .layout import build_design, report_design
from .ratings import link_ratings, read_ratings, report_ratings


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
        value_columns = source.get("value_columns", {}).values()
        paths.extend(write_ratings(linked, folder, source_id, value_columns))

    print()
    print("EXPORTED")

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
