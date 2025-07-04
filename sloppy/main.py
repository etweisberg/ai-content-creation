#!/usr/bin/env python3
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sloppy.db.script_model import Script, ScriptRepository, ScriptState
from sloppy.script_gen.tasks import generate_news_script

"""
Script/video task management
"""

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
print(f"OPENAI_API_KEY loaded: {'OPENAI_API_KEY' in os.environ}")

script_mongo = ScriptRepository()
if script_mongo.test_connection():
    print("✅☘️ MongoDB Connected Succesfully!")
else:
    print("❌ Failed to Connect")


class TaskManager:
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="task_handler"
        )
        self.futures = []

    def new_script_task(self, choice):
        script_task = generate_news_script.apply_async(args=(choice,))  # type: ignore
        script_obj = Script(id=script_task.id, user_prompt=choice)
        # Submit to thread pool
        future = self.executor.submit(handle_script_task, script_task, script_obj)
        self.futures.append(future)

        return future


def handle_script_task(script_task, script_obj):
    # Create initial script in DB
    script_mongo.create_script(script_obj)

    # Poll task
    while not script_task.ready():
        continue
    script_mongo.update_script(
        script_task.id, {"script": script_task.result, "state": ScriptState.GENERATED}
    )


task_manager = TaskManager()

"""
Terminal UI for task generation
"""

console = Console()


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
    has_submitted = False  # only clear and print menu before our first submission
    while True:
        if not has_submitted:
            clear_screen()

            # Header
            console.print(
                Panel(Text("AI TT Generator", style="bold blue", justify="center"))
            )

            # Submenu
            console.print(
                Panel(
                    f"""Selected: {option}

    b - Back""",
                    title=option,
                )
            )

        choice = input("\nEnter choice: ").strip().lower()
        st = task_manager.new_script_task(choice)

        if choice == "b":
            has_submitted = False
            break
        else:
            has_submitted = True
            console.print(f"\n[blue]Script task submitted!! -- {st}[/blue]")


def main():
    try:
        show_main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user[/red]")


if __name__ == "__main__":
    main()
