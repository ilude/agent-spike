"""CLI interface for the multi-agent coordinator."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .agent import analyze_url, analyze_urls_batch
from .router import URLRouter, URLType


app = typer.Typer(help="Multi-agent coordinator - routes URLs to specialized agents")
console = Console()


@app.command()
def analyze(
    url: str = typer.Argument(..., help="URL to analyze (YouTube video or webpage)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
):
    """Analyze any URL by automatically routing to the appropriate agent."""
    try:
        # Classify URL first
        url_type = URLRouter.classify_url(url)

        if url_type == URLType.INVALID:
            console.print(f"[bold red]Error:[/bold red] Invalid URL: {url}")
            raise typer.Exit(1)

        # Show routing info
        handler = URLRouter.get_handler_name(url_type)
        console.print(f"[cyan]URL Type:[/cyan] {url_type.value}")
        console.print(f"[cyan]Handler:[/cyan] {handler}\n")

        # Process the URL
        with console.status(f"[bold blue]Analyzing with {handler}..."):
            result = asyncio.run(analyze_url(url, model))

        # Display results
        if result.error:
            console.print(f"[bold red]Error:[/bold red] {result.error}")
            raise typer.Exit(1)

        console.print("\n[bold green]Analysis Complete![/bold green]\n")
        console.print(result.result)
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def interactive():
    """Interactive mode - analyze multiple URLs of any type."""
    console.print("[bold blue]Multi-Agent Coordinator - Interactive Mode[/bold blue]")
    console.print("Enter any URL - YouTube videos or webpages (or 'exit' to quit)\n")

    while True:
        try:
            url = typer.prompt("URL")
            if url.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            # Classify and display routing info
            url_type = URLRouter.classify_url(url)
            if url_type == URLType.INVALID:
                console.print(f"[bold red]Invalid URL:[/bold red] {url}\n")
                continue

            handler = URLRouter.get_handler_name(url_type)
            console.print(f"[dim]→ Routing to {handler}...[/dim]")

            # Analyze
            with console.status("[bold blue]Analyzing..."):
                result = asyncio.run(analyze_url(url))

            # Display results
            if result.error:
                console.print(f"[bold red]Error:[/bold red] {result.error}\n")
            else:
                console.print("\n[bold green]Analysis:[/bold green]")
                console.print(result.result)
                console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}\n")


@app.command()
def batch(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
):
    """Batch mode - analyze multiple URLs from stdin."""
    console.print("[bold blue]Multi-Agent Coordinator - Batch Mode[/bold blue]")
    console.print("Enter URLs (one per line), then press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:\n")

    urls = []
    try:
        while True:
            line = input()
            if line.strip():
                urls.append(line.strip())
    except EOFError:
        pass

    if not urls:
        console.print("[yellow]No URLs provided[/yellow]")
        return

    console.print(f"\n[cyan]Processing {len(urls)} URLs...[/cyan]\n")

    with console.status("[bold blue]Analyzing URLs..."):
        results = asyncio.run(analyze_urls_batch(urls, model))

    # Display all results
    console.print("\n[bold green]Batch Analysis Complete![/bold green]\n")

    for i, result in enumerate(results, 1):
        console.print(f"[bold cyan]Result {i}/{len(results)}:[/bold cyan]")
        if result.error:
            console.print(f"[bold red]Error:[/bold red] {result.error}")
        else:
            console.print(f"URL: {result.url}")
            console.print(f"Handler: {result.handler}")
            console.print(result.result)
        console.print()


@app.command()
def test():
    """Test the router with sample URLs."""
    test_urls = [
        ("https://www.youtube.com/watch?v=i5kwX7jeWL8", URLType.YOUTUBE),
        ("https://youtu.be/i5kwX7jeWL8", URLType.YOUTUBE),
        ("https://github.com/docling-project/docling", URLType.WEBPAGE),
        ("https://example.com", URLType.WEBPAGE),
        ("not-a-url", URLType.INVALID),
        ("", URLType.INVALID),
    ]

    console.print("[bold blue]Testing URL Router[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("URL", style="cyan", width=50)
    table.add_column("Expected", style="white", width=12)
    table.add_column("Actual", style="white", width=12)
    table.add_column("Status", style="white", width=10)

    for url, expected in test_urls:
        actual = URLRouter.classify_url(url)
        status = "✓" if actual == expected else "✗"
        status_color = "green" if actual == expected else "red"

        table.add_row(
            url if url else "(empty)",
            expected.value,
            actual.value,
            f"[{status_color}]{status}[/{status_color}]",
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
