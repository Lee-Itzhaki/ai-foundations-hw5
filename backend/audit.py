"""Append-only audit trail at output/audit_trail.json.

The file is a JSON array. Each append re-reads the existing array, adds one
entry, and atomically replaces the file, so earlier runs are never erased.
If the existing file is not a valid JSON array the append is refused rather
than overwriting it.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

from .config import AUDIT_PATH
from .models import AuditEntry

_SECRET_KEY = re.compile(r"(api[_-]?key|token|secret|password|authorization|credential)", re.I)
_SECRET_VALUE = re.compile(r"(sk-[A-Za-z0-9]{8,}|pk-[A-Za-z0-9]{8,})")
_MAX_SUMMARY = 400


class AuditTrailCorrupt(RuntimeError):
    pass


def redact(value: Any) -> Any:
    """Drop secret-looking keys and mask secret-looking strings."""
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if _SECRET_KEY.search(str(k)) else redact(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return value


def summarize(value: Any) -> str:
    """Concise, redacted, single-line summary of a tool result."""
    text = json.dumps(redact(value), default=str, separators=(",", ":"))
    return text if len(text) <= _MAX_SUMMARY else text[: _MAX_SUMMARY - 3] + "..."


class AuditTrail:
    def __init__(self, path: Path = AUDIT_PATH):
        self.path = path
        self._lock = threading.Lock()

    def append(self, entry: AuditEntry) -> None:
        record = redact(entry.model_dump(mode="json", exclude_none=True))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(".lock")
        with self._lock, open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            entries = self._read_existing()
            entries.append(record)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(entries, f, indent=2)
                f.write("\n")
            os.replace(tmp, self.path)

    def _read_existing(self) -> list[dict[str, Any]]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        try:
            data = json.loads(self.path.read_text())
        except json.JSONDecodeError as exc:
            raise AuditTrailCorrupt(f"{self.path} is not valid JSON; refusing to overwrite.") from exc
        if not isinstance(data, list):
            raise AuditTrailCorrupt(f"{self.path} is not a JSON array; refusing to overwrite.")
        return data
