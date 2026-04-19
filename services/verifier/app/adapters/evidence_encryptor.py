from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import base64
import hashlib
import json
from typing import Any


@dataclass(slots=True)
class DisputePolicyInput:
    wallet_address: str
    encrypted_bytes: bytes
    audit_reason: str = "dispute_review"


@dataclass(slots=True)
class EncryptedEvidence:
    encrypted_bytes: bytes
    seal_identity: str
    policy_version: str = "mock-seal-v1"
    metadata: dict[str, Any] = field(default_factory=dict)


class EvidenceEncryptor(ABC):
    @abstractmethod
    def encrypt_for_wallet(
        self,
        wallet_address: str,
        payload: bytes | str | dict[str, Any],
    ) -> EncryptedEvidence:
        """Encrypt or wrap payload bytes for the target wallet."""

    @abstractmethod
    def decrypt_for_dispute(
        self,
        policy_input: DisputePolicyInput | EncryptedEvidence | dict[str, Any],
    ) -> bytes:
        """Recover encrypted evidence for dispute handling."""


class MockEvidenceEncryptor(EvidenceEncryptor):
    def encrypt_for_wallet(
        self,
        wallet_address: str,
        payload: bytes | str | dict[str, Any],
    ) -> EncryptedEvidence:
        payload_bytes = self._normalize_payload(payload)
        digest = hashlib.sha256(wallet_address.encode("utf-8") + payload_bytes).hexdigest()
        nonce = digest[:16]
        seal_identity = f"seal_identity_{digest[16:40]}"
        envelope = {
            "scheme": "mock-seal-v1",
            "wallet_address": wallet_address,
            "nonce": nonce,
            "seal_identity": seal_identity,
            "payload_b64": base64.b64encode(payload_bytes).decode("utf-8"),
        }
        return EncryptedEvidence(
            encrypted_bytes=json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8"),
            seal_identity=seal_identity,
            policy_version="mock-seal-v1",
            metadata={"wallet_address": wallet_address, "nonce": nonce},
        )

    def decrypt_for_dispute(
        self,
        policy_input: DisputePolicyInput | EncryptedEvidence | dict[str, Any],
    ) -> bytes:
        if isinstance(policy_input, dict):
            encrypted_bytes = policy_input["encrypted_bytes"]
        elif isinstance(policy_input, EncryptedEvidence):
            encrypted_bytes = policy_input.encrypted_bytes
        else:
            encrypted_bytes = policy_input.encrypted_bytes

        envelope = json.loads(encrypted_bytes.decode("utf-8"))
        return base64.b64decode(envelope["payload_b64"])

    def _normalize_payload(self, payload: bytes | str | dict[str, Any]) -> bytes:
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, str):
            return payload.encode("utf-8")
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
