import contextlib
import json
import threading
from pathlib import Path

from visavoice.backend.store import JsonStore


def test_read_missing_returns_default(tmp_path):
    store = JsonStore(tmp_path / "x.json", default=[])
    assert store.read() == []


def test_write_then_read(tmp_path):
    store = JsonStore(tmp_path / "x.json", default=[])
    store.write([{"a": 1}])
    assert store.read() == [{"a": 1}]


def test_write_is_atomic(tmp_path, monkeypatch):
    """If write is interrupted between tempfile and rename, the original file survives."""
    path = tmp_path / "x.json"
    JsonStore(path, default=[]).write([{"v": "first"}])

    store = JsonStore(path, default=[])

    def boom(self, target):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(Path, "replace", boom)
    with contextlib.suppress(RuntimeError):
        store.write([{"v": "second"}])

    # Original file intact, no partial write at target
    assert json.loads(path.read_text()) == [{"v": "first"}]


def test_concurrent_writes_do_not_corrupt(tmp_path):
    path = tmp_path / "x.json"
    store = JsonStore(path, default=[])
    store.write([])

    def writer(n):
        for i in range(20):
            current = store.read()
            current.append({"w": n, "i": i})
            store.write(current)

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # May lose writes (last-writer-wins), but file must be valid JSON.
    data = store.read()
    assert isinstance(data, list)
    assert all("w" in d and "i" in d for d in data)
