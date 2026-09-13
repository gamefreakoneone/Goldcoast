def job_view(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "mode": row.mode,
        "state": row.state,
        "input": row.input,
        "checkpoint": row.checkpoint,
        "counters": row.counters,
        "created_at": row.created_at,
        "finished_at": row.finished_at,
    }
