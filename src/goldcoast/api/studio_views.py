def started_via(row):
    value = row.input.get("started_via")
    if value in {"studio", "telegram"}:
        return value
    return (
        "telegram" if row.request_key.startswith(("telegram:", "telegram-campaign:")) else "studio"
    )


def job_view(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "mode": row.mode,
        "state": row.state,
        "started_via": started_via(row),
        "input": row.input,
        "checkpoint": row.checkpoint,
        "counters": row.counters,
        "created_at": row.created_at,
        "finished_at": row.finished_at,
    }
