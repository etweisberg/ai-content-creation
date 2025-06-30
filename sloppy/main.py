#!/usr/bin/env python3
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from sloppy.celery_app import app

console = Console()


def create_header():
    """Create the beautiful header"""
    header_text = Text("AI TT Generator", style="bold magenta", justify="center")
    header_text.stylize("bold cyan", 0, 2)
    header_text.stylize("bold yellow", 3, 5)
    header_text.stylize("bold green", 6, 15)
    return Panel(header_text, border_style="bright_blue", padding=(1, 2))


def get_celery_stats():
    """Get Celery worker and queue statistics"""
    try:
        inspect = app.control.inspect()
        stats = inspect.stats()
        active_tasks = inspect.active()

        if not stats:
            return "No workers available", "No active tasks"

        worker_count = len(stats.keys())
        active_count = (
            sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        )

        return f"Workers: {worker_count}", f"Active Tasks: {active_count}"
    except Exception as e:
        return "Connection Error", str(e)


def create_status_panel():
    """Create status panel with Celery info"""
    worker_info, task_info = get_celery_stats()

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Status", "Running")
    table.add_row(
        "Workers", worker_info.split(": ")[1] if ": " in worker_info else worker_info
    )
    table.add_row(
        "Active Tasks", task_info.split(": ")[1] if ": " in task_info else task_info
    )

    return Panel(table, title="Celery Status", border_style="green")


def create_menu():
    """Create the main menu"""
    menu_table = Table(show_header=False, box=None, padding=(0, 2))
    menu_table.add_column("Option", style="bold white")
    menu_table.add_column("Description", style="dim white")

    menu_table.add_row("1", "Generate Script")
    menu_table.add_row("2", "Generate Video")
    menu_table.add_row("q", "Quit")

    return Panel(menu_table, title="Main Menu", border_style="blue")


def main():
    """Main TUI loop"""
    while True:
        console.clear()

        # Display header
        console.print(create_header())
        console.print()

        # Display status
        console.print(create_status_panel())
        console.print()

        # Display menu
        console.print(create_menu())
        console.print()

        # Get user choice
        choice = Prompt.ask("Select an option", choices=["1", "2", "q"], default="q")

        if choice == "1":
            console.print(
                "[yellow]Generate Script selected - Feature coming soon![/yellow]"
            )
            console.input("Press Enter to continue...")
        elif choice == "2":
            console.print(
                "[yellow]Generate Video selected - Feature coming soon![/yellow]"
            )
            console.input("Press Enter to continue...")
        elif choice == "q":
            console.print("[green]Goodbye![/green]")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
