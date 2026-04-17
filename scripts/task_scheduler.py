#!/usr/bin/env python3
"""
task_scheduler.py — Pure-Python Task Scheduler
==============================================
Run scheduled shell commands using a JSON config and the `schedule` library.

Usage:
    python scripts/task_scheduler.py list
    python scripts/task_scheduler.py run
    python scripts/task_scheduler.py run-once daily_backup
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import click
import schedule
from loguru import logger
from rich.console import Console
from rich.table import Table

console = Console()

DAYS = {
    "monday": schedule.every().monday,
    "tuesday": schedule.every().tuesday,
    "wednesday": schedule.every().wednesday,
    "thursday": schedule.every().thursday,
    "friday": schedule.every().friday,
    "saturday": schedule.every().saturday,
    "sunday": schedule.every().sunday,
}


@dataclass
class Task:
    """A scheduled task entry."""

    name: str
    command: str
    schedule: str
    time: str | None = None
    day: str | None = None


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


def load_config(path: Path) -> list[Task]:
    """Load tasks from a JSON config file."""
    if not path.exists():
        console.print(f"[red]Error:[/red] Config file not found: {path}")
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] Invalid JSON: {exc}")
        sys.exit(1)

    tasks = []
    for item in data.get("tasks", []):
        tasks.append(
            Task(
                name=item.get("name", ""),
                command=item.get("command", ""),
                schedule=item.get("schedule", ""),
                time=item.get("time"),
                day=item.get("day"),
            )
        )
    return tasks


def run_command(task: Task) -> int:
    """Run a task's command and return its exit code."""
    start = datetime.now()
    logger.info(f"Running {task.name!r}: {task.command}")

    try:
        completed = subprocess.run(
            task.command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to execute {task.name!r}: {exc}")
        return 1

    duration = (datetime.now() - start).total_seconds()
    if completed.stdout:
        logger.debug(f"stdout:\n{completed.stdout.strip()}")
    if completed.stderr:
        logger.warning(f"stderr:\n{completed.stderr.strip()}")

    logger.info(
        f"Finished {task.name!r} with exit code {completed.returncode} in {duration:.1f}s"
    )
    return completed.returncode


def schedule_task(task: Task) -> None:
    """Register a task with the schedule library."""
    schedule_type = task.schedule.strip().lower()

    if schedule_type == "hourly":
        schedule.every().hour.do(run_command, task)
        return

    if schedule_type == "daily":
        if task.time:
            schedule.every().day.at(task.time).do(run_command, task)
        else:
            schedule.every().day.do(run_command, task)
        return

    if schedule_type == "weekly":
        if task.day:
            day_key = task.day.strip().lower()
            if day_key not in DAYS:
                raise ValueError(f"Invalid day: {task.day}")
            job = DAYS[day_key]
        else:
            job = schedule.every().week

        if task.time:
            job.at(task.time).do(run_command, task)
        else:
            job.do(run_command, task)
        return

    if schedule_type.startswith("every_") and schedule_type.endswith("_minutes"):
        try:
            minutes = int(schedule_type.replace("every_", "").replace("_minutes", ""))
        except ValueError as exc:
            raise ValueError(f"Invalid schedule format: {task.schedule}") from exc
        schedule.every(minutes).minutes.do(run_command, task)
        return

    raise ValueError(
        "Unsupported schedule. Use hourly, daily, weekly, or every_N_minutes."
    )


def validate_tasks(tasks: Iterable[Task]) -> list[Task]:
    """Validate tasks and filter out invalid entries."""
    valid = []
    for task in tasks:
        if not task.name or not task.command or not task.schedule:
            logger.warning(f"Skipping invalid task entry: {task}")
            continue
        valid.append(task)
    return valid


def render_task_table(tasks: Iterable[Task]) -> None:
    """Print a table of tasks."""
    table = Table(title="Scheduled Tasks", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Schedule")
    table.add_column("Time")
    table.add_column("Day")
    table.add_column("Command")

    for task in tasks:
        table.add_row(
            task.name,
            task.schedule,
            task.time or "-",
            task.day or "-",
            task.command,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.version_option("1.0.0", prog_name="task-scheduler")
@click.option(
    "--config",
    "-c",
    default=Path("scheduler_config.json"),
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    show_default=True,
    help="Path to scheduler config JSON.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
@click.pass_context
def cli(ctx: click.Context, config: Path, verbose: bool) -> None:
    """Task Scheduler — run commands on a schedule."""
    configure_logger(verbose)
    ctx.obj = {"config": config}


@cli.command("list")
@click.pass_context
def list_tasks(ctx: click.Context) -> None:
    """List all scheduled tasks."""
    tasks = validate_tasks(load_config(ctx.obj["config"]))
    if not tasks:
        console.print("[yellow]No tasks found in config.[/yellow]")
        return
    render_task_table(tasks)


@cli.command("run")
@click.pass_context
def run_scheduler(ctx: click.Context) -> None:
    """Start the scheduler loop (long-running)."""
    tasks = validate_tasks(load_config(ctx.obj["config"]))
    if not tasks:
        console.print("[red]No valid tasks found. Exiting.[/red]")
        sys.exit(1)

    for task in tasks:
        try:
            schedule_task(task)
            logger.info(f"Scheduled {task.name!r} ({task.schedule})")
        except ValueError as exc:
            logger.error(f"Skipping {task.name!r}: {exc}")

    console.print("[green]Scheduler started. Press Ctrl+C to stop.[/green]")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("[yellow]Scheduler stopped.[/yellow]")


@cli.command("run-once")
@click.argument("task_name")
@click.pass_context
def run_once(ctx: click.Context, task_name: str) -> None:
    """Run a task immediately by name."""
    tasks = validate_tasks(load_config(ctx.obj["config"]))
    for task in tasks:
        if task.name == task_name:
            code = run_command(task)
            sys.exit(code)

    console.print(f"[red]Task not found:[/red] {task_name}")
    sys.exit(1)


if __name__ == "__main__":
    cli()
