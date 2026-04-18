from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
from typing import Any

from ..pipeline.types import SessionStatus, VerificationResult


@dataclass(slots=True)
class MintResult:
    success: bool
    proof_id: str | None = None
    transaction_digest: str | None = None
    expires_at: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RenewResult:
    success: bool
    proof_id: str
    expires_at: str | None = None
    transaction_digest: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProofMinter(ABC):
    @abstractmethod
    def mint_proof(self, session_result: VerificationResult) -> MintResult:
        """Mint a proof for a successful verification result."""

    @abstractmethod
    def renew_proof(self, wallet_address: str, previous_proof_id: str) -> RenewResult:
        """Renew an existing proof after a fresh verification."""


class MockProofMinter(ProofMinter):
    def __init__(self, proof_ttl_days: int = 90, minimum_confidence: float = 0.7) -> None:
        self.proof_ttl_days = proof_ttl_days
        self.minimum_confidence = minimum_confidence

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
        expires_at = (datetime.utcnow() + timedelta(days=self.proof_ttl_days)).isoformat()
        return MintResult(
            success=True,
            proof_id=f"0xproof_{digest[:24]}",
            transaction_digest=f"0xtxn_{digest[24:48]}",
            expires_at=expires_at,
            metadata={"network": "mock-sui-testnet", "proof_ttl_days": self.proof_ttl_days},
        )

    def renew_proof(self, wallet_address: str, previous_proof_id: str) -> RenewResult:
        seed = f"{wallet_address}|{previous_proof_id}|renew"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        expires_at = (datetime.utcnow() + timedelta(days=self.proof_ttl_days)).isoformat()
        return RenewResult(
            success=True,
            proof_id=previous_proof_id,
            expires_at=expires_at,
            transaction_digest=f"0xtxn_{digest[:24]}",
            metadata={"network": "mock-sui-testnet", "renewed": True},
        )
