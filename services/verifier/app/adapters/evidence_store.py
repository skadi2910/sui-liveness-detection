from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from .command_runner import SubprocessCommandRunner, parse_json_output, require_success


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


class WalrusCliEvidenceStore(EvidenceStore):
    def __init__(
        self,
        *,
        walrus_binary: str = "walrus",
        config_path: str | None = None,
        context: str | None = None,
        wallet_path: str | None = None,
        gas_budget: int | None = None,
        storage_epochs: int = 5,
        force_store: bool = True,
        deletable: bool = True,
        runner: SubprocessCommandRunner | None = None,
    ) -> None:
        self.walrus_binary = walrus_binary
        self.config_path = config_path
        self.context = context
        self.wallet_path = wallet_path
        self.gas_budget = gas_budget
        self.storage_epochs = storage_epochs
        self.force_store = force_store
        self.deletable = deletable
        self.runner = runner or SubprocessCommandRunner()
        self._known_blob_object_ids: dict[str, str] = {}

    def put_encrypted_blob(self, blob_bytes: bytes, metadata: dict[str, Any]) -> StoredBlobRef:
        with tempfile.NamedTemporaryFile(prefix="walrus-evidence-", suffix=".bin", delete=False) as tmp_file:
            tmp_file.write(blob_bytes)
            temp_path = Path(tmp_file.name)

        try:
            output = self.runner(
                self._command_args(
                    "store",
                    "--epochs",
                    str(self.storage_epochs),
                    *(["--force"] if self.force_store else []),
                    *(["--deletable"] if self.deletable else []),
                    "--json",
                    str(temp_path),
                )
            )
            require_success(output, error_prefix="walrus store failed")
            parsed = self._normalize_store_payload(parse_json_output(output))
            blob_store_result = parsed.get("blobStoreResult") if isinstance(parsed, dict) else None
            if isinstance(blob_store_result, dict):
                blob_payload = (
                    blob_store_result.get("newlyCreated")
                    or blob_store_result.get("alreadyCertified")
                    or {}
                )
            else:
                blob_payload = parsed.get("newlyCreated") or parsed.get("alreadyCertified") or {}
            blob_object = blob_payload.get("blobObject") or {}
            blob_id = blob_object.get("blobId") or blob_payload.get("blobId")
            blob_object_id = blob_object.get("id")
            if not isinstance(blob_id, str) or not blob_id:
                raise ValueError("walrus store did not return blobId")
            if not isinstance(blob_object_id, str) or not blob_object_id:
                blob_object_id = f"unknown-object-for-{blob_id}"
            self._known_blob_object_ids[blob_id] = blob_object_id
            provider_metadata = dict(metadata)
            provider_metadata["walrus"] = parsed
            created_at = datetime.now(tz=UTC).isoformat()
            return StoredBlobRef(
                blob_id=blob_id,
                blob_object_id=blob_object_id,
                metadata=provider_metadata,
                created_at=created_at,
            )
        finally:
            temp_path.unlink(missing_ok=True)

    def delete_blob(self, blob_id: str) -> bool:
        known_object_id = self._known_blob_object_ids.get(blob_id)
        output = self.runner(
            self._command_args(
                "delete",
                *(
                    ["--object-ids", known_object_id]
                    if known_object_id
                    else ["--blob-ids", blob_id]
                ),
                "--yes",
                "--json",
            )
        )
        require_success(output, error_prefix="walrus delete failed")
        self._known_blob_object_ids.pop(blob_id, None)
        return True

    def _normalize_store_payload(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                if (
                    "newlyCreated" in item
                    or "alreadyCertified" in item
                    or "blobStoreResult" in item
                    or "blobObject" in item
                    or "blobId" in item
                ):
                    return item
        raise ValueError("walrus store did not return a recognized JSON payload")

    def _command_args(self, command: str, *args: str) -> list[str]:
        base = [self.walrus_binary, command]
        if self.config_path:
            base.extend(["--config", self.config_path])
        if self.context:
            base.extend(["--context", self.context])
        if self.wallet_path:
            base.extend(["--wallet", self.wallet_path])
        if self.gas_budget is not None:
            base.extend(["--gas-budget", str(self.gas_budget)])
        base.extend(args)
        return base
