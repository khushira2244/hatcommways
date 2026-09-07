from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .errors import ValidationError


MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
ALLOWED_EVIDENCE_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class StoredEvidenceFile:
    storage_key: str
    original_filename: str
    content_type: str
    file_size: int


class LocalGovernanceEvidenceStorage:
    """Replaceable local adapter; callers persist only its opaque storage key."""

    def __init__(self, root: Path | None = None) -> None:
        configured = os.environ.get("HATCOMMWAYS_GOVERNANCE_UPLOAD_DIR")
        self.root = (root or Path(configured or "var/governance-evidence")).resolve()

    def save(self, original_filename: str, content_type: str, content: bytes) -> StoredEvidenceFile:
        name = Path(original_filename or "").name.strip()
        if not name or len(name) > 255:
            raise ValidationError("a valid evidence filename is required")
        normalized_type = (content_type or "").lower().split(";", 1)[0].strip()
        expected_extension = ALLOWED_EVIDENCE_TYPES.get(normalized_type)
        extension = Path(name).suffix.lower()
        if normalized_type == "image/jpeg" and extension == ".jpeg":
            extension = ".jpg"
        if expected_extension is None or extension != expected_extension:
            raise ValidationError("evidence must be a PDF, PNG, JPEG, or WebP file")
        if not content:
            raise ValidationError("evidence file must not be empty")
        if len(content) > MAX_EVIDENCE_BYTES:
            raise ValidationError("evidence file must be 10 MiB or smaller")
        signatures = {
            "application/pdf": content.startswith(b"%PDF-"),
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": content.startswith(b"\xff\xd8\xff"),
            "image/webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
        }
        if not signatures[normalized_type]:
            raise ValidationError("evidence file content does not match its declared type")
        self.root.mkdir(parents=True, exist_ok=True)
        key = f"{uuid4().hex}{expected_extension}"
        destination = (self.root / key).resolve()
        if destination.parent != self.root:
            raise ValidationError("invalid evidence storage target")
        destination.write_bytes(content)
        return StoredEvidenceFile(key, name, normalized_type, len(content))

    def delete(self, storage_key: str) -> None:
        target = (self.root / storage_key).resolve()
        if target.parent == self.root:
            target.unlink(missing_ok=True)

    def exists(self, storage_key: str) -> bool:
        target = (self.root / storage_key).resolve()
        return target.parent == self.root and target.is_file()
