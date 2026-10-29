"""Turn spreadsheet field maps and rating sheets into a design table and one ratings table per date."""

from .diagnostics import color_summary, plot_cells
from .export import write_design, write_ratings
from .layout import DEFAULT_UNIT_RULES, build_design, report_design
from .pipeline import build_designs, build_ratings, export, run
from .ratings import link_ratings, read_ratings, report_ratings
from .workbook import read_cells

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_UNIT_RULES",
    "build_design",
    "build_designs",
    "build_ratings",
    "color_summary",
    "export",
    "link_ratings",
    "plot_cells",
    "read_cells",
    "read_ratings",
    "report_design",
    "report_ratings",
    "run",
    "write_design",
    "write_ratings",
]
