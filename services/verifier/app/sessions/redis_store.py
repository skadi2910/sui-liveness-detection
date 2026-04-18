from __future__ import annotations

import asyncio
from datetime import UTC, datetime

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - dependency may be absent before install
    Redis = None

from app.sessions.models import SessionRecord, SessionStatus, WalletCooldown
from app.sessions.store import SessionStore, active_sessions, is_expired


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._cooldowns: dict[str, WalletCooldown] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, session: SessionRecord) -> SessionRecord:
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> SessionRecord | None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session and is_expired(session.expires_at):
                session.status = SessionStatus.EXPIRED
                session.updated_at = datetime.now(tz=UTC)
                self._sessions[session_id] = session
            return session

    async def save_session(self, session: SessionRecord) -> SessionRecord:
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def find_active_session_by_wallet(self, wallet_address: str) -> SessionRecord | None:
        async with self._lock:
            sessions = [
                session
                for session in self._sessions.values()
                if session.wallet_address == wallet_address
            ]
            active = active_sessions(sessions)
            return max(active, key=lambda item: item.updated_at, default=None)

    async def get_wallet_cooldown(self, wallet_address: str) -> WalletCooldown | None:
        async with self._lock:
            cooldown = self._cooldowns.get(wallet_address)
            if cooldown and is_expired(cooldown.blocked_until):
                self._cooldowns.pop(wallet_address, None)
                return None
            return cooldown

    async def set_wallet_cooldown(self, cooldown: WalletCooldown) -> None:
        async with self._lock:
            self._cooldowns[cooldown.wallet_address] = cooldown

    async def ping(self) -> bool:
        return True

    def backend_label(self) -> str:
        return "memory"


class RedisSessionStore(SessionStore):
    """Redis-ready placeholder that falls back to in-memory storage for MVP scaffolding."""

    def __init__(self, redis_url: str | None) -> None:
        self._redis_url = redis_url
        self._fallback = InMemorySessionStore()
        self._client: Redis | None = None

        if redis_url and Redis is not None:
            self._client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def create_session(self, session: SessionRecord) -> SessionRecord:
        # TODO: Persist sessions in Redis hashes/JSON once the pipeline worker wires recovery logic.
        return await self._fallback.create_session(session)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        return await self._fallback.get_session(session_id)

    async def save_session(self, session: SessionRecord) -> SessionRecord:
        return await self._fallback.save_session(session)

    async def find_active_session_by_wallet(self, wallet_address: str) -> SessionRecord | None:
        return await self._fallback.find_active_session_by_wallet(wallet_address)

    async def get_wallet_cooldown(self, wallet_address: str) -> WalletCooldown | None:
        return await self._fallback.get_wallet_cooldown(wallet_address)

    async def set_wallet_cooldown(self, cooldown: WalletCooldown) -> None:
        await self._fallback.set_wallet_cooldown(cooldown)

    async def ping(self) -> bool:
        if self._client is None:
            return False

        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    def backend_label(self) -> str:
        if self._client is None:
            return "memory-fallback"
        return "redis-placeholder"
