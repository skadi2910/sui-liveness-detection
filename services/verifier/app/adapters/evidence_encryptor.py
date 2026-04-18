from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import base64
import hashlib
import json
from typing import Any


@dataclass(slots=True)
class DisputePolicyInput:
    wallet_address: str
    encrypted_bytes: bytes
    audit_reason: str = "dispute_review"


class EvidenceEncryptor(ABC):
    @abstractmethod
    def encrypt_for_wallet(self, wallet_address: str, payload: bytes | str | dict[str, Any]) -> bytes:
        """Encrypt or wrap payload bytes for the target wallet."""

    @abstractmethod
    def decrypt_for_dispute(self, policy_input: DisputePolicyInput | dict[str, Any]) -> bytes:
        """Recover encrypted evidence for dispute handling."""


class MockEvidenceEncryptor(EvidenceEncryptor):
    def encrypt_for_wallet(self, wallet_address: str, payload: bytes | str | dict[str, Any]) -> bytes:
        payload_bytes = self._normalize_payload(payload)
        nonce = hashlib.sha256(wallet_address.encode("utf-8") + payload_bytes).hexdigest()[:16]
        envelope = {
            "scheme": "mock-seal-v1",
            "wallet_address": wallet_address,
            "nonce": nonce,
            "payload_b64": base64.b64encode(payload_bytes).decode("utf-8"),
        }
        return json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def decrypt_for_dispute(self, policy_input: DisputePolicyInput | dict[str, Any]) -> bytes:
        if isinstance(policy_input, dict):
            encrypted_bytes = policy_input["encrypted_bytes"]
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
