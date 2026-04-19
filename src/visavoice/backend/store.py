import json
import os
import tempfile
from pathlib import Path
from typing import Any


class JsonStore:
    """Atomic-write JSON file store. Writes via tempfile + rename."""

    def __init__(self, path: Path, default: Any):
        self.path = Path(path)
        self._default = default
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> Any:
        if not self.path.exists():
            return self._default
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, value: Any) -> None:
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(value, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp_path.replace(self.path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise
