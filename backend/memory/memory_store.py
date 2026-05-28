from __future__ import annotations

from typing import Any, Optional

from database.models import Memory


class MemoryStore:
    """
    Two-layer memory system.

    SHORT-TERM: Python dict keyed by session_id
    {
      "session_abc": {
        "last_project_id": "123",
        "last_project_name": "Website Redesign",
        "last_tasks": [...],
        "conversation_history": [...]
      }
    }

    LONG-TERM: SQLite memory table
    Persisted keys per user:
      - "preferred_project_id"
      - "preferred_project_name"
      - "last_query"
      - "frequent_projects" (JSON list)
    """

    def __init__(self, db_session):
        self._short_term: dict[str, dict[str, Any]] = {}
        self.db = db_session

    # SHORT TERM
    def get_short(self, session_id: str, key: str):
        return (self._short_term.get(session_id) or {}).get(key)

    def set_short(self, session_id: str, key: str, value):
        self._short_term.setdefault(session_id, {})
        self._short_term[session_id][key] = value

    def get_all_short(self, session_id: str) -> dict:
        return dict(self._short_term.get(session_id) or {})

    def clear_short(self, session_id: str):
        self._short_term.pop(session_id, None)

    # LONG TERM
    async def get_long(self, user_id: str, key: str) -> Optional[str]:
        row = self.db.query(Memory).filter(Memory.user_id == user_id, Memory.key == key).first()
        if not row:
            return None
        return row.value

    async def set_long(self, user_id: str, key: str, value: str):
        row = self.db.query(Memory).filter(Memory.user_id == user_id, Memory.key == key).first()
        if row:
            row.value = value
        else:
            row = Memory(user_id=user_id, key=key, value=value)
            self.db.add(row)
        self.db.commit()

    async def get_all_long(self, user_id: str) -> dict:
        rows = self.db.query(Memory).filter(Memory.user_id == user_id).all()
        return {r.key: r.value for r in rows}
