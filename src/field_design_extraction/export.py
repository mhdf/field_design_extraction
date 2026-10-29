"""Write the consolidated tables: one design file per layout, one ratings file per date."""

from pathlib import Path

import pandas as pd

from .ratings import RATING_COLUMNS

# --- utf-8 with BOM, so Excel shows accented labels correctly
ENCODING = "utf-8-sig"


def write_design(design, folder, layout_id):
    """<folder>/<layout_id>.csv"""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{layout_id}.csv"
    design.to_csv(path, index=False, encoding=ENCODING)

    return path


def write_ratings(linked, folder, source_id, value_columns):
    """<folder>/<source_id>_<YYYYMMDD>.csv with the linked ratings of each date.

    Ratings that could not be linked go to <source_id>_<YYYYMMDD>_unlinked.csv
    (an older file of that name is removed when every rating is linked).
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    paths = []

    for date, group in linked.groupby("date"):
        stem = f"{source_id}_{pd.Timestamp(date):%Y%m%d}"

        ok = group[group["link_status"] == "linked"]
        path = folder / f"{stem}.csv"
        ok[RATING_COLUMNS + list(value_columns)].to_csv(path, index=False, encoding=ENCODING)
        paths.append(path)

        unlinked = group[group["link_status"] != "linked"]
        unlinked_path = folder / f"{stem}_unlinked.csv"

        if unlinked.empty:
            unlinked_path.unlink(missing_ok=True)
        else:
            unlinked[
                ["block_source", "block_id", "plot_number", "date", "disease", "link_status"]
                + list(value_columns)
            ].to_csv(unlinked_path, index=False, encoding=ENCODING)
            paths.append(unlinked_path)

    return paths
