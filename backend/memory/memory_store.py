"""
memory/memory_store.py
──────────────────────
Two-layer memory system for the Zoho AI chatbot.

Short-term memory  (within a single user session)
──────────────────────────────────────────────────
  • Stored in a module-level dict keyed by session_id.
  • Survives multiple HTTP requests within the same server process.
  • Automatically pruned when a session is closed (call clear_short).
  • Keys typically used:
      last_project_id    – id of the most recently mentioned project
      last_project_name  – human-readable name of the same project
      last_task_id       – id of the most recently mentioned task
      pending_action     – serialised HIL action waiting for confirmation

Long-term memory  (across sessions and server restarts)
─────────────────────────────────────────────────────────
  • Persisted in the SQLite ``memory`` table via SQLAlchemy.
  • Keys are arbitrary strings; values are text (JSON or plain).
  • Keys typically used:
      preferred_project_id    – user's most-used project
      preferred_project_name
      last_query              – last natural-language query
      frequent_projects       – JSON list of {id, name} dicts

Usage
─────
    store = MemoryStore(db_session)
    store.set_short(session_id, "last_project_id", "12345")
    pid = store.get_short(session_id, "last_project_id")

    await store.set_long(user_id, "preferred_project_id", "12345")
    pid = await store.get_long(user_id, "preferred_project_id")
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from database.models import Memory

# ── Module-level short-term store ────────────────────────────────
# Using a single dict at module scope guarantees that all
# MemoryStore instances (created fresh per HTTP request) share the
# same in-process state.  A threading.Lock protects writes in
# multi-threaded environments (e.g. Uvicorn with multiple workers
# would each have their own process copy — acceptable for SQLite).

_short_term_store: dict[str, dict[str, Any]] = {}
_store_lock = threading.Lock()


class MemoryStore:
    """
    Unified short-term (in-process) and long-term (SQLite) memory.

    A new instance is safe to create per request; all instances share
    the same ``_short_term_store`` module-level dict.
    """

    def __init__(self, db_session) -> None:
        self._db = db_session

    # ──────────────────────────────────────────────────────────────
    # Short-term (in-process, per session)
    # ──────────────────────────────────────────────────────────────

    def get_short(self, session_id: str, key: str) -> Any:
        """Return a single short-term value, or ``None`` if missing."""
        with _store_lock:
            return _short_term_store.get(session_id, {}).get(key)

    def set_short(self, session_id: str, key: str, value: Any) -> None:
        """Upsert a single short-term key/value for a session."""
        with _store_lock:
            if session_id not in _short_term_store:
                _short_term_store[session_id] = {}
            _short_term_store[session_id][key] = value

    def get_all_short(self, session_id: str) -> dict:
        """Return a snapshot of all short-term values for a session."""
        with _store_lock:
            return dict(_short_term_store.get(session_id, {}))

    def clear_short(self, session_id: str) -> None:
        """Delete all short-term state for a session (e.g. on logout)."""
        with _store_lock:
            _short_term_store.pop(session_id, None)

    def update_short(self, session_id: str, data: dict) -> None:
        """Bulk-upsert multiple short-term values at once."""
        with _store_lock:
            if session_id not in _short_term_store:
                _short_term_store[session_id] = {}
            _short_term_store[session_id].update(data)

    # ──────────────────────────────────────────────────────────────
    # Long-term (SQLite, per user)
    # ──────────────────────────────────────────────────────────────

    async def get_long(self, user_id: str, key: str) -> Optional[str]:
        """Return the long-term value for ``user_id/key``, or ``None``."""
        row = (
            self._db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.key == key)
            .first()
        )
        return row.value if row else None

    async def set_long(self, user_id: str, key: str, value: str) -> None:
        """Upsert a long-term value for ``user_id/key``."""
        row = (
            self._db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.key == key)
            .first()
        )
        if row:
            row.value = value
        else:
            row = Memory(user_id=user_id, key=key, value=value)
            self._db.add(row)
        self._db.commit()

    async def get_all_long(self, user_id: str) -> dict:
        """Return all long-term key/value pairs for a user."""
        rows = self._db.query(Memory).filter(Memory.user_id == user_id).all()
        return {r.key: r.value for r in rows}

    async def update_long(self, user_id: str, data: dict) -> None:
        """Bulk-upsert multiple long-term values at once."""
        for key, value in data.items():
            await self.set_long(user_id, key, str(value))
