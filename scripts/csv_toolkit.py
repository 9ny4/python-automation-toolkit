#!/usr/bin/env python3
"""
csv_toolkit.py — CSV Toolkit
==============================
A collection of handy CSV utilities: merge, dedupe, filter, and stats.

Usage:
    python csv_toolkit.py merge -i a.csv b.csv -o merged.csv
    python csv_toolkit.py dedupe -i data.csv -o clean.csv --cols email
    python csv_toolkit.py filter -i data.csv -o out.csv --col status --value active
    python csv_toolkit.py stats  -i data.csv
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from loguru import logger
from rich.console import Console
from rich.table import Table

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


def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame with friendly error handling."""
    if not path.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        sys.exit(1)
    try:
        df = pd.read_csv(path)
        logger.debug(f"Loaded {path.name!r} — {len(df):,} rows × {len(df.columns)} cols")
        return df
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] Could not read {path}: {exc}")
        sys.exit(1)


def save_csv(df: pd.DataFrame, path: Path, dry_run: bool) -> None:
    """Write DataFrame to CSV, or print preview if dry-run."""
    if dry_run:
        console.rule("[yellow]Dry run — output preview (first 5 rows)[/yellow]")
        console.print(df.head().to_string(index=False))
        console.print(f"\n[yellow]Would write {len(df):,} rows to {path}[/yellow]")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    console.print(f"\n[green]✓[/green] Saved {len(df):,} rows → {path}")


# ---------------------------------------------------------------------------
# Shared options decorator
# ---------------------------------------------------------------------------

_common_options = [
    click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose logging."),
    click.option(
        "--dry-run", "-n",
        is_flag=True,
        default=False,
        help="Preview result without writing output file.",
    ),
]


def common_options(func):
    """Attach shared --verbose and --dry-run options to a command."""
    for option in reversed(_common_options):
        func = option(func)
    return func


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option("1.0.0", prog_name="csv-toolkit")
def cli() -> None:
    """CSV Toolkit — merge, dedupe, filter, and inspect CSV files."""


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--input", "-i", "inputs",
    required=True,
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input CSV files (repeat for multiple). At least two required.",
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output CSV file path.",
)
@common_options
def merge(inputs: tuple[Path, ...], output: Path, verbose: bool, dry_run: bool) -> None:
    """Merge multiple CSV files into a single output file.

    Handles files with different column sets — missing values become empty cells.

    \b
    Example:
        python csv_toolkit.py merge -i jan.csv feb.csv mar.csv -o q1.csv
    """
    configure_logger(verbose)

    if len(inputs) < 2:
        console.print("[red]Error:[/red] Provide at least two input files with -i.")
        sys.exit(1)

    frames: list[pd.DataFrame] = []
    for path in inputs:
        df = load_csv(path)
        df["_source_file"] = path.name
        frames.append(df)
        logger.info(f"Read {path.name!r}: {len(df):,} rows")

    merged = pd.concat(frames, ignore_index=True, sort=False)
    # Move _source_file to end for cleanliness
    cols = [c for c in merged.columns if c != "_source_file"] + ["_source_file"]
    merged = merged[cols]

    console.print(f"\nMerged [cyan]{len(inputs)}[/cyan] files → "
                  f"[cyan]{len(merged):,}[/cyan] rows, "
                  f"[cyan]{len(merged.columns)}[/cyan] columns")

    save_csv(merged, output, dry_run)


# ---------------------------------------------------------------------------
# dedupe
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--input", "-i", "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input CSV file.",
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output CSV file path.",
)
@click.option(
    "--cols", "-c",
    default=None,
    help="Comma-separated column names to deduplicate on. Defaults to all columns.",
)
@click.option(
    "--keep",
    type=click.Choice(["first", "last", "none"], case_sensitive=False),
    default="first",
    show_default=True,
    help="Which duplicate to keep: first, last, or none (drop all duplicates).",
)
@common_options
def dedupe(
    input_path: Path,
    output: Path,
    cols: Optional[str],
    keep: str,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Remove duplicate rows from a CSV file.

    \b
    Example:
        python csv_toolkit.py dedupe -i contacts.csv -o clean.csv --cols email,phone
    """
    configure_logger(verbose)

    df = load_csv(input_path)
    original_count = len(df)

    subset = [c.strip() for c in cols.split(",")] if cols else None
    if subset:
        missing = [c for c in subset if c not in df.columns]
        if missing:
            console.print(f"[red]Error:[/red] Column(s) not found: {missing}")
            console.print(f"Available columns: {list(df.columns)}")
            sys.exit(1)

    keep_param: bool | str = keep if keep != "none" else False
    df_clean = df.drop_duplicates(subset=subset, keep=keep_param)  # type: ignore[arg-type]

    removed = original_count - len(df_clean)
    console.print(
        f"\nDeduplication: [cyan]{original_count:,}[/cyan] rows → "
        f"[green]{len(df_clean):,}[/green] rows  "
        f"([red]{removed:,} duplicates removed[/red])"
    )
    if subset:
        console.print(f"Key columns: [cyan]{', '.join(subset)}[/cyan]")

    save_csv(df_clean, output, dry_run)


# ---------------------------------------------------------------------------
# filter
# ---------------------------------------------------------------------------

@cli.command(name="filter")
@click.option(
    "--input", "-i", "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input CSV file.",
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output CSV file path.",
)
@click.option("--col", required=True, help="Column name to filter on.")
@click.option("--value", required=True, help="Value to match (case-insensitive).")
@click.option(
    "--exclude",
    is_flag=True,
    default=False,
    help="Exclude matching rows instead of keeping them.",
)
@common_options
def filter_cmd(
    input_path: Path,
    output: Path,
    col: str,
    value: str,
    exclude: bool,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Filter CSV rows by column value.

    \b
    Example:
        python csv_toolkit.py filter -i orders.csv -o active.csv --col status --value active
        python csv_toolkit.py filter -i orders.csv -o pending.csv --col status --value cancelled --exclude
    """
    configure_logger(verbose)

    df = load_csv(input_path)

    if col not in df.columns:
        console.print(f"[red]Error:[/red] Column {col!r} not found.")
        console.print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    mask = df[col].astype(str).str.lower() == value.lower()
    matched = mask.sum()

    if exclude:
        result = df[~mask]
        action = "excluded"
    else:
        result = df[mask]
        action = "kept"

    console.print(
        f"\nFilter [cyan]{col}[/cyan] == [cyan]{value!r}[/cyan]: "
        f"[green]{matched:,}[/green] match(es) — "
        f"[cyan]{len(result):,}[/cyan] rows {action}"
    )

    save_csv(result, output, dry_run)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--input", "-i", "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input CSV file.",
)
@click.option(
    "--full",
    is_flag=True,
    default=False,
    help="Show full numeric summary (percentiles etc.).",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose logging.")
def stats(input_path: Path, full: bool, verbose: bool) -> None:
    """Print summary statistics for a CSV file.

    \b
    Example:
        python csv_toolkit.py stats -i sales.csv
        python csv_toolkit.py stats -i sales.csv --full
    """
    configure_logger(verbose)

    df = load_csv(input_path)

    # ---- Overview ----
    overview = Table(title=f"Overview: {input_path.name}", header_style="bold cyan")
    overview.add_column("Metric", style="cyan")
    overview.add_column("Value", style="magenta", justify="right")
    overview.add_row("Rows", f"{len(df):,}")
    overview.add_row("Columns", str(len(df.columns)))
    overview.add_row("Memory usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    console.print(overview)
    console.print()

    # ---- Column breakdown ----
    col_table = Table(title="Column Details", header_style="bold cyan")
    col_table.add_column("Column", style="cyan")
    col_table.add_column("Type", style="dim")
    col_table.add_column("Non-null", justify="right")
    col_table.add_column("Null", justify="right", style="red")
    col_table.add_column("Unique", justify="right", style="magenta")
    col_table.add_column("Sample", style="dim")

    for col in df.columns:
        non_null = df[col].notna().sum()
        null = df[col].isna().sum()
        unique = df[col].nunique()
        sample_vals = df[col].dropna().astype(str).head(3).tolist()
        sample = ", ".join(sample_vals)
        if len(sample) > 40:
            sample = sample[:37] + "…"
        col_table.add_row(
            col,
            str(df[col].dtype),
            f"{non_null:,}",
            f"{null:,}" if null else "[green]0[/green]",
            f"{unique:,}",
            sample,
        )

    console.print(col_table)

    # ---- Numeric summary ----
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        console.print()
        desc = df[numeric_cols].describe(percentiles=[0.25, 0.5, 0.75] if full else [0.5])
        num_table = Table(title="Numeric Summary", header_style="bold cyan")
        num_table.add_column("Stat", style="cyan")
        for col in desc.columns:
            num_table.add_column(col, justify="right", style="magenta")

        for stat_name in desc.index:
            row_vals = [f"{desc.loc[stat_name, col]:.2f}" for col in desc.columns]
            num_table.add_row(stat_name, *row_vals)

        console.print(num_table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
