"""Agent Spike CLI entrypoint."""

import typer

app = typer.Typer()


@app.command()
def hello(name: str = typer.Option("World", help="Name to greet")) -> None:
    """Greet someone."""
    typer.echo(f"Hello, {name}!")


if __name__ == "__main__":
    app()
