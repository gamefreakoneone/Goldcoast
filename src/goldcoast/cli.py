from pathlib import Path
from typing import Annotated
from uuid import uuid4

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
    for warning in seed.warnings:
        typer.echo(f"warning: {warning}", err=True)


def _not_implemented() -> None:
    typer.echo("not implemented", err=True)
    raise typer.Exit(code=1)


@app.command()
def detect(
    clip: Path,
    out: Annotated[Path | None, typer.Option("--out")] = None,
    threshold: Annotated[int | None, typer.Option("--threshold", min=0, max=10)] = None,
    force_analysis: Annotated[bool, typer.Option("--force-analysis")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    import json

    from goldcoast.agents.video_agent import VideoAgent
    from goldcoast.llm.client import GeminiClient
    from goldcoast.llm.recordings import RecordedResponseClient
    from goldcoast.settings import Settings

    try:
        settings = Settings.from_env()
        if threshold is not None:
            settings.hype_threshold = threshold
        destination = out or settings.output_dir / "manual" / f"detect-{uuid4().hex[:8]}"
        if settings.replay:
            if not settings.replay_run:
                raise ValueError("Replay requires GOLDCOAST_REPLAY_RUN")
            client = RecordedResponseClient(
                settings.output_dir / "runs" / settings.replay_run / "model_calls",
                destination / "model_calls",
            )
        else:
            client = GeminiClient(settings, destination / "model_calls")
        agent = VideoAgent(client, settings, destination)
        moments = agent.detect(clip, force=force_analysis)
        typer.echo(json.dumps([m.model_dump(mode="json") for m in moments], indent=2))
        for error in agent.frame_errors:
            typer.echo(error, err=True)
        if agent.frame_errors:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def clips() -> None:
    from goldcoast.models.manifest import ClipManifest
    from goldcoast.settings import Settings

    try:
        manifest = ClipManifest.load(Settings.from_env().clip_manifest)
        typer.echo("clip\tanalyzed\tathlete_id\tbest_frame_s")
        for entry in manifest.entries:
            times = ", ".join(str(m.best_frame_s) for m in entry.moments)
            typer.echo(f"{entry.file}\t{entry.analyzed}\t{entry.athlete_id or '-'}\t{times}")
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


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
