"""CLI interface for webpage tagging agent."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich import print as rprint

from .agent import analyze_webpage


app = typer.Typer(help="Webpage content tagging agent for read-it-later apps")
console = Console()


@app.command()
def analyze(
    url: str = typer.Argument(..., help="Webpage URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
):
    """Analyze a webpage and generate tags."""
    try:
        with console.status("[bold blue]Fetching and analyzing webpage..."):
            result = asyncio.run(analyze_webpage(url, model))

        console.print("\n[bold green]Analysis Complete![/bold green]\n")
        console.print(result)
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def interactive():
    """Interactive mode - analyze multiple webpages."""
    console.print("[bold blue]Webpage Tagging Agent - Interactive Mode[/bold blue]")
    console.print("Enter webpage URLs (or 'exit' to quit)\n")

    while True:
        try:
            url = typer.prompt("Webpage URL")
            if url.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            with console.status("[bold blue]Fetching and analyzing..."):
                result = asyncio.run(analyze_webpage(url))

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
