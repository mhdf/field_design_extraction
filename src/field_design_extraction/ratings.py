"""Ratings tables: read them and link every rating to a plot of the design."""

import datetime as dt
import re

import pandas as pd

from .layout import normalize_plot_number


RATING_COLUMNS = ["plot_key", "block_id", "plot_number", "date", "disease"]

# --- why a rating was not linked to a plot
LINK_STATUS = {
    "linked": "linked to one plot",
    "unmapped_block": "block label missing from block_mapping",
    "unknown_block": "block not in the design",
    "ambiguous": "plot number occurs more than once in the block",
    "no_match": "plot number not found in the block",
}


DATE_PATTERN = re.compile(r"\d{4}-\d{1,2}-\d{1,2}|\d{8}|\d{1,2}/\d{1,2}/\d{4}")


def date_label(value):
    """Assessment date as YYYY-MM-DD; any other text (e.g. 'Date 1') is kept as given."""
    if isinstance(value, (dt.date, dt.datetime, pd.Timestamp)):
        return pd.Timestamp(value).date().isoformat()

    text = str(value).strip()

    if DATE_PATTERN.fullmatch(text):
        return pd.to_datetime(text, dayfirst="/" in text).date().isoformat()

    return text


def date_stem(date):
    """Date for file names: 2025-09-10 → 20250910, 'Date 1' → date_1."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)):
        return str(date).replace("-", "")

    return re.sub(r"[^0-9a-z]+", "_", str(date).lower()).strip("_")


def _block_id(label, mapping):
    """Block label in the ratings → block_id of the design."""
    if label is None or (not isinstance(label, str) and pd.isna(label)):
        return None

    text = str(label).strip()

    if mapping is None:
        return text

    return mapping.get(text)


def read_ratings(source):
    """All assessment sheets of one ratings source in one table.

    source: dict with workbook, plot_column, value_columns, assessments and
            optional header_row, block_column, block_mapping (see the README).
    """
    header_row = source.get("header_row", 1)
    plot_column = source["plot_column"]
    block_column = source.get("block_column")
    value_columns = source.get("value_columns", {})
    mapping = source.get("block_mapping")

    tables = []

    for key, assessment in source["assessments"].items():
        df = pd.read_excel(
            source["workbook"],
            sheet_name=assessment["sheet"],
            header=header_row - 1,
        )

        needed = [plot_column, *value_columns] + ([block_column] if block_column else [])
        missing = [column for column in needed if column not in df.columns]

        if missing:
            raise ValueError(
                f"Assessment {key!r} (sheet {assessment['sheet']!r}): columns {missing} "
                f"not found. Columns read with header_row={header_row}: {list(df.columns)}"
            )

        df["plot_number"] = df[plot_column].apply(normalize_plot_number)

        # --- rows without a plot number (e.g. MIN/MAX rows below the table)
        no_plot = df["plot_number"].isna()

        if no_plot.any():
            print(f"  {key}: dropped {int(no_plot.sum())} rows without a plot number")
            df = df.loc[~no_plot]

        # --- block label: from a column, or one block per sheet
        if block_column:
            block_source = df[block_column]
        else:
            block_source = pd.Series(assessment.get("block"), index=df.index)

        table = pd.DataFrame({
            "block_source": block_source,
            "block_id": block_source.apply(lambda label: _block_id(label, mapping)),
            "plot_number": df["plot_number"],
            "date": date_label(assessment["date"]),
            "disease": source["disease"],
            "assessment": key,
        })

        for source_name, output_name in value_columns.items():
            table[output_name] = df[source_name]

        tables.append(table)

    return pd.concat(tables, ignore_index=True)


def link_ratings(ratings, design):
    """Add plot_key and link_status to every rating (see LINK_STATUS)."""
    keys = design[["block_id", "plot_number", "plot_key"]].copy()
    keys["n_plots"] = keys.groupby(["block_id", "plot_number"])["plot_key"].transform("nunique")

    unique_keys = keys.loc[keys["n_plots"] == 1, ["block_id", "plot_number", "plot_key"]]
    ambiguous = set(
        keys.loc[keys["n_plots"] > 1, ["block_id", "plot_number"]].itertuples(index=False, name=None)
    )

    linked = ratings.merge(
        unique_keys, on=["block_id", "plot_number"], how="left", validate="many_to_one",
    )

    design_blocks = set(design["block_id"])

    def status(row):
        if row["block_id"] is None or pd.isna(row["block_id"]):
            return "unmapped_block"
        if row["block_id"] not in design_blocks:
            return "unknown_block"
        if (row["block_id"], row["plot_number"]) in ambiguous:
            return "ambiguous"
        if pd.isna(row["plot_key"]):
            return "no_match"
        return "linked"

    linked["link_status"] = linked.apply(status, axis=1)

    return linked


def report_ratings(source_id, linked, design):
    """Print, per date, how many ratings were linked and what went wrong with the rest."""
    print()
    print("=" * 80)
    print(f"RATINGS — {source_id}")
    print("=" * 80)

    for date, group in linked.groupby("date"):
        n_linked = int((group["link_status"] == "linked").sum())
        rated_plots = group.loc[group["link_status"] == "linked", "plot_key"]
        repeated = rated_plots[rated_plots.duplicated()].nunique()

        print(
            f"{date}: {n_linked} of {len(group)} ratings linked; "
            f"{len(design) - rated_plots.nunique()} of {len(design)} plots without a rating"
            + (f"; WARNING: {repeated} plots rated more than once" if repeated else "")
        )

        problems = group[group["link_status"] != "linked"]

        if not problems.empty:
            for status, rows in problems.groupby("link_status"):
                print(f"  NOT LINKED — {LINK_STATUS[status]}: {len(rows)}")
                print(
                    rows[["block_source", "block_id", "plot_number"]]
                    .drop_duplicates()
                    .head(20)
                    .to_string(index=False)
                )
