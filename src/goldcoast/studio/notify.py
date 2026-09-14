import html
import json
import secrets
import string
import threading
import time
from contextlib import suppress
from datetime import UTC, datetime
from typing import Literal
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

import httpx
from pydantic import AwareDatetime, Field
from sqlalchemy import delete, select

from goldcoast.studio.brand import StrictModel
from goldcoast.studio.creative import CreativeArtifact, CreativeService, DecisionRequest
from goldcoast.studio.database import Controls, Job, Resource, Tenant
from goldcoast.studio.repository import AccessError, Conflict
from goldcoast.studio.workflow import Snapshot, WorkflowStart, start_campaign


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token, transport=None):
        self._token, self.transport = token, transport

    def _call(self, method, payload, files=None, polling=False):
        try:
            timeout = httpx.Timeout(10, read=30 if polling else 10)
            with httpx.Client(timeout=timeout, trust_env=False, transport=self.transport) as client:
                url = "https://api.telegram.org/bot" + self._token + "/" + method
                response = (
                    client.post(url, data=payload, files=files)
                    if files
                    else client.post(url, json=payload)
                )
                response.raise_for_status()
                value = response.json()
                if value.get("ok") is not True:
                    raise TelegramError("Telegram request failed")
                return value["result"]
        except Exception:
            raise TelegramError("Telegram request failed; try a new action in the studio") from None

    def get_updates(self, offset):
        return self._call(
            "getUpdates",
            {"offset": offset, "timeout": 20, "allowed_updates": ["message", "callback_query"]},
            polling=True,
        )

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text[:4096]}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._call("sendMessage", payload)

    def send_photo(self, chat_id, png_bytes, caption, reply_markup):
        if len(caption.encode("utf-16-le")) // 2 > 1024:
            raise TelegramError("Preview caption is too long")
        return self._call(
            "sendPhoto",
            {
                "chat_id": str(chat_id),
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(reply_markup),
            },
            files={"photo": ("creative.png", png_bytes, "image/png")},
        )

    def answer_callback(self, callback_id, text, alert=False):
        return self._call(
            "answerCallbackQuery",
            {"callback_query_id": callback_id, "text": text[:200], "show_alert": alert},
        )

    def edit_reply_markup(self, chat_id, message_id, reply_markup):
        return self._call(
            "editMessageReplyMarkup",
            {"chat_id": chat_id, "message_id": message_id, "reply_markup": reply_markup},
        )

    def edit_caption(self, chat_id, message_id, caption):
        return self._call(
            "editMessageCaption",
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "caption": caption,
                "parse_mode": "HTML",
            },
        )


class PendingPrompt(StrictModel):
    action: Literal["reject", "regenerate"]
    chat_id: int
    prompt_message_id: int
    job_id: str
    creative_id: str | None = None
    version: int | None = None
    photo_message_id: int | None = None
    skip_message_id: int | None = None
    caption: str = ""


class NotificationView(StrictModel):
    channel: Literal["telegram"] = "telegram"
    chat_id: int
    chat_title: str
    linked_at: AwareDatetime
    enabled: bool = True


class NotificationSettings(NotificationView):
    pending: dict[str, PendingPrompt] = Field(default_factory=dict)


class NotificationSave(StrictModel):
    enabled: bool


class TelegramLink(StrictModel):
    code: str = Field(pattern=r"^[A-Za-z0-9]{8}$")
    expires_at: float


class TelegramLinkView(StrictModel):
    code: str
    deep_link: str


class NotificationConfig(StrictModel):
    configured: bool


def escaped(value, limit):
    result = ""
    for character in str(value):
        part = html.escape(character)
        if len((result + part).encode("utf-16-le")) // 2 > limit:
            break
        result += part
    return result


def review_link(settings, job_id):
    return settings.frontend_origin.rstrip("/") + "/#/review/" + job_id


def creative_caption(settings, job, artifact):
    snapshot = Snapshot.model_validate(job.input["snapshot"])
    placement = {
        "post": "Instagram post",
        "story": "Story",
        "landscape": "Landscape",
        "portrait": "Portrait",
    }[artifact.format]
    verdict = artifact.verdict
    signals = job.checkpoint.get("local_signals", {}).get("output", {})
    selected = job.checkpoint.get("campaign", {}).get("output", {}).get("selected", {})
    header = (
        f"<b>{escaped(snapshot.profile.name, 80)}</b> · {placement} · "
        f"{artifact.width}×{artifact.height}\n<b>{escaped(artifact.brief.headline, 100)}</b>\n"
    )
    footer = (
        f"\nJudge: factuality {verdict.factuality} · brand {verdict.brand_fidelity} · "
        f"visual {verdict.visual_quality} · legibility {verdict.legibility}\n"
    )
    if signals.get("summary"):
        footer += "Signal: " + escaped(signals["summary"][0], 180) + " · "
    footer += f"{len(selected.get('source_ids', []))} cited sources\n"
    footer += (
        "Valid until "
        + artifact.expires_at.astimezone(ZoneInfo(snapshot.profile.timezone)).strftime(
            "%b %d, %I:%M %p"
        )
        + "\n"
    )
    footer += "Review in the studio: " + escaped(review_link(settings, job.id), 220) + "\n"
    footer += "Compressed preview; export ZIP contains the full-resolution source."
    remaining = max(0, 920 - len((header + footer).encode("utf-16-le")) // 2)
    return header + escaped(artifact.brief.caption, remaining) + footer


def creative_keyboard(creative_id, version, job_id):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"d:{creative_id}:{version}:approved"},
                {"text": "❌ Reject", "callback_data": f"d:{creative_id}:{version}:rejected"},
            ],
            [{"text": "🔁 Regenerate with a note", "callback_data": "r:" + job_id}],
        ]
    }
    if any(
        len(b["callback_data"].encode()) > 64 for row in keyboard["inline_keyboard"] for b in row
    ):
        raise TelegramError("Creative identifier is too long for Telegram")
    return keyboard


class NotificationService:
    def __init__(self, repo, assets, settings, client=None):
        self.repo, self.assets, self.settings = repo, assets, settings
        self.client = client or TelegramClient(settings.telegram_token)

    @property
    def configured(self):
        return bool(self.settings.telegram_token.strip())

    def _row(self, session, tenant, lock=False):
        query = select(Resource).where(
            Resource.tenant_id == tenant, Resource.kind == "notifications"
        )
        return session.scalar(query.with_for_update() if lock else query)

    def current(self, tenant):
        with self.repo.sessions() as session:
            row = self._row(session, tenant)
            return NotificationSettings.model_validate(row.data) if row else None

    def view(self, tenant):
        current = self.current(tenant)
        return (
            NotificationView.model_validate(current.model_dump(exclude={"pending"}))
            if current
            else None
        )

    def link(self, tenant):
        if not self.configured:
            raise Conflict("Telegram is not configured")
        link = self.settings.telegram_bot_link.rstrip("/")
        if (
            not link.startswith("https://t.me/")
            or any(c in link[13:] for c in "?/# ")
            or len(link) <= 13
        ):
            raise Conflict("Configure telegram_bot_link with the bot's https://t.me link")
        with self.repo.sessions.begin() as session:
            session.execute(
                select(Tenant).where(Tenant.id == tenant).with_for_update()
            ).scalar_one()
            session.execute(
                delete(Resource).where(
                    Resource.tenant_id == tenant, Resource.kind == "telegram_link"
                )
            )
            code = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            session.add(
                Resource(
                    id=uuid5(NAMESPACE_URL, "telegram-link:" + code).hex,
                    tenant_id=tenant,
                    kind="telegram_link",
                    data=TelegramLink(code=code, expires_at=time.time() + 600).model_dump(),
                )
            )
        return TelegramLinkView(code=code, deep_link=link + "?start=" + code)

    def unlink(self, tenant):
        with self.repo.sessions.begin() as session:
            session.execute(
                select(Tenant).where(Tenant.id == tenant).with_for_update()
            ).scalar_one()
            session.execute(
                delete(Resource).where(
                    Resource.tenant_id == tenant,
                    Resource.kind.in_(["notifications", "telegram_link"]),
                )
            )

    def toggle(self, tenant, enabled):
        if not self.configured:
            raise Conflict("Telegram is not configured")
        with self.repo.sessions.begin() as session:
            row = self._row(session, tenant, True)
            if not row:
                raise Conflict("Connect Telegram first")
            value = NotificationSettings.model_validate(row.data)
            value.enabled = enabled
            row.data, row.version = value.model_dump(mode="json"), row.version + 1
        return self.view(tenant)

    def _claim(self, tenant, identity):
        receipt_id = uuid5(NAMESPACE_URL, "telegram-receipt:" + identity).hex
        with self.repo.sessions.begin() as session:
            session.execute(
                select(Tenant).where(Tenant.id == tenant).with_for_update()
            ).scalar_one()
            if session.get(Resource, receipt_id):
                return False
            session.add(
                Resource(
                    id=receipt_id,
                    tenant_id=tenant,
                    kind="telegram_receipt",
                    data={"state": "claimed"},
                )
            )
        return True

    def event(self, tenant, job_id, kind, creative_id=None, **payload):
        with suppress(Exception):
            self.repo.emit(tenant, job_id, kind, {"creative_id": creative_id, **payload})

    def _safe(self, tenant, job_id, method, *args, creative_id=None):
        try:
            return method(*args)
        except Exception:
            self.event(
                tenant, job_id, "notification_failed", creative_id, error="Telegram request failed"
            )
            return None

    def notify_job(self, job, failure=None):
        if not self.configured or job.mode == "replay" or job.kind != "campaign":
            return
        connection = self.current(job.tenant_id)
        if not connection or not connection.enabled:
            return
        if failure is not None:
            if self._claim(job.tenant_id, "failure:" + job.id):
                business = job.input["snapshot"]["profile"]["name"]
                message = self._safe(
                    job.tenant_id,
                    job.id,
                    self.client.send_message,
                    connection.chat_id,
                    f"Today's campaign for {business} stopped: {failure}. Nothing was published. "
                    "Open the studio to see the details.",
                )
                if message:
                    self.event(
                        job.tenant_id, job.id, "notification_sent", message_id=message["message_id"]
                    )
            return
        if job.state != "completed":
            return
        ids = (
            job.checkpoint.get("creative_result", {})
            .get("output", {})
            .get("passing_creative_ids", [])
        )
        for identity in ids[:6]:
            try:
                row = self.repo.get(job.tenant_id, "creative", identity)
                artifact = CreativeArtifact.model_validate(row.data)
                if (
                    artifact.job_id != job.id
                    or not artifact.verdict.passing()
                    or artifact.decision != "pending"
                    or CreativeService(self.repo, self.assets).stale(job.tenant_id, artifact)
                ):
                    continue
                if not self._claim(job.tenant_id, "photo:" + job.id + ":" + identity):
                    continue
                message = self.client.send_photo(
                    connection.chat_id,
                    self.assets.get(job.tenant_id, identity),
                    creative_caption(self.settings, job, artifact),
                    creative_keyboard(identity, row.version, job.id),
                )
                self.event(
                    job.tenant_id,
                    job.id,
                    "notification_sent",
                    identity,
                    message_id=message["message_id"],
                )
            except Exception:
                self.event(
                    job.tenant_id,
                    job.id,
                    "notification_failed",
                    identity,
                    error="Telegram preview could not be sent",
                )
        if len(ids) > 6 and self._claim(job.tenant_id, "summary:" + job.id):
            self._safe(
                job.tenant_id,
                job.id,
                self.client.send_message,
                connection.chat_id,
                f"{len(ids)} passing creatives are ready. Review all in the studio: "
                + review_link(self.settings, job.id),
            )

    def connect(self, message, update_id):
        parts = message.get("text", "").split()
        if len(parts) != 2:
            return
        code = parts[1]
        identity = uuid5(NAMESPACE_URL, "telegram-link:" + code).hex
        business = None
        with self.repo.sessions.begin() as session:
            tenant = session.scalar(
                select(Resource.tenant_id).where(
                    Resource.id == identity, Resource.kind == "telegram_link"
                )
            )
            if tenant:
                session.execute(
                    select(Tenant).where(Tenant.id == tenant).with_for_update()
                ).scalar_one()
            link = session.scalar(
                select(Resource)
                .where(Resource.id == identity, Resource.kind == "telegram_link")
                .with_for_update()
            )
            if link and TelegramLink.model_validate(link.data).expires_at > time.time():
                tenant = link.tenant_id
                value = NotificationSettings(
                    chat_id=message["chat"]["id"],
                    chat_title=str(
                        message.get("from", {}).get("first_name")
                        or message["chat"].get("title")
                        or "Owner"
                    )[:100],
                    linked_at=datetime.now(UTC),
                )
                row = self._row(session, tenant, True)
                if row:
                    row.data, row.version = value.model_dump(mode="json"), row.version + 1
                else:
                    session.add(
                        Resource(
                            tenant_id=tenant,
                            kind="notifications",
                            data=value.model_dump(mode="json"),
                        )
                    )
                profile = session.scalar(
                    select(Resource).where(
                        Resource.tenant_id == tenant, Resource.kind == "business"
                    )
                )
                business = profile.data["name"] if profile else "your business"
                session.delete(link)
        text = (
            f"Connected to {business}. You will get finished creatives here."
            if business
            else "This link expired; open Settings in the studio and connect again."
        )
        self.client.send_message(message["chat"]["id"], text)

    def _pending(self, tenant, prompt, remove=False):
        with self.repo.sessions.begin() as session:
            row = self._row(session, tenant, True)
            if not row:
                raise Conflict("Telegram was disconnected")
            value = NotificationSettings.model_validate(row.data)
            if value.chat_id != prompt.chat_id:
                raise Conflict("Telegram connection changed")
            key = str(prompt.prompt_message_id)
            if remove:
                value.pending.pop(key, None)
            else:
                value.pending[key] = prompt
            row.data, row.version = value.model_dump(mode="json"), row.version + 1

    def _decide(
        self,
        tenant,
        creative_id,
        version,
        decision,
        chat_id,
        message_id,
        caption,
        callback_id=None,
        note="",
    ):
        row = self.repo.get(tenant, "creative", creative_id)
        job_id = row.data["job_id"]
        try:
            CreativeService(self.repo, self.assets).decide(
                tenant,
                creative_id,
                DecisionRequest(version=version, decision=decision, note=note),
                via="telegram",
            )
        except Conflict as exc:
            if callback_id:
                self._safe(tenant, job_id, self.client.answer_callback, callback_id, str(exc), True)
            else:
                self._safe(tenant, job_id, self.client.send_message, chat_id, str(exc))
            self._safe(
                tenant,
                job_id,
                self.client.edit_reply_markup,
                chat_id,
                message_id,
                {"inline_keyboard": []},
            )
            return
        if callback_id:
            self._safe(tenant, job_id, self.client.answer_callback, callback_id, decision.title())
        else:
            self._safe(tenant, job_id, self.client.send_message, chat_id, decision.title())
        self._safe(
            tenant,
            job_id,
            self.client.edit_reply_markup,
            chat_id,
            message_id,
            {"inline_keyboard": []},
        )
        job = self.repo.job(tenant, job_id)
        timezone = job.input["snapshot"]["profile"]["timezone"]
        stamp = datetime.now(ZoneInfo(timezone)).strftime("%b %d, %I:%M %p")
        annotation = (
            f"\n{'✅' if decision == 'approved' else '❌'} {decision.title()} "
            f"on Telegram at {stamp}"
        )
        self._safe(
            tenant,
            job_id,
            self.client.edit_caption,
            chat_id,
            message_id,
            escaped(caption, 900) + annotation,
        )

    def callback(self, query, update_id):
        parts = query.get("data", "").split(":")
        message = query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        if not chat_id or len(parts) not in {2, 4, 5}:
            return
        with self.repo.sessions() as session:
            if parts[0] == "d" and len(parts) in {4, 5}:
                target = session.scalar(
                    select(Resource).where(Resource.id == parts[1], Resource.kind == "creative")
                )
                job_id = target.data["job_id"] if target else None
            elif parts[0] == "r" and len(parts) == 2:
                target = session.get(Job, parts[1])
                job_id = target.id if target and target.kind == "campaign" else None
            else:
                return
            tenant = target.tenant_id if target else None
        connection = self.current(tenant) if tenant else None
        if not job_id or not connection or connection.chat_id != chat_id or not connection.enabled:
            self.client.answer_callback(query["id"], "Not authorized")
            return
        if not self._claim(tenant, "update:" + str(update_id)):
            return
        if parts[0] == "d":
            if not parts[2].isdigit() or parts[3] not in {"approved", "rejected"}:
                return
            version = int(parts[2])
            creative = self.repo.get(tenant, "creative", parts[1])
            artifact = CreativeArtifact.model_validate(creative.data)
            if len(parts) == 4 and (
                creative.version != version
                or artifact.decision != "pending"
                or self.repo.job(tenant, job_id).state != "completed"
                or not artifact.verdict.passing()
                or CreativeService(self.repo, self.assets).stale(tenant, artifact)
            ):
                self._safe(
                    tenant,
                    job_id,
                    self.client.answer_callback,
                    query["id"],
                    "Creative changed or expired; review it in the studio",
                    True,
                )
                self._safe(
                    tenant,
                    job_id,
                    self.client.edit_reply_markup,
                    chat_id,
                    message["message_id"],
                    {"inline_keyboard": []},
                )
                return
            if len(parts) == 5:
                pending = next(
                    (
                        p
                        for p in connection.pending.values()
                        if p.action == "reject"
                        and p.creative_id == parts[1]
                        and p.version == version
                        and p.skip_message_id == message.get("message_id")
                    ),
                    None,
                )
                if parts[4] != "skip" or pending is None:
                    return
                self._decide(
                    tenant,
                    parts[1],
                    version,
                    "rejected",
                    chat_id,
                    pending.photo_message_id,
                    pending.caption,
                    query["id"],
                )
                self._pending(tenant, pending, True)
                self._safe(
                    tenant,
                    job_id,
                    self.client.edit_reply_markup,
                    chat_id,
                    message["message_id"],
                    {"inline_keyboard": []},
                )
                return
            if parts[3] == "approved":
                self._decide(
                    tenant,
                    parts[1],
                    version,
                    "approved",
                    chat_id,
                    message["message_id"],
                    message.get("caption", ""),
                    query["id"],
                )
                return
            action, text = "reject", "Why reject this? Reply with a short reason, or tap Skip."
        else:
            action, text = (
                "regenerate",
                "What should change? Reply in one or two sentences. Uses 1 campaign credit.",
            )
        self._safe(tenant, job_id, self.client.answer_callback, query["id"], "Reply with your note")
        sent = self.client.send_message(chat_id, text, {"force_reply": True, "selective": True})
        pending = PendingPrompt(
            action=action,
            chat_id=chat_id,
            prompt_message_id=sent["message_id"],
            job_id=job_id,
            creative_id=parts[1] if action == "reject" else None,
            version=int(parts[2]) if action == "reject" else None,
            photo_message_id=message["message_id"],
            caption=message.get("caption", ""),
        )
        self._pending(tenant, pending)
        if action == "reject":
            skip = self.client.send_message(
                chat_id,
                "Reject without a reason",
                {"inline_keyboard": [[{"text": "Skip", "callback_data": query["data"] + ":skip"}]]},
            )
            pending.skip_message_id = skip["message_id"]
            self._pending(tenant, pending)

    def reply(self, message, update_id):
        parent = message.get("reply_to_message", {})
        if not parent.get("from", {}).get("is_bot") or not isinstance(message.get("text"), str):
            return
        chat_id = message.get("chat", {}).get("id")
        with self.repo.sessions() as session:
            rows = list(session.scalars(select(Resource).where(Resource.kind == "notifications")))
        for row in rows:
            connection = NotificationSettings.model_validate(row.data)
            pending = connection.pending.get(str(parent.get("message_id")))
            if (
                not pending
                or not connection.enabled
                or connection.chat_id != chat_id
                or pending.chat_id != chat_id
            ):
                continue
            if not self._claim(row.tenant_id, "update:" + str(update_id)):
                return
            note = message["text"].strip()
            if len(note) > 500 or (pending.action == "regenerate" and not note):
                self.client.send_message(chat_id, "Reply with a note between 1 and 500 characters.")
                return
            if pending.action == "reject":
                self._decide(
                    row.tenant_id,
                    pending.creative_id,
                    pending.version,
                    "rejected",
                    chat_id,
                    pending.photo_message_id,
                    pending.caption,
                    note=note,
                )
                if pending.skip_message_id:
                    self._safe(
                        row.tenant_id,
                        pending.job_id,
                        self.client.edit_reply_markup,
                        chat_id,
                        pending.skip_message_id,
                        {"inline_keyboard": []},
                    )
            else:
                try:
                    start_campaign(
                        self.repo,
                        self.assets,
                        row.tenant_id,
                        WorkflowStart(
                            mode="live", regenerate_from=pending.job_id, owner_feedback=note
                        ),
                        key="telegram:" + str(update_id),
                    )
                    left = self.repo.tenant(row.tenant_id).campaign_grants
                    text = (
                        f"Regenerating with your note. Uses 1 campaign credit; {left} left. "
                        "You will get the new version here."
                    )
                except (Conflict, AccessError) as exc:
                    text = str(exc) if isinstance(exc, Conflict) else "Campaign is unavailable"
                self._safe(row.tenant_id, pending.job_id, self.client.send_message, chat_id, text)
            self._pending(row.tenant_id, pending, True)
            return

    def handle(self, update):
        if not self.configured:
            return
        if "callback_query" in update:
            self.callback(update["callback_query"], update["update_id"])
        elif "message" in update:
            message = update["message"]
            if message.get("text", "").split(" ")[0].split("@")[0] == "/start":
                self.connect(message, update["update_id"])
            elif "reply_to_message" in message:
                self.reply(message, update["update_id"])


class TelegramPoller(threading.Thread):
    def __init__(self, service):
        super().__init__(daemon=True, name="telegram-poller")
        self.service = service
        self.stop_event = threading.Event()

    def tick(self):
        if not self.service.configured:
            return
        repo = self.service.repo
        offset = repo.controls().telegram_offset
        updates = self.service.client.get_updates(offset)
        for update in sorted(updates, key=lambda u: u["update_id"]):
            if update["update_id"] < offset:
                continue
            try:
                self.service.handle(update)
            except Exception:
                query = update.get("callback_query", {})
                parts = query.get("data", "").split(":")
                if len(parts) > 1:
                    with repo.sessions() as session:
                        row = (
                            session.get(Job, parts[1])
                            if parts[0] == "r"
                            else session.get(Resource, parts[1])
                        )
                        if row:
                            job_id = row.id if isinstance(row, Job) else row.data.get("job_id")
                            if job_id:
                                self.service.event(
                                    row.tenant_id,
                                    job_id,
                                    "notification_failed",
                                    error="Telegram action could not be completed; use the studio",
                                )
            with repo.sessions.begin() as session:
                controls = session.execute(
                    select(Controls).where(Controls.id == 1).with_for_update()
                ).scalar_one()
                controls.telegram_offset = max(controls.telegram_offset, update["update_id"] + 1)
                offset = controls.telegram_offset

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception:
                self.stop_event.wait(3)

    def stop(self):
        self.stop_event.set()


def notify_finished(repo, assets, job, failure=None):
    from goldcoast.studio.config import StudioSettings

    if job.mode == "replay" or job.kind != "campaign":
        return
    try:
        NotificationService(repo, assets, StudioSettings.from_env()).notify_job(job, failure)
    except Exception:
        with suppress(Exception):
            repo.emit(
                job.tenant_id,
                job.id,
                "notification_failed",
                {"creative_id": None, "error": "Telegram notification unavailable"},
            )
