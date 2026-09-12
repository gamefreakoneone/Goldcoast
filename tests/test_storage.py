import os

import pytest

from goldcoast.storage import write_bytes


def test_atomic_write_retries_windows_sharing(tmp_path, monkeypatch):
    path = tmp_path / "run.json"
    path.write_bytes(b"old")
    original = os.replace
    calls = 0

    def sharing_once(source, target):
        nonlocal calls
        calls += 1
        if calls == 1:
            assert path.read_bytes() == b"old"
            error = PermissionError("Windows reader holds file open")
            error.winerror = 5
            raise error
        original(source, target)

    monkeypatch.setattr(os, "replace", sharing_once)
    write_bytes(path, b"new")
    assert calls == 2
    assert path.read_bytes() == b"new"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_write_sharing_retry_is_bounded(tmp_path, monkeypatch):
    path = tmp_path / "run.json"
    path.write_bytes(b"old")
    calls = 0

    def denied(source, target):
        nonlocal calls
        calls += 1
        error = PermissionError("Persistent sharing violation")
        error.winerror = 32
        raise error

    monkeypatch.setattr(os, "replace", denied)
    with pytest.raises(PermissionError):
        write_bytes(path, b"new")
    assert calls == 6
    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]
