"""
agents/router_agent.py
──────────────────────
RouterAgent — classifies each incoming user message as READ or WRITE
and sets ``state["route"]`` accordingly.

Design decisions
────────────────
* Primary classification: LLM (zero-shot prompt).
* Fallback classification: deterministic keyword scan — ensures the
  system still routes correctly even if the LLM is unavailable or
  returns an unexpected token.
* The router does NOT call any Zoho API and does NOT modify messages.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.base_agent import BaseAgent

_SYSTEM_PROMPT = """\
You are a strict router for a project-management chatbot.
Classify the user's intent as exactly one of:
  READ  – listing, showing, fetching, getting, summarising information
  WRITE – creating, updating, deleting, assigning, changing, modifying

Reply with ONLY one word: READ or WRITE.
Do not add punctuation, explanation, or extra text.\
"""

_WRITE_KEYWORDS = frozenset(
    {
        "create", "add", "make", "new",
        "update", "edit", "change", "modify", "rename", "set",
        "delete", "remove", "trash", "archive",
        "assign", "reassign", "move",
        "mark", "complete", "close", "reopen",
    }
)

class RouterAgent(BaseAgent):
    """
    Decides whether the user's request requires a read (Query) or
    write (Action) agent and sets ``state["route"]`` to either
    ``"query"`` or ``"action"``.
    """

    async def run(self, state: dict) -> dict:
        if state.get("awaiting_confirmation"):
            self.log_info("Awaiting confirmation — routing directly to action")
            state["route"] = "action"
            return state

        message = self._extract_last_user_message(state["messages"])
        self.log_info("Routing message", preview=message[:60])

        route = await self._llm_classify(message)
        state["route"] = route

        self.log_info("Route decided", route=route)
        return state

    async def _llm_classify(self, message: str) -> str:
        """
        Classify the message as 'query' or 'action'.

        Strategy (quota-efficient):
          1. Try the keyword scan first — handles the vast majority of requests
             instantly and at zero API cost.
          2. Only call the LLM when keywords give no strong signal (i.e. no
             write keyword matched AND the message is >20 chars, suggesting a
             complex/ambiguous intent like "what's going on with my team?").
        """
        words = set(message.lower().split())

        if words & _WRITE_KEYWORDS:
            return "action"

        if len(message) <= 20:
            return "query"

        try:
            llm = self.get_llm()
            response = await llm.ainvoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=message),
                ]
            )
            label = str(response.content).strip().upper()
            if "WRITE" in label:
                return "action"
            if "READ" in label:
                return "query"
        except Exception as exc:
            self.log_error("LLM classification failed, using keywords", exc=exc)

        return "query"

    def _keyword_classify(self, message: str) -> str:
        """Deterministic keyword-based fallback classifier."""
        words = set(message.lower().split())
        if words & _WRITE_KEYWORDS:
            return "action"
        return "query"

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
        return ""