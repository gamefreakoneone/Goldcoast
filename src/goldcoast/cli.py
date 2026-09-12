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
def match(
    moment: Path,
    out: Annotated[Path | None, typer.Option("--out")] = None,
    max_businesses: Annotated[int | None, typer.Option("--max-businesses", min=1)] = None,
) -> None:
    import json

    from goldcoast.agents.matching_agent import MatchingAgent
    from goldcoast.llm.client import GeminiClient
    from goldcoast.llm.recordings import RecordedResponseClient
    from goldcoast.models.pipeline import HypeMoment
    from goldcoast.settings import Settings

    try:
        settings = Settings.from_env()
        if max_businesses is not None:
            settings.max_businesses = max_businesses
        destination = out or settings.output_dir / "manual" / f"match-{uuid4().hex[:8]}"
        if settings.replay:
            if not settings.replay_run:
                raise ValueError("Replay requires GOLDCOAST_REPLAY_RUN")
            client = RecordedResponseClient(
                settings.output_dir / "runs" / settings.replay_run / "model_calls",
                destination / "model_calls",
            )
        else:
            client = GeminiClient(settings, destination / "model_calls")
        value = HypeMoment.model_validate_json(moment.read_text(encoding="utf-8"))
        briefs = MatchingAgent(client, load_seed(settings.data_dir), settings, destination).match(
            value
        )
        typer.echo(json.dumps([b.model_dump(mode="json") for b in briefs], indent=2))
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _stage_client(settings, destination):
    from goldcoast.llm.client import GeminiClient
    from goldcoast.llm.recordings import RecordedResponseClient

    if settings.replay:
        if not settings.replay_run:
            raise ValueError("Replay requires GOLDCOAST_REPLAY_RUN")
        return RecordedResponseClient(
            settings.output_dir / "runs" / settings.replay_run / "model_calls",
            destination / "model_calls",
        )
    return GeminiClient(settings, destination / "model_calls")


@app.command()
def generate(
    brief: Path,
    moment: Annotated[Path, typer.Option("--moment")],
    out: Annotated[Path | None, typer.Option("--out")] = None,
    format: Annotated[str | None, typer.Option("--format")] = None,
    attempt: Annotated[int, typer.Option("--attempt", min=1)] = 1,
    hint: Annotated[list[str] | None, typer.Option("--hint")] = None,
) -> None:
    import json

    from goldcoast.agents.ad_agent import AdAgent
    from goldcoast.models.pipeline import AdBrief, AdFormat, HypeMoment
    from goldcoast.settings import Settings

    try:
        settings = Settings.from_env()
        destination = out or settings.output_dir / "manual" / f"generate-{uuid4().hex[:8]}"
        value = AdBrief.model_validate_json(brief.read_text(encoding="utf-8"))
        context = HypeMoment.model_validate_json(moment.read_text(encoding="utf-8"))
        agent = AdAgent(
            _stage_client(settings, destination),
            load_seed(settings.data_dir),
            settings,
            destination,
        )
        if format:
            ads = [agent.generate_one(value, context, AdFormat(format), attempt, hint)]
        else:
            ads = agent.generate(value, context, attempt, hint)
        typer.echo(json.dumps([ad.model_dump(mode="json") for ad in ads], indent=2))
        if agent.errors:
            raise ValueError("; ".join(agent.errors))
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def judge(
    ad: Path,
    brief: Annotated[Path, typer.Option("--brief")],
    moment: Annotated[Path, typer.Option("--moment")],
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    from goldcoast.agents.judge_agent import JudgeAgent
    from goldcoast.models.pipeline import AdBrief, GeneratedAd, HypeMoment
    from goldcoast.settings import Settings

    try:
        settings = Settings.from_env()
        destination = out or settings.output_dir / "manual" / f"judge-{uuid4().hex[:8]}"
        agent = JudgeAgent(
            _stage_client(settings, destination),
            load_seed(settings.data_dir),
            settings,
            destination,
        )
        result = agent.judge(
            GeneratedAd.model_validate_json(ad.read_text(encoding="utf-8")),
            AdBrief.model_validate_json(brief.read_text(encoding="utf-8")),
            HypeMoment.model_validate_json(moment.read_text(encoding="utf-8")),
        )
        typer.echo(result.model_dump_json(indent=2))
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("judge-loop")
def judge_loop_command(
    brief: Annotated[Path, typer.Option("--brief")],
    moment: Annotated[Path, typer.Option("--moment")],
    format: Annotated[str, typer.Option("--format")],
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    from goldcoast.agents.ad_agent import AdAgent
    from goldcoast.agents.judge_agent import JudgeAgent
    from goldcoast.models.pipeline import AdBrief, AdFormat, HypeMoment
    from goldcoast.pipeline.judge_loop import judge_loop
    from goldcoast.settings import Settings

    try:
        settings = Settings.from_env()
        destination = out or settings.output_dir / "manual" / f"judge-loop-{uuid4().hex[:8]}"
        client = _stage_client(settings, destination)
        seed = load_seed(settings.data_dir)
        result = judge_loop(
            AdAgent(client, seed, settings, destination),
            JudgeAgent(client, seed, settings, destination),
            AdBrief.model_validate_json(brief.read_text(encoding="utf-8")),
            HypeMoment.model_validate_json(moment.read_text(encoding="utf-8")),
            AdFormat(format),
        )
        typer.echo(result.model_dump_json(indent=2))
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def run(
    clip: Path, replay_from: Annotated[str | None, typer.Option("--replay-from")] = None
) -> None:
    from goldcoast.pipeline.orchestrator import Pipeline
    from goldcoast.pipeline.run_store import RunStore
    from goldcoast.settings import Settings

    try:
        settings = Settings.from_env()
        result = Pipeline(
            settings, load_seed(settings.data_dir), RunStore(settings.output_dir)
        ).run(clip, replay_from)
        typer.echo(result.model_dump_json(indent=2))
        if result.status == "failed":
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def runs() -> None:
    from goldcoast.pipeline.run_store import RunStore
    from goldcoast.settings import Settings

    for run in RunStore(Settings.from_env().output_dir).list_runs():
        typer.echo(
            f"{run.id}\t{run.status}\tmoments={len(run.moment_ids)} "
            f"briefs={len(run.brief_ids)} ads={len(run.ad_ids)} "
            f"failures={len(run.failures)} replay={run.replay}"
        )
