#!/usr/bin/env python3
import os

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sloppy.celery_app import app

console = Console()


def get_celery_stats():
    """Get Celery stats"""
    try:
        inspect = app.control.inspect()
        stats = inspect.stats()

        if not stats:
            return "No workers connected"

        worker_count = len(stats.keys())
        return f"Workers: {worker_count} - Connected"
    except Exception:
        return "Celery connection failed"


def clear_screen():
    """Clear the screen"""
    os.system("clear" if os.name == "posix" else "cls")


def show_main_menu():
    """Show main menu and get user choice"""
    while True:
        clear_screen()

        # Header
        console.print(
            Panel(Text("AI TT Generator", style="bold blue", justify="center"))
        )

        # Status
        status_text = get_celery_stats()
        console.print(Panel(Text(status_text, style="green"), title="Celery Status"))

        # Menu
        console.print(
            Panel(
                """1 - Generate Script
2 - Generate Video
q - Quit""",
                title="Main Menu",
            )
        )

        choice = input("\nEnter choice: ").strip().lower()

        if choice == "1":
            show_submenu("Generate Script")
        elif choice == "2":
            show_submenu("Generate Video")
        elif choice == "q":
            console.print("\n[green]Goodbye![/green]")
            break
        else:
            console.print("\n[red]Invalid choice. Press Enter to continue...[/red]")
            input()


def show_submenu(option):
    """Show submenu for selected option"""
    while True:
        clear_screen()

        # Header
        console.print(
            Panel(Text("AI TT Generator", style="bold blue", justify="center"))
        )

        # Status
        status_text = get_celery_stats()
        console.print(Panel(Text(status_text, style="green"), title="Celery Status"))

        # Submenu
        console.print(
            Panel(
                f"""Selected: {option}
[yellow]Feature coming soon![/yellow]

b - Back""",
                title=option,
            )
        )

        choice = input("\nEnter choice: ").strip().lower()

        if choice == "b":
            break
        else:
            console.print(
                "\n[yellow]Feature coming soon! Press Enter to continue...[/yellow]"
            )
            input()
            break


def main():
    try:
        show_main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user[/red]")


if __name__ == "__main__":
    main()
