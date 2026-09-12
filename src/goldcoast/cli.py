from pathlib import Path
from typing import Annotated

import typer

from goldcoast.data import SeedValidationError, load_seed

app = typer.Typer(no_args_is_help=True, help="Goldcoast dynamic ad-generation workflow.")


@app.command("validate-seed")
def validate_seed(
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir", help="Directory containing seed JSON files."),
    ] = Path("data"),
) -> None:
    try:
        seed = load_seed(data_dir)
    except SeedValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"athletes: {len(seed.athletes)}")
    typer.echo(f"businesses: {len(seed.businesses)}")
    typer.echo(f"ad_styles: {len(seed.ad_styles)}")
    typer.echo(f"venues: {len(seed.venues)}")


def _not_implemented() -> None:
    typer.echo("not implemented", err=True)
    raise typer.Exit(code=1)


@app.command()
def detect(clip: Path) -> None:
    _not_implemented()


@app.command()
def match(moment: Path) -> None:
    _not_implemented()


@app.command()
def generate(brief: Path) -> None:
    _not_implemented()


@app.command()
def judge(ad: Path) -> None:
    _not_implemented()


@app.command()
def run(clip: Path) -> None:
    _not_implemented()
