"""CLI interface for YouTube tagging agent."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .agent import analyze_video


app = typer.Typer(help="YouTube video tagging agent for read-it-later apps")
console = Console()


@app.command()
def analyze(
    url: str = typer.Argument(..., help="YouTube video URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
):
    """Analyze a YouTube video and generate tags."""
    try:
        with console.status("[bold blue]Analyzing video..."):
            result = asyncio.run(analyze_video(url, model))

        console.print("\n[bold green]Analysis Complete![/bold green]\n")
        console.print(result)
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


def display_results(result: dict):
    """Display analysis results in a nice table format."""
    console.print("\n[bold green]Analysis Complete![/bold green]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=15)
    table.add_column("Value", style="white")

    if "video_title" in result:
        table.add_row("Title", result["video_title"])

    if "tags" in result:
        tags_str = ", ".join(result["tags"]) if result["tags"] else "No tags generated"
        table.add_row("Tags", tags_str)

    if "summary" in result:
        table.add_row("Summary", result["summary"])

    console.print(table)
    console.print()


@app.command()
def interactive():
    """Interactive mode - analyze multiple videos."""
    console.print("[bold blue]YouTube Tagging Agent - Interactive Mode[/bold blue]")
    console.print("Enter YouTube URLs (or 'exit' to quit)\n")

    while True:
        try:
            url = typer.prompt("YouTube URL")
            if url.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            with console.status("[bold blue]Analyzing..."):
                result = asyncio.run(analyze_video(url))

            console.print("\n[bold green]Analysis:[/bold green]")
            console.print(result)
            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}\n")


if __name__ == "__main__":
    app()
