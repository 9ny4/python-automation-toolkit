#!/usr/bin/env python3
"""
organize.py — File Organizer
=============================
Scans a directory and sorts files into subdirectories by type.
Supports dry-run mode to preview changes before applying them.

Usage:
    python organize.py --source ./Downloads
    python organize.py --source ./Downloads --dest ./Sorted --dry-run --verbose
"""

import shutil
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()

# ---------------------------------------------------------------------------
# Extension → category mapping
# ---------------------------------------------------------------------------
CATEGORY_MAP: dict[str, str] = {
    # Images
    "jpg": "Images", "jpeg": "Images", "png": "Images",
    "gif": "Images", "webp": "Images", "bmp": "Images",
    "svg": "Images", "tiff": "Images",
    # Documents
    "pdf": "Documents", "doc": "Documents", "docx": "Documents",
    "txt": "Documents", "xlsx": "Documents", "xls": "Documents",
    "csv": "Documents", "pptx": "Documents", "ppt": "Documents",
    "odt": "Documents", "ods": "Documents", "rtf": "Documents",
    # Videos
    "mp4": "Videos", "mov": "Videos", "avi": "Videos",
    "mkv": "Videos", "wmv": "Videos", "flv": "Videos",
    "webm": "Videos",
    # Audio
    "mp3": "Audio", "wav": "Audio", "flac": "Audio",
    "aac": "Audio", "ogg": "Audio", "m4a": "Audio",
    # Archives
    "zip": "Archives", "tar": "Archives", "gz": "Archives",
    "rar": "Archives", "7z": "Archives", "bz2": "Archives",
    "xz": "Archives",
}


def get_category(file: Path) -> str:
    """Return the target category folder name for a given file."""
    ext = file.suffix.lstrip(".").lower()
    return CATEGORY_MAP.get(ext, "Other")


def configure_logger(verbose: bool, log_file: Optional[Path]) -> None:
    """Configure loguru: console level depends on --verbose flag."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(lambda msg: console.print(msg, end=""), level=level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    if log_file:
        logger.add(str(log_file), level="DEBUG", rotation="1 MB",
                   format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")


@click.command()
@click.option(
    "--source", "-s",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory to scan for files.",
)
@click.option(
    "--dest", "-d",
    default=None,
    type=click.Path(file_okay=False, path_type=Path),
    help="Destination root for organized files. Defaults to --source.",
)
@click.option(
    "--dry-run", "-n",
    is_flag=True,
    default=False,
    help="Preview what would happen without moving any files.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging.",
)
@click.option(
    "--log-file",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional path to write a log file.",
)
def main(
    source: Path,
    dest: Optional[Path],
    dry_run: bool,
    verbose: bool,
    log_file: Optional[Path],
) -> None:
    """Organize files in SOURCE into categorized subdirectories.

    Files are moved into: Images/, Documents/, Videos/, Audio/, Archives/, Other/

    Example:
        python organize.py --source ~/Downloads --dry-run
    """
    configure_logger(verbose, log_file)

    destination = dest or source
    destination = destination.resolve()
    source = source.resolve()

    if dry_run:
        console.rule("[bold yellow]DRY RUN — no files will be moved[/bold yellow]")

    logger.info(f"Source      : {source}")
    logger.info(f"Destination : {destination}")
    logger.debug(f"Dry run     : {dry_run}")

    # Collect only top-level files (non-recursive)
    files = [f for f in source.iterdir() if f.is_file()]

    if not files:
        console.print("[yellow]No files found in source directory.[/yellow]")
        return

    summary: dict[str, list[Path]] = {}
    errors: list[tuple[Path, str]] = []

    for file in files:
        category = get_category(file)
        target_dir = destination / category
        target_path = target_dir / file.name

        logger.debug(f"{file.name!r}  →  {category}/")

        if not dry_run:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)

                # Handle name collisions: append a counter
                counter = 1
                while target_path.exists():
                    stem = file.stem
                    suffix = file.suffix
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                shutil.move(str(file), str(target_path))
                logger.info(f"Moved  {file.name!r}  →  {category}/{target_path.name}")
            except OSError as exc:
                logger.error(f"Failed to move {file.name!r}: {exc}")
                errors.append((file, str(exc)))
                continue

        summary.setdefault(category, []).append(file)

    # -----------------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------------
    table = Table(title="Organizer Summary", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Files", justify="right", style="magenta")
    table.add_column("Sample", style="dim")

    total = 0
    for category, moved in sorted(summary.items()):
        sample = ", ".join(f.name for f in moved[:3])
        if len(moved) > 3:
            sample += f" … (+{len(moved) - 3} more)"
        table.add_row(category, str(len(moved)), sample)
        total += len(moved)

    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]", "")

    console.print()
    console.print(table)

    if errors:
        console.print(f"\n[red]Errors: {len(errors)} file(s) could not be moved.[/red]")
        for path, msg in errors:
            console.print(f"  [red]✗[/red] {path.name}: {msg}")

    if dry_run:
        console.print("\n[yellow]Dry run complete — rerun without --dry-run to apply.[/yellow]")
    else:
        console.print(f"\n[green]Done.[/green] {total} file(s) organized into {destination}")


if __name__ == "__main__":
    main()
