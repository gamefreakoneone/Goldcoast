from datetime import UTC, datetime
from uuid import uuid4


def run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:6]


def child_id(parent: str, kind: str, sequence: int) -> str:
    return f"{parent}-{kind}-{sequence}"
