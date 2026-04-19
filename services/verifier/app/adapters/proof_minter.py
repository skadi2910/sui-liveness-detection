from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any

from .command_runner import (
    CommandExecutionError,
    SubprocessCommandRunner,
    parse_json_output,
    require_success,
)
from ..pipeline.types import SessionStatus, VerificationResult
from ..sessions.models import PreparedProofClaim, ProofClaimOperation


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _string_as_u8_vector(value: str | None) -> str:
    encoded = (value or "").encode("utf-8")
    return "[" + ",".join(str(item) for item in encoded) + "]"


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _walk_json(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_json(item)


@dataclass(slots=True)
class ActiveProof:
    proof_id: str
    expires_at: str | None = None
    object_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MintResult:
    success: bool
    proof_id: str | None = None
    transaction_digest: str | None = None
    proof_operation: str | None = None
    chain_network: str | None = None
    walrus_blob_id: str | None = None
    walrus_blob_object_id: str | None = None
    seal_identity: str | None = None
    evidence_schema_version: int | None = None
    model_hash: str | None = None
    challenge_type: str | None = None
    expires_at: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RenewResult:
    success: bool
    proof_id: str | None = None
    expires_at: str | None = None
    transaction_digest: str | None = None
    proof_operation: str | None = None
    chain_network: str | None = None
    walrus_blob_id: str | None = None
    walrus_blob_object_id: str | None = None
    seal_identity: str | None = None
    evidence_schema_version: int | None = None
    model_hash: str | None = None
    challenge_type: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProofMinter(ABC):
    @abstractmethod
    def find_active_proof(
        self,
        wallet_address: str,
        *,
        now: datetime | None = None,
    ) -> ActiveProof | None:
        """Return the current active proof for a wallet if one exists."""

    @abstractmethod
    def mint_proof(self, session_result: VerificationResult) -> MintResult:
        """Mint a proof for a successful verification result."""

    @abstractmethod
    def renew_proof(
        self,
        session_result: VerificationResult,
        previous_proof_id: str,
    ) -> RenewResult:
        """Renew an existing proof after a fresh verification."""

    @abstractmethod
    def prepare_wallet_claim(
        self,
        session_result: VerificationResult,
        *,
        operation: ProofClaimOperation,
        claim_id: str,
        claim_expires_at_ms: int,
        issued_at_ms: int,
        expires_at_ms: int,
        proof_object_id: str | None = None,
    ) -> PreparedProofClaim:
        """Prepare a user-wallet-submitted proof claim."""


class MockProofMinter(ProofMinter):
    def __init__(self, proof_ttl_days: int = 90, minimum_confidence: float = 0.7) -> None:
        self.proof_ttl_days = proof_ttl_days
        self.minimum_confidence = minimum_confidence
        self._active_proofs: dict[str, ActiveProof] = {}

    def find_active_proof(
        self,
        wallet_address: str,
        *,
        now: datetime | None = None,
    ) -> ActiveProof | None:
        active_proof = self._active_proofs.get(wallet_address)
        if active_proof is None:
            return None
        active_now = now or _now_utc()
        expires_at = _parse_iso_datetime(active_proof.expires_at)
        if expires_at is not None and expires_at <= active_now:
            self._active_proofs.pop(wallet_address, None)
            return None
        return active_proof

    def mint_proof(self, session_result: VerificationResult) -> MintResult:
        if session_result.status is not SessionStatus.VERIFIED or not session_result.human:
            return MintResult(success=False, reason="session_not_verified")
        if session_result.confidence < self.minimum_confidence:
            return MintResult(success=False, reason="confidence_below_threshold")

        seed = "|".join(
            [
                session_result.session_id,
                session_result.wallet_address,
                session_result.challenge_type.value,
                f"{session_result.confidence:.4f}",
                f"{session_result.spoof_score:.4f}",
            ]
        )
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        expires_at = (_now_utc() + timedelta(days=self.proof_ttl_days)).isoformat()
        proof_id = f"0xproof_{digest[:24]}"
        self._active_proofs[session_result.wallet_address] = ActiveProof(
            proof_id=proof_id,
            expires_at=expires_at,
            object_id=proof_id,
        )
        return MintResult(
            success=True,
            proof_id=proof_id,
            transaction_digest=f"0xtxn_{digest[24:48]}",
            proof_operation="minted",
            chain_network="mock-sui-testnet",
            walrus_blob_id=session_result.walrus_blob_id,
            walrus_blob_object_id=session_result.walrus_blob_object_id,
            seal_identity=session_result.seal_identity,
            evidence_schema_version=session_result.evidence_schema_version,
            model_hash=session_result.model_hash,
            challenge_type=session_result.challenge_type.value,
            expires_at=expires_at,
            metadata={"network": "mock-sui-testnet", "proof_ttl_days": self.proof_ttl_days},
        )

    def renew_proof(
        self,
        session_result: VerificationResult,
        previous_proof_id: str,
    ) -> RenewResult:
        seed = f"{session_result.wallet_address}|{previous_proof_id}|renew"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        expires_at = (_now_utc() + timedelta(days=self.proof_ttl_days)).isoformat()
        self._active_proofs[session_result.wallet_address] = ActiveProof(
            proof_id=previous_proof_id,
            expires_at=expires_at,
            object_id=previous_proof_id,
        )
        return RenewResult(
            success=True,
            proof_id=previous_proof_id,
            expires_at=expires_at,
            transaction_digest=f"0xtxn_{digest[:24]}",
            proof_operation="renewed",
            chain_network="mock-sui-testnet",
            walrus_blob_id=session_result.walrus_blob_id,
            walrus_blob_object_id=session_result.walrus_blob_object_id,
            seal_identity=session_result.seal_identity,
            evidence_schema_version=session_result.evidence_schema_version,
            model_hash=session_result.model_hash,
            challenge_type=session_result.challenge_type.value,
            metadata={"network": "mock-sui-testnet", "renewed": True},
        )

    def prepare_wallet_claim(
        self,
        session_result: VerificationResult,
        *,
        operation: ProofClaimOperation,
        claim_id: str,
        claim_expires_at_ms: int,
        issued_at_ms: int,
        expires_at_ms: int,
        proof_object_id: str | None = None,
    ) -> PreparedProofClaim:
        return PreparedProofClaim(
            session_id=session_result.session_id,
            wallet_address=session_result.wallet_address,
            operation=operation,
            package_id="0xmock_package",
            registry_object_id="0xmock_registry",
            module_name="proof_of_human",
            claim_id=claim_id,
            claim_expires_at_ms=claim_expires_at_ms,
            proof_object_id=proof_object_id,
            walrus_blob_id=session_result.walrus_blob_id or "",
            walrus_blob_object_id=session_result.walrus_blob_object_id or "0xmock_blob",
            seal_identity=session_result.seal_identity or "",
            evidence_schema_version=session_result.evidence_schema_version or 1,
            model_hash=session_result.model_hash,
            confidence_bps=self._confidence_bps(session_result.confidence),
            issued_at_ms=issued_at_ms,
            expires_at_ms=expires_at_ms,
            challenge_type=session_result.challenge_type.value,
            signature_b64="bW9ja19zaWduYXR1cmU=",
            chain_network="mock-sui-testnet",
        )


class SuiCliProofMinter(ProofMinter):
    def __init__(
        self,
        *,
        package_id: str,
        registry_object_id: str,
        verifier_cap_object_id: str,
        module_name: str = "proof_of_human",
        network: str = "sui-testnet",
        client_config_path: str | None = None,
        env_alias: str | None = None,
        expected_active_address: str | None = None,
        gas_budget: int | None = None,
        proof_ttl_days: int = 90,
        runner: SubprocessCommandRunner | None = None,
    ) -> None:
        self.package_id = package_id
        self.registry_object_id = registry_object_id
        self.verifier_cap_object_id = verifier_cap_object_id
        self.module_name = module_name
        self.network = network
        self.client_config_path = client_config_path
        self.env_alias = env_alias
        self.expected_active_address = expected_active_address
        self.gas_budget = gas_budget
        self.proof_ttl_days = proof_ttl_days
        self.runner = runner or SubprocessCommandRunner()
        self._proof_type = f"{self.package_id}::{self.module_name}::ProofOfHuman"
        self._claim_sign_script = (
            Path(__file__).resolve().parents[4] / "apps" / "web" / "scripts" / "sign-proof-claim.mjs"
        )

    def find_active_proof(
        self,
        wallet_address: str,
        *,
        now: datetime | None = None,
    ) -> ActiveProof | None:
        self._ensure_expected_signer()
        active_now_ms = int((now or _now_utc()).timestamp() * 1000)
        registry_proof = self._find_active_proof_from_registry(
            wallet_address,
            active_now_ms=active_now_ms,
        )
        if registry_proof is not None:
            return registry_proof

        owned_objects = self._list_owned_objects(wallet_address)
        for item in owned_objects:
            object_type = str(item.get("type") or item.get("objectType") or "")
            if object_type != self._proof_type:
                continue
            object_id = str(item.get("objectId") or item.get("object_id") or "")
            if not object_id:
                continue
            object_payload = self._get_object(object_id)
            fields = self._extract_object_fields(object_payload)
            expires_at_ms = _safe_int(fields.get("expires_at_ms"))
            if expires_at_ms is None or expires_at_ms <= active_now_ms:
                continue
            return ActiveProof(
                proof_id=object_id,
                expires_at=datetime.fromtimestamp(expires_at_ms / 1000, tz=UTC).isoformat(),
                object_id=object_id,
                metadata={"network": self.network},
            )
        return None

    def _find_active_proof_from_registry(
        self,
        wallet_address: str,
        *,
        active_now_ms: int,
    ) -> ActiveProof | None:
        payload = self._get_object(self.registry_object_id)
        best_match: ActiveProof | None = None

        for node in _walk_json(payload):
            owner = node.get("owner")
            proof_id = node.get("proof_id") or node.get("proofId")
            expires_at_ms = _safe_int(node.get("expires_at_ms") or node.get("expiresAtMs"))
            issued_at_ms = _safe_int(node.get("issued_at_ms") or node.get("issuedAtMs")) or 0
            revoked = node.get("revoked")

            if owner != wallet_address:
                continue
            if not isinstance(proof_id, str) or not proof_id:
                continue
            if expires_at_ms is None or expires_at_ms <= active_now_ms:
                continue
            if isinstance(revoked, bool) and revoked:
                continue

            candidate = ActiveProof(
                proof_id=proof_id,
                expires_at=datetime.fromtimestamp(expires_at_ms / 1000, tz=UTC).isoformat(),
                object_id=proof_id,
                metadata={
                    "network": self.network,
                    "issued_at_ms": issued_at_ms,
                    "source": "registry_record",
                },
            )
            if best_match is None:
                best_match = candidate
                continue

            best_issued_at_ms = _safe_int(best_match.metadata.get("issued_at_ms")) or 0
            if issued_at_ms >= best_issued_at_ms:
                best_match = candidate

        return best_match

    def mint_proof(self, session_result: VerificationResult) -> MintResult:
        if session_result.status is not SessionStatus.VERIFIED or not session_result.human:
            return MintResult(success=False, reason="session_not_verified")

        registry_config = self._get_registry_config()
        if session_result.confidence < registry_config["minimum_confidence"]:
            return MintResult(success=False, reason="confidence_below_threshold")

        issued_at_ms, expires_at_ms, expires_at = self._issuance_window(registry_config["ttl_ms"])
        payload = self._execute_move_call(
            "verify_and_mint",
            [
                self.registry_object_id,
                self.verifier_cap_object_id,
                session_result.wallet_address,
                _string_as_u8_vector(session_result.walrus_blob_id),
                session_result.walrus_blob_object_id,
                _string_as_u8_vector(session_result.seal_identity),
                str(session_result.evidence_schema_version or 1),
                _string_as_u8_vector(session_result.model_hash),
                str(self._confidence_bps(session_result.confidence)),
                str(issued_at_ms),
                str(expires_at_ms),
                _string_as_u8_vector(session_result.challenge_type.value),
            ],
        )
        proof_id = self._extract_proof_object_id(payload)
        if proof_id is None:
            active_proof = self.find_active_proof(session_result.wallet_address)
            proof_id = active_proof.proof_id if active_proof is not None else None
        return MintResult(
            success=proof_id is not None,
            proof_id=proof_id,
            transaction_digest=self._extract_transaction_digest(payload),
            proof_operation="minted",
            chain_network=self.network,
            walrus_blob_id=session_result.walrus_blob_id,
            walrus_blob_object_id=session_result.walrus_blob_object_id,
            seal_identity=session_result.seal_identity,
            evidence_schema_version=session_result.evidence_schema_version,
            model_hash=session_result.model_hash,
            challenge_type=session_result.challenge_type.value,
            expires_at=expires_at,
            reason=None if proof_id is not None else "mint_failed",
            metadata={"network": self.network, "registry_ttl_ms": registry_config["ttl_ms"]},
        )

    def renew_proof(
        self,
        session_result: VerificationResult,
        previous_proof_id: str,
    ) -> RenewResult:
        if session_result.status is not SessionStatus.VERIFIED or not session_result.human:
            return RenewResult(success=False, proof_id=previous_proof_id, reason="session_not_verified")

        registry_config = self._get_registry_config()
        if session_result.confidence < registry_config["minimum_confidence"]:
            return RenewResult(
                success=False,
                proof_id=previous_proof_id,
                reason="confidence_below_threshold",
            )

        issued_at_ms, expires_at_ms, expires_at = self._issuance_window(registry_config["ttl_ms"])
        payload = self._execute_move_call(
            "renew",
            [
                self.registry_object_id,
                self.verifier_cap_object_id,
                previous_proof_id,
                _string_as_u8_vector(session_result.walrus_blob_id),
                session_result.walrus_blob_object_id,
                _string_as_u8_vector(session_result.seal_identity),
                str(session_result.evidence_schema_version or 1),
                _string_as_u8_vector(session_result.model_hash),
                str(self._confidence_bps(session_result.confidence)),
                str(issued_at_ms),
                str(expires_at_ms),
                _string_as_u8_vector(session_result.challenge_type.value),
            ],
        )
        return RenewResult(
            success=True,
            proof_id=previous_proof_id,
            expires_at=expires_at,
            transaction_digest=self._extract_transaction_digest(payload),
            proof_operation="renewed",
            chain_network=self.network,
            walrus_blob_id=session_result.walrus_blob_id,
            walrus_blob_object_id=session_result.walrus_blob_object_id,
            seal_identity=session_result.seal_identity,
            evidence_schema_version=session_result.evidence_schema_version,
            model_hash=session_result.model_hash,
            challenge_type=session_result.challenge_type.value,
            metadata={"network": self.network, "registry_ttl_ms": registry_config["ttl_ms"]},
        )

    def prepare_wallet_claim(
        self,
        session_result: VerificationResult,
        *,
        operation: ProofClaimOperation,
        claim_id: str,
        claim_expires_at_ms: int,
        issued_at_ms: int,
        expires_at_ms: int,
        proof_object_id: str | None = None,
    ) -> PreparedProofClaim:
        self._ensure_expected_signer()

        signer_private_key = self._export_signer_private_key()
        payload = {
            "operation": operation.value,
            "claim_id": claim_id,
            "claim_expires_at_ms": claim_expires_at_ms,
            "wallet_address": session_result.wallet_address,
            "proof_object_id": proof_object_id,
            "walrus_blob_id": session_result.walrus_blob_id or "",
            "walrus_blob_object_id": session_result.walrus_blob_object_id or "",
            "seal_identity": session_result.seal_identity or "",
            "evidence_schema_version": session_result.evidence_schema_version or 1,
            "model_hash": session_result.model_hash or "",
            "confidence_bps": self._confidence_bps(session_result.confidence),
            "issued_at_ms": issued_at_ms,
            "expires_at_ms": expires_at_ms,
            "challenge_type": session_result.challenge_type.value,
            "private_key": signer_private_key,
        }
        signature_payload = self._run_claim_signer(payload)

        return PreparedProofClaim(
            session_id=session_result.session_id,
            wallet_address=session_result.wallet_address,
            operation=operation,
            package_id=self.package_id,
            registry_object_id=self.registry_object_id,
            module_name=self.module_name,
            claim_id=claim_id,
            claim_expires_at_ms=claim_expires_at_ms,
            proof_object_id=proof_object_id,
            walrus_blob_id=session_result.walrus_blob_id or "",
            walrus_blob_object_id=session_result.walrus_blob_object_id or "",
            seal_identity=session_result.seal_identity or "",
            evidence_schema_version=session_result.evidence_schema_version or 1,
            model_hash=session_result.model_hash,
            confidence_bps=self._confidence_bps(session_result.confidence),
            issued_at_ms=issued_at_ms,
            expires_at_ms=expires_at_ms,
            challenge_type=session_result.challenge_type.value,
            signature_b64=str(signature_payload["signature_b64"]),
            chain_network=self.network,
        )

    def _issuance_window(self, ttl_ms: int) -> tuple[int, int, str]:
        issued_at = _now_utc()
        ttl_delta = timedelta(milliseconds=ttl_ms)
        expires_at = issued_at + ttl_delta
        return (
            int(issued_at.timestamp() * 1000),
            int(expires_at.timestamp() * 1000),
            expires_at.isoformat(),
        )

    def _confidence_bps(self, confidence: float) -> int:
        return round(confidence * 10_000)

    def _get_registry_config(self) -> dict[str, int | float]:
        payload = self._get_object(self.registry_object_id)
        fields = self._extract_object_fields(payload)
        minimum_confidence_bps = _safe_int(fields.get("minimum_confidence_bps"))
        default_ttl_ms = _safe_int(fields.get("default_ttl_ms"))
        ttl_ms = default_ttl_ms or (self.proof_ttl_days * 24 * 60 * 60 * 1000)
        minimum_confidence = (minimum_confidence_bps or 0) / 10_000
        return {
            "minimum_confidence_bps": minimum_confidence_bps or 0,
            "minimum_confidence": minimum_confidence,
            "ttl_ms": ttl_ms,
        }

    def _list_owned_objects(self, wallet_address: str) -> list[dict[str, Any]]:
        payload = self._run_json_command("objects", "--json", wallet_address)
        matches: list[dict[str, Any]] = []
        for node in _walk_json(payload):
            if "objectId" in node or "object_id" in node:
                matches.append(node)
        return matches

    def _get_object(self, object_id: str) -> dict[str, Any]:
        payload = self._run_json_command("object", "--json", object_id)
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected object payload for {object_id}")
        return payload

    def _extract_object_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        for node in _walk_json(payload):
            fields = node.get("fields")
            if isinstance(fields, dict):
                return fields
            content = node.get("content")
            if isinstance(content, dict) and all(not isinstance(value, dict) for value in content.values()):
                return content
        raise ValueError("could not locate object fields in sui payload")

    def _extract_transaction_digest(self, payload: Any) -> str | None:
        for node in _walk_json(payload):
            for key in ("digest", "transactionDigest", "txDigest"):
                value = node.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    def _extract_proof_object_id(self, payload: Any) -> str | None:
        for node in _walk_json(payload):
            object_type = str(node.get("objectType") or node.get("type") or "")
            if object_type == self._proof_type:
                object_id = node.get("objectId") or node.get("object_id")
                if isinstance(object_id, str) and object_id:
                    return object_id
        return None

    def _execute_move_call(self, function_name: str, args: list[str]) -> Any:
        return self._run_json_command(
            "call",
            "--package",
            self.package_id,
            "--module",
            self.module_name,
            "--function",
            function_name,
            "--args",
            *args,
            *(["--gas-budget", str(self.gas_budget)] if self.gas_budget else []),
            "--json",
        )

    def _run_json_command(self, command: str, *args: str) -> Any:
        base_args = ["sui", "client"]
        if self.client_config_path:
            base_args.extend(["--client.config", self.client_config_path])
        if self.env_alias:
            base_args.extend(["--client.env", self.env_alias])
        base_args.extend([command, *args])
        output = self.runner(base_args)
        require_success(output, error_prefix=f"sui client {command} failed")
        return parse_json_output(output)

    def _export_signer_private_key(self) -> str:
        base_args = ["sui", "keytool"]
        if self.client_config_path:
            base_args.extend(["--keystore-path", self._resolve_keystore_path(self.client_config_path)])
        base_args.extend(["export", "--key-identity", self.expected_active_address or "active", "--json"])
        output = self.runner(base_args)
        require_success(output, error_prefix="sui keytool export failed")
        payload = parse_json_output(output)
        exported_private_key = payload.get("exportedPrivateKey")
        if not isinstance(exported_private_key, str) or not exported_private_key:
            raise ValueError("sui keytool export did not return exportedPrivateKey")
        return exported_private_key

    def _resolve_keystore_path(self, client_config_path: str) -> str:
        config_path = Path(client_config_path)
        if config_path.is_dir():
            return str(config_path)
        return str(config_path.with_name("sui.keystore"))

    def _run_claim_signer(self, payload: dict[str, Any]) -> dict[str, Any]:
        output = self.runner(
            ["node", str(self._claim_sign_script)],
            input_text=json.dumps(payload),
            cwd=str(self._claim_sign_script.parent.parent.parent.parent),
        )
        require_success(output, error_prefix="proof claim signer failed")
        parsed = parse_json_output(output)
        if not isinstance(parsed, dict):
            raise ValueError("proof claim signer returned an invalid payload")
        return parsed

    def _ensure_expected_signer(self) -> None:
        if not self.expected_active_address:
            return
        base_args = ["sui", "client"]
        if self.client_config_path:
            base_args.extend(["--client.config", self.client_config_path])
        if self.env_alias:
            base_args.extend(["--client.env", self.env_alias])
        base_args.append("active-address")
        output = self.runner(base_args)
        require_success(output, error_prefix="sui client active-address failed")
        active_address = output.stdout.strip()
        if active_address != self.expected_active_address:
            raise CommandExecutionError(
                f"unexpected active signer {active_address}; expected {self.expected_active_address}",
                output,
            )
