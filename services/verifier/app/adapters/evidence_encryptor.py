from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import base64
import hashlib
import json
import shlex
from typing import Any

from .command_runner import SubprocessCommandRunner, parse_json_output, require_success


def _normalize_payload(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


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
        payload_bytes = _normalize_payload(payload)
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


class SealCommandEvidenceEncryptor(EvidenceEncryptor):
    def __init__(
        self,
        *,
        encrypt_command: str,
        decrypt_command: str | None = None,
        command_cwd: str | None = None,
        helper_env: dict[str, str] | None = None,
        policy_version: str = "seal-v1",
        runner: SubprocessCommandRunner | None = None,
    ) -> None:
        self.encrypt_command = shlex.split(encrypt_command)
        self.decrypt_command = shlex.split(decrypt_command) if decrypt_command else None
        self.command_cwd = command_cwd
        self.helper_env = dict(helper_env or {})
        self.policy_version = policy_version
        self.runner = runner or SubprocessCommandRunner()

    def encrypt_for_wallet(
        self,
        wallet_address: str,
        payload: bytes | str | dict[str, Any],
    ) -> EncryptedEvidence:
        payload_bytes = _normalize_payload(payload)
        output = self.runner(
            self.encrypt_command,
            cwd=self.command_cwd,
            env=self.helper_env,
            input_text=json.dumps(
                {
                    "wallet_address": wallet_address,
                    "payload_b64": base64.b64encode(payload_bytes).decode("utf-8"),
                    "policy_version": self.policy_version,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        require_success(output, error_prefix="seal encrypt command failed")
        parsed = parse_json_output(output)
        encrypted_bytes_b64 = parsed.get("encrypted_bytes_b64")
        seal_identity = parsed.get("seal_identity")
        if not isinstance(encrypted_bytes_b64, str) or not isinstance(seal_identity, str):
            raise ValueError("seal encrypt command did not return encrypted_bytes_b64 and seal_identity")
        return EncryptedEvidence(
            encrypted_bytes=base64.b64decode(encrypted_bytes_b64),
            seal_identity=seal_identity,
            policy_version=str(parsed.get("policy_version") or self.policy_version),
            metadata=dict(parsed.get("metadata") or {}),
        )

    def decrypt_for_dispute(
        self,
        policy_input: DisputePolicyInput | EncryptedEvidence | dict[str, Any],
    ) -> bytes:
        if self.decrypt_command is None:
            raise RuntimeError("seal decrypt command is not configured")

        if isinstance(policy_input, dict):
            wallet_address = str(policy_input.get("wallet_address") or "")
            encrypted_bytes = policy_input["encrypted_bytes"]
            audit_reason = str(policy_input.get("audit_reason") or "dispute_review")
        elif isinstance(policy_input, EncryptedEvidence):
            wallet_address = str(policy_input.metadata.get("wallet_address") or "")
            encrypted_bytes = policy_input.encrypted_bytes
            audit_reason = "dispute_review"
        else:
            wallet_address = policy_input.wallet_address
            encrypted_bytes = policy_input.encrypted_bytes
            audit_reason = policy_input.audit_reason

        output = self.runner(
            self.decrypt_command,
            cwd=self.command_cwd,
            env=self.helper_env,
            input_text=json.dumps(
                {
                    "wallet_address": wallet_address,
                    "audit_reason": audit_reason,
                    "encrypted_bytes_b64": base64.b64encode(encrypted_bytes).decode("utf-8"),
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        require_success(output, error_prefix="seal decrypt command failed")
        parsed = parse_json_output(output)
        decrypted_bytes_b64 = parsed.get("decrypted_bytes_b64")
        if not isinstance(decrypted_bytes_b64, str):
            raise ValueError("seal decrypt command did not return decrypted_bytes_b64")
        return base64.b64decode(decrypted_bytes_b64)
