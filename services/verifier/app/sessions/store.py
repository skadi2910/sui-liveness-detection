from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol

from app.sessions.models import SessionRecord, SessionStatus, WalletCooldown


class SessionStore(Protocol):
    async def create_session(self, session: SessionRecord) -> SessionRecord:
        ...

    async def get_session(self, session_id: str) -> SessionRecord | None:
        ...

    async def save_session(self, session: SessionRecord) -> SessionRecord:
        ...

    async def find_active_session_by_wallet(self, wallet_address: str) -> SessionRecord | None:
        ...

    async def get_wallet_cooldown(self, wallet_address: str) -> WalletCooldown | None:
        ...

    async def set_wallet_cooldown(self, cooldown: WalletCooldown) -> None:
        ...

    async def ping(self) -> bool:
        ...

    def backend_label(self) -> str:
        ...


def is_expired(timestamp: datetime) -> bool:
    return timestamp <= datetime.now(tz=UTC)


def active_sessions(records: Iterable[SessionRecord]) -> list[SessionRecord]:
    return [
        record
        for record in records
        if not is_expired(record.expires_at)
        and record.status
        not in {SessionStatus.VERIFIED, SessionStatus.FAILED, SessionStatus.EXPIRED}
    ]
