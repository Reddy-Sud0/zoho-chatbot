from __future__ import annotations

import ast
from typing import Any

def normalize_reply_text(content: Any) -> str:
    """Convert Gemini/LangChain message content into plain user-facing text."""
    if content is None:
        return ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text).strip())
            elif isinstance(item, str) and item.strip():
                parts.append(item.strip())
        return "\n\n".join(parts).strip()

    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        return str(text).strip() if text else ""

    if isinstance(content, str):
        s = content.strip()
        if s.startswith("[{") and ("'type'" in s or '"type"' in s):
            try:
                parsed = ast.literal_eval(s)
                return normalize_reply_text(parsed)
            except Exception:
                pass
        return s

    return str(content).strip()