from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from typing import Any


@dataclass(slots=True)
class StoredBlobRef:
    blob_id: str
    blob_object_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


@dataclass(slots=True)
class StoredBlob:
    blob_id: str
    blob_object_id: str
    payload: bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


class EvidenceStore(ABC):
    @abstractmethod
    def put_encrypted_blob(self, blob_bytes: bytes, metadata: dict[str, Any]) -> StoredBlobRef:
        """Persist encrypted evidence and return its durable ID."""

    @abstractmethod
    def delete_blob(self, blob_id: str) -> bool:
        """Delete a stored blob if it exists."""


class InMemoryEvidenceStore(EvidenceStore):
    def __init__(self) -> None:
        self._blobs: dict[str, StoredBlob] = {}

    def put_encrypted_blob(self, blob_bytes: bytes, metadata: dict[str, Any]) -> StoredBlobRef:
        metadata_fingerprint = repr(sorted(metadata.items()))
        digest = hashlib.sha256(blob_bytes + metadata_fingerprint.encode("utf-8")).hexdigest()
        blob_id = f"walrus_blob_{digest[:20]}"
        blob_object_id = f"0xwalrus_blob_object_{digest[20:44]}"
        stored_blob = StoredBlob(
            blob_id=blob_id,
            blob_object_id=blob_object_id,
            payload=blob_bytes,
            metadata=dict(metadata),
        )
        self._blobs[blob_id] = stored_blob
        return StoredBlobRef(
            blob_id=blob_id,
            blob_object_id=blob_object_id,
            metadata=dict(metadata),
            created_at=stored_blob.created_at,
        )

    def delete_blob(self, blob_id: str) -> bool:
        return self._blobs.pop(blob_id, None) is not None

    def get_blob(self, blob_id: str) -> StoredBlob | None:
        return self._blobs.get(blob_id)
