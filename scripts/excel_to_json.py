#!/usr/bin/env python3
"""
excel_to_json.py — Excel → JSON Converter
=========================================
Convert Excel files into JSON files (one per sheet).

Usage:
    python scripts/excel_to_json.py --input data.xlsx
    python scripts/excel_to_json.py --input a.xlsx --input b.xls --output out --pretty
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import click
import pandas as pd
from loguru import logger
from rich.console import Console

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def configure_logger(verbose: bool) -> None:
    """Configure loguru log level based on --verbose flag."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        lambda msg: console.print(msg, end=""),
        level=level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )


def safe_name(value: str) -> str:
    """Make a filesystem-friendly name from a string."""
    value = value.strip().replace(" ", "_")
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value or "sheet"


def normalize_value(value: Any) -> Any:
    """Normalize pandas cell values for JSON serialization."""
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    # Convert numpy scalar types to native Python
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return value
    return value


def convert_sheet(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into a list of JSON-ready row dicts."""
    records = df.to_dict(orient="records")
    converted: list[dict[str, Any]] = []
    for row in records:
        converted.append({k: normalize_value(v) for k, v in row.items()})
    return converted


def load_excel_sheets(path: Path, sheet: str | None) -> dict[str, pd.DataFrame]:
    """Load one or more sheets from an Excel file."""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        sys.exit(1)

    logger.debug(f"Loading {path.name!r}")

    try:
        if path.suffix.lower() == ".xls":
            # xlrd is required for .xls support
            return pd.read_excel(path, sheet_name=sheet or None, engine="xlrd")
        return pd.read_excel(path, sheet_name=sheet or None, engine="openpyxl")
    except ImportError as exc:
        console.print(f"[red]Missing dependency:[/red] {exc}")
        if path.suffix.lower() == ".xls":
            console.print("Install xlrd for .xls support: [cyan]pip install xlrd[/cyan]")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Could not read {path}: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--input",
    "-i",
    "inputs",
    required=True,
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Input Excel file(s). Repeat for multiple files.",
)
@click.option(
    "--output",
    "-o",
    default=Path("."),
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory (default: current directory).",
)
@click.option(
    "--sheet",
    "-s",
    default=None,
    help="Specific sheet name to export (default: all sheets).",
)
@click.option(
    "--pretty",
    is_flag=True,
    default=False,
    help="Pretty-print JSON output.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
def main(
    inputs: Iterable[Path],
    output: Path,
    sheet: str | None,
    pretty: bool,
    verbose: bool,
) -> None:
    """Convert Excel files into JSON files (one per sheet)."""
    configure_logger(verbose)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    indent = 2 if pretty else None

    for excel_path in inputs:
        excel_path = excel_path.resolve()
        sheets = load_excel_sheets(excel_path, sheet)

        if not sheets:
            logger.warning(f"No sheets found in {excel_path.name}")
            continue

        for sheet_name, df in sheets.items():
            safe_sheet = safe_name(str(sheet_name))
            out_name = f"{excel_path.stem}_{safe_sheet}.json"
            out_path = output / out_name

            logger.info(f"Converting {excel_path.name} → {sheet_name}")
            rows = convert_sheet(df)

            with out_path.open("w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=indent)

            logger.info(f"Saved {len(rows):,} rows → {out_path}")


if __name__ == "__main__":
    main()
