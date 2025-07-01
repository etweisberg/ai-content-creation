#!/usr/bin/env python3
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sloppy.celery_app import app

console = Console()


def get_celery_stats():
    """Get detailed Celery worker and task statistics"""
    try:
        inspect = app.control.inspect()
        stats = inspect.stats()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()

        if not stats:
            return {
                "status": "No workers connected",
                "status_color": "red",
                "workers": 0,
                "active": 0,
                "scheduled": 0,
                "reserved": 0,
                "active_tasks": [],
                "scheduled_tasks": [],
                "reserved_tasks": [],
                "task_totals": {},
            }

        worker_count = len(stats.keys())
        active_count = (
            sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        )
        scheduled_count = (
            sum(len(tasks) for tasks in scheduled_tasks.values())
            if scheduled_tasks
            else 0
        )
        reserved_count = (
            sum(len(tasks) for tasks in reserved_tasks.values())
            if reserved_tasks
            else 0
        )

        # Extract task totals from worker stats
        task_totals = {}
        for _, worker_stats in stats.items():
            total_stats = worker_stats.get("total", {})
            for task_name, count in total_stats.items():
                if task_name not in task_totals:
                    task_totals[task_name] = 0
                task_totals[task_name] += count

        # Flatten task lists for display
        all_active = []
        all_scheduled = []
        all_reserved = []

        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    all_active.append(
                        {
                            "worker": worker,
                            "name": task.get("name", "Unknown"),
                            "id": task.get("id", "Unknown")[:8],
                            "args": str(task.get("args", ""))[:20],
                        }
                    )

        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    all_scheduled.append(
                        {
                            "worker": worker,
                            "name": task.get("request", {}).get("name", "Unknown"),
                            "id": task.get("request", {}).get("id", "Unknown")[:8],
                            "eta": task.get("eta", "Unknown"),
                        }
                    )

        if reserved_tasks:
            for worker, tasks in reserved_tasks.items():
                for task in tasks:
                    all_reserved.append(
                        {
                            "worker": worker,
                            "name": task.get("name", "Unknown"),
                            "id": task.get("id", "Unknown")[:8],
                        }
                    )

        return {
            "status": "Connected",
            "status_color": "green",
            "workers": worker_count,
            "active": active_count,
            "scheduled": scheduled_count,
            "reserved": reserved_count,
            "active_tasks": all_active,
            "scheduled_tasks": all_scheduled,
            "reserved_tasks": all_reserved,
            "task_totals": task_totals,
        }

    except Exception as e:
        return {
            "status": f"Error: {str(e)}",
            "status_color": "red",
            "workers": 0,
            "active": 0,
            "scheduled": 0,
            "reserved": 0,
            "active_tasks": [],
            "scheduled_tasks": [],
            "reserved_tasks": [],
            "task_totals": {},
        }


def create_status_panel(stats):
    """Create the status panel"""
    status_text = Text(f"Status: {stats['status']}", style=stats["status_color"])
    return Panel(status_text, title="Connection Status", border_style="blue")


def create_worker_table(stats):
    """Create the worker statistics table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=15)
    table.add_column("Count", style="green", justify="right")

    table.add_row("Workers", str(stats["workers"]))
    table.add_row("Active Tasks", str(stats["active"]))
    table.add_row("Scheduled Tasks", str(stats["scheduled"]))
    table.add_row("Reserved Tasks", str(stats["reserved"]))

    return Panel(table, title="Worker Stats", border_style="green")


def create_task_totals_table(stats):
    """Create the task totals table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task Name", style="cyan", width=35)
    table.add_column("Total Executed", style="green", justify="right")

    task_totals = stats.get("task_totals", {})
    if not task_totals:
        table.add_row("No tasks executed yet", "0")
    else:
        # Sort by count, highest first
        sorted_tasks = sorted(task_totals.items(), key=lambda x: x[1], reverse=True)
        for task_name, count in sorted_tasks:
            # Truncate long task names
            display_name = task_name
            if len(display_name) > 33:
                display_name = display_name[:30] + "..."
            table.add_row(display_name, str(count))

    return Panel(table, title="Task Execution Totals", border_style="yellow")


def create_active_tasks_table(stats):
    """Create the active tasks table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task", style="cyan", width=25)
    table.add_column("ID", style="yellow", width=10)
    table.add_column("Worker", style="green", width=15)
    table.add_column("Args", style="white", width=15)

    active_tasks = stats.get("active_tasks", [])
    if not active_tasks:
        table.add_row("No active tasks", "-", "-", "-")
    else:
        for task in active_tasks[:10]:  # Limit to 10 most recent
            task_name = task["name"]
            if len(task_name) > 23:
                task_name = task_name[:20] + "..."

            worker_name = (
                task["worker"].split("@")[0]
                if "@" in task["worker"]
                else task["worker"]
            )
            if len(worker_name) > 13:
                worker_name = worker_name[:10] + "..."

            args = task["args"]
            if len(args) > 13:
                args = args[:10] + "..."

            table.add_row(task_name, task["id"], worker_name, args)

    return Panel(table, title="Currently Active Tasks", border_style="red")


def create_info_panel():
    """Create the info panel with controls"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    info_text = f"Last updated: {timestamp}\nPress Ctrl+C to exit"
    return Panel(info_text, title="Info", border_style="yellow")


def create_display():
    """Create the complete display layout"""
    stats = get_celery_stats()

    # Create the main layout
    layout = Layout()

    # Split into 4 sections
    layout.split_column(
        Layout(create_status_panel(stats), name="status", size=3),
        Layout(name="top_row", size=8),
        Layout(name="bottom_row", size=12),
        Layout(create_info_panel(), name="info", size=4),
    )

    # Split the top row
    layout["top_row"].split_row(
        Layout(create_worker_table(stats), name="worker_stats"),
        Layout(create_task_totals_table(stats), name="task_totals"),
    )

    # Bottom row is the active tasks table
    layout["bottom_row"].update(create_active_tasks_table(stats))

    return layout


def main():
    """Main monitoring loop with live updates"""
    try:
        with Live(create_display(), refresh_per_second=10, console=console) as live:
            while True:
                # Update the display
                live.update(create_display())
                time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Celery monitor stopped[/yellow]")


if __name__ == "__main__":
    main()
