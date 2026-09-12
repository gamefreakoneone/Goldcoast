from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from goldcoast.agents.ad_agent import AdAgent
from goldcoast.agents.judge_agent import JudgeAgent
from goldcoast.agents.matching_agent import MatchingAgent
from goldcoast.agents.video_agent import VideoAgent
from goldcoast.data import SeedData, load_seed
from goldcoast.llm.recordings import ReplayMissError
from goldcoast.llm.replay import create_client
from goldcoast.models.pipeline import HypeMoment, Run, RunFailure, RunStatus
from goldcoast.models.pipeline import PipelineEventType as E
from goldcoast.pipeline.events import EventBus, EventPersistenceError
from goldcoast.pipeline.ids import child_id
from goldcoast.pipeline.judge_loop import judge_loop
from goldcoast.pipeline.run_store import RunStore
from goldcoast.settings import Settings
from goldcoast.storage import write_bytes, write_json


def copy_tree(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        if path.is_file():
            write_bytes(destination / path.relative_to(source), path.read_bytes())


class Pipeline:
    def __init__(self, settings: Settings, seed: SeedData, run_store: RunStore):
        self.settings, self.seed, self.store = settings, seed, run_store

    def run(
        self,
        clip_path: Path,
        replay_from: str | None = None,
        *,
        run: Run | None = None,
        bus: EventBus | None = None,
    ) -> Run:
        replay_from = replay_from or (self.settings.replay_run if self.settings.replay else None)
        run = run or self.store.create_run(clip_path, bool(replay_from) or self.settings.replay)
        destination = self.store.run_dir(run.id)
        bus = bus or EventBus(destination)
        run.replay_from = replay_from
        run.replay = bool(replay_from) or self.settings.replay
        client = None
        try:
            bus.emit(E.RUN_STARTED, run.model_dump(mode="json"))
            bus.emit(E.CLIP_LOADED, {"clip_path": str(clip_path)})
            settings = self.settings.model_copy()
            source = self.store.run_dir(replay_from) if replay_from else None
            if source:
                original = self.store.get_run(replay_from)
                if original.clip_path.resolve() != clip_path.resolve():
                    raise ValueError("Replay clip must match the source run's clip_path")
                snapshot = source / "settings.json"
                if not snapshot.is_file() or not (source / "seed").is_dir():
                    raise ReplayMissError(f"Missing replay settings/seed snapshot: {source}")
                settings = settings.model_copy(update=json.loads(snapshot.read_text()))
                copy_tree(source / "seed", destination / "seed")
                settings.replay = True
                settings.clip_manifest = destination / "clip_manifest.json"
                if (source / "clip_manifest.json").is_file():
                    write_bytes(
                        settings.clip_manifest, (source / "clip_manifest.json").read_bytes()
                    )
            else:
                copy_tree(settings.data_dir, destination / "seed")
            settings.data_dir = destination / "seed"
            seed = load_seed(settings.data_dir)
            write_json(
                destination / "settings.json",
                settings.model_dump(
                    mode="json",
                    exclude={
                        "gemini_api_key",
                        "data_dir",
                        "output_dir",
                        "clip_manifest",
                        "replay",
                        "replay_run",
                    },
                ),
            )
            client = create_client(settings, destination / "model_calls", source)
            if source:
                moments = self._replay_moments(original, source, run, destination)
                for event in EventBus(source).backlog():
                    if event.type == E.CLIP_MANIFEST_HIT:
                        bus.emit(E.CLIP_MANIFEST_HIT, event.payload)
                        break
            else:
                video = VideoAgent(client, settings, destination)
                moments = video.detect(clip_path)
                if video.manifest_hit:
                    bus.emit(E.CLIP_MANIFEST_HIT, video.manifest_hit.model_dump(mode="json"))
                write_bytes(destination / "clip_manifest.json", settings.clip_manifest.read_bytes())
            run.moment_ids = [m.id for m in moments]
            self.store.save_run(run)
            matching = MatchingAgent(client, seed, settings, destination)
            ads = AdAgent(client, seed, settings, destination)
            judge = JudgeAgent(client, seed, settings, destination)
            for moment in moments:
                bus.emit(E.MOMENT_DETECTED, moment.model_dump(mode="json"))
                if moment.best_frame_path:
                    bus.emit(E.FRAME_EXTRACTED, moment.model_dump(mode="json"))
                try:
                    briefs = matching.match(moment)
                except (ReplayMissError, EventPersistenceError):
                    raise
                except Exception as exc:
                    failure = RunFailure(stage="match", message=str(exc), moment_id=moment.id)
                    run.failures.append(failure)
                    bus.emit(E.MOMENT_SKIPPED, failure.model_dump(mode="json"))
                    continue
                bus.emit(
                    E.ATHLETE_RESOLVED, {**matching.resolved.model_dump(), "moment_id": moment.id}
                )
                for brief in briefs:
                    run.brief_ids.append(brief.id)
                    bus.emit(E.BUSINESS_MATCHED, brief.model_dump(mode="json"))
                    bus.emit(E.BRIEF_CREATED, brief.model_dump(mode="json"))
                    self.store.save_run(run)
                    for fmt in brief.formats:
                        try:
                            result = judge_loop(ads, judge, brief, moment, fmt, bus.emit)
                            run.ad_ids.append(result.final_ad.id)
                            for error in result.errors:
                                run.failures.append(
                                    RunFailure(
                                        stage="generate",
                                        message=error,
                                        brief_id=brief.id,
                                        format=fmt,
                                    )
                                )
                        except (ReplayMissError, EventPersistenceError):
                            raise
                        except Exception as exc:
                            run.failures.append(
                                RunFailure(
                                    stage="ad_failed",
                                    message=str(exc),
                                    moment_id=moment.id,
                                    brief_id=brief.id,
                                    format=fmt,
                                )
                            )
                        self.store.save_run(run)
            if moments and not run.brief_ids:
                raise ValueError("No moment could be matched; see run failures")
            if source is None:
                write_bytes(destination / "clip_manifest.json", settings.clip_manifest.read_bytes())
            run.status = RunStatus.COMPLETED
            run.finished_at = datetime.now(UTC)
            self.store.save_run(run)
            bus.emit(E.RUN_COMPLETED, run.model_dump(mode="json"))
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            run.failures.append(RunFailure(stage="run", message=str(exc)))
            self.store.save_run(run)
            if isinstance(exc, EventPersistenceError):
                raise
            bus.emit(E.RUN_FAILED, {**run.model_dump(mode="json"), "reason": str(exc)})
        finally:
            if client is not None and not client.replay:
                client._client.close()
        return run

    def _replay_moments(
        self, original: Run, source: Path, run: Run, destination: Path
    ) -> list[HypeMoment]:
        moments = []
        for index, identifier in enumerate(original.moment_ids, 1):
            path = source / "moments" / f"{identifier}.json"
            if not path.is_file():
                raise ReplayMissError(f"Missing replay moment: {path}")
            moment = HypeMoment.model_validate_json(path.read_text())
            moment.id = child_id(run.id, "moment", index)
            moment.run_id = run.id
            moment.clip_path = run.clip_path
            if moment.best_frame_path:
                frame = source / "frames" / f"{identifier}.png"
                if not frame.is_file():
                    raise ReplayMissError(f"Missing replay frame: {frame}")
                moment.best_frame_path = destination / "frames" / f"{moment.id}.png"
                write_bytes(moment.best_frame_path, frame.read_bytes())
            write_json(destination / "moments" / f"{moment.id}.json", moment)
            moments.append(moment)
        return moments
