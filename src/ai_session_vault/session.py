"""Session model and JSONL parsing.

Sessions are JSONL files where each line is one JSON record. We treat the
format tolerance as a first-class concern: agent runtimes write different
shapes, so all parsing here must degrade gracefully on malformed input.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

SESSION_ID_FIELDS = ("sessionId", "session_id", "uuid", "conversationId")


def iter_records(path: Path) -> Iterator[dict[str, Any]]:
    """Yield each JSON object found on a line of a JSONL file.

    Malformed lines are skipped silently; empty lines are ignored.
    """
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of the raw file bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def turn_count(path: Path) -> int:
    """Count message-bearing records in a session file.

    A record counts as a turn if it has a ``message`` key with a ``role``,
    or a top-level ``role`` field. Malformed lines never count.
    """
    count = 0
    for record in iter_records(path):
        message = record.get("message")
        if isinstance(message, dict) and message.get("role"):
            count += 1
        elif record.get("role"):
            count += 1
    return count


def derive_session_id(path: Path, session_id_field: str | None, first_uuid: str | None) -> str:
    """Calculate a stable, short session identifier.

    Priority: the session UUID found inside the file, then the filename
    (minus extension), then a digest of the absolute path. The result is
    sanitised to a safe slug.
    """
    candidate = first_uuid or session_id_field
    if candidate:
        slug = re.sub(r"[^a-zA-Z0-9._-]", "-", candidate)
        return slug[:24] or slug
    base = path.stem
    slug = re.sub(r"[^a-zA-Z0-9._-]", "-", base)
    if slug:
        return slug[:24]
    return hashlib.sha256(str(path.absolute()).encode("utf-8")).hexdigest()[:12]


def _first_identifiers(path: Path) -> tuple[str | None, str | None]:
    """Return (session_id_field, uuid_from_first_record) without a full parse."""
    session_field: str | None = None
    first_uuid: str | None = None
    for record in iter_records(path):
        if session_field is None:
            for key in SESSION_ID_FIELDS:
                value = record.get(key)
                if isinstance(value, str) and value:
                    session_field = value
                    break
            if first_uuid is None:
                first_uuid = session_field
        if session_field is not None and first_uuid is not None:
            break
    return session_field, first_uuid


def session_meta(path: Path, runtime: str, session_id: str) -> dict[str, Any]:
    """Build a metadata sidecar dict for a session file."""
    turns = turn_count(path)
    return {
        "runtime": runtime,
        "session_id": session_id,
        "turns": turns,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "source": str(path.absolute()),
        "mtime": int(path.stat().st_mtime),
    }


@dataclass(frozen=True)
class IdentifiedSession:
    """A session file together with its calculated identifier."""

    path: Path
    runtime: str
    session_id: str

    @classmethod
    def from_file(cls, path: Path, runtime: str) -> "IdentifiedSession":
        field, uuid_ = _first_identifiers(path)
        return cls(
            path=path,
            runtime=runtime,
            session_id=derive_session_id(path, field, uuid_),
        )

    @property
    def filename(self) -> str:
        return f"{self.session_id}.jsonl"

    def meta(self) -> dict[str, Any]:
        return session_meta(self.path, self.runtime, self.session_id)