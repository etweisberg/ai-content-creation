#!/usr/bin/env python3
import os
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sloppy.script_gen.tasks import generate_news_script

console = Console()

"""
Script/video task management
"""


class TaskManager:
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="task_handler"
        )
        self.futures = []

    def new_script_task(self, choice):
        script_task = generate_news_script.apply_async(args=(choice,))

        # Submit to thread pool
        future = self.executor.submit(handle_script_task, script_task)
        self.futures.append(future)

        return future


def handle_script_task(script_task):
    print("--------SCRIPT TASK HANDLING--------")
    print(f"id: {script_task.id}")
    while not script_task.ready():
        continue

    print(f"result: {script_task.result}")


task_manager = TaskManager()

"""
Terminal UI for task generation
"""


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
        st = task_manager.new_script_task(choice)

        if choice == "b":
            break
        else:
            console.print(f"\n[blue]Script task submitted!! -- {st}[/blue]")


def main():
    try:
        show_main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user[/red]")


if __name__ == "__main__":
    main()
