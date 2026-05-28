"""
agents/query_agent.py
─────────────────────
QueryAgent — handles ALL read-only operations against Zoho Projects.

Responsibilities
────────────────
* list_projects, list_tasks, get_task_details,
  list_project_members, get_task_utilisation
* Uses short-term and long-term memory for context (e.g. "the first
  project", "the one we talked about earlier").
* Runs a tool-call loop (up to MAX_TOOL_ITERATIONS) to resolve
  multi-step queries.
* Never calls create / update / delete tools.

Design pattern
──────────────
The agent runs a ReAct-style tool loop:
  1. Build messages (system + memory context + user query).
  2. Ask the bound LLM to decide which tool to call (or answer directly).
  3. If a tool call is returned, invoke the tool and append the result.
  4. Repeat until the LLM produces a plain text answer or we hit the
     iteration cap.
"""

from __future__ import annotations

import json
import logging
from typing import Final

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.base_agent import BaseAgent
from tools.zoho_tools import (
    get_task_details,
    get_task_utilisation,
    list_project_members,
    list_projects,
    list_tasks,
)

logger = logging.getLogger(__name__)

_READ_TOOLS: Final = [
    list_projects,
    list_tasks,
    get_task_details,
    list_project_members,
    get_task_utilisation,
]

_TOOL_MAP: Final = {t.name: t for t in _READ_TOOLS}

MAX_TOOL_ITERATIONS: Final[int] = 6

_SYSTEM_TEMPLATE = """\
You are a helpful Zoho Projects assistant. You can ONLY read data — never write.

Available tools:
  • list_projects        – fetch all projects for the user
  • list_tasks           – list tasks in a project (filters: status, assignee, due_date)
  • get_task_details     – full details of a single task
  • list_project_members – members and roles in a project
  • get_task_utilisation – task load per member in a project

=== Session context (short-term memory) ===
{short_term}

=== User preferences (long-term memory) ===
{long_term}

Response rules:
  - Be concise and friendly.
  - Use markdown: bullet lists (- item), bold (**text**), headers (## Title).
  - Never output raw JSON, Python dicts, or code blocks.
  - Never sign off or add metadata.
  - If unsure, ask a clarifying question rather than guessing.
  - When the user says "the first project" or "that project", use last_project_id
    from short-term context.\
"""


class QueryAgent(BaseAgent):
    """
    Read-only agent.  Calls Zoho read tools and returns a markdown
    answer back to the user.  Never mutates Zoho data.
    """

    async def run(self, state: dict) -> dict:
        user_message = self._last_user_text(state["messages"])
        self.log_info("Handling query", preview=user_message[:60])

        system_prompt = _SYSTEM_TEMPLATE.format(
            short_term=json.dumps(state.get("short_term_context") or {}, ensure_ascii=False),
            long_term=json.dumps(state.get("long_term_context") or {}, ensure_ascii=False),
        )

        # Inject auth context transparently in the user turn so tools can pick
        # up access_token / portal_id without the user having to provide them.
        augmented_user_content = (
            f"{user_message}\n\n"
            f"[ctx: access_token={state['access_token']} "
            f"portal_id={state['portal_id']}]"
        )

        conversation: list = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=augmented_user_content),
        ]

        reply = await self._tool_loop(conversation)
        state["messages"].append(reply)
        return state

    # ──────────────────────────────────────────────────────────────
    # Tool execution loop
    # ──────────────────────────────────────────────────────────────

    async def _tool_loop(self, messages: list) -> AIMessage:
        """
        ReAct-style tool loop.

        Iterates up to MAX_TOOL_ITERATIONS.  On each turn the LLM either:
          a) Returns a plain text answer  → we return it immediately.
          b) Requests one or more tool calls → we invoke them and append results.
        """
        llm = self.get_llm().bind_tools(_READ_TOOLS)
        current = list(messages)

        for iteration in range(MAX_TOOL_ITERATIONS):
            ai_msg: AIMessage = await llm.ainvoke(current)
            current.append(ai_msg)

            tool_calls = getattr(ai_msg, "tool_calls", None) or []
            if not tool_calls:
                # Plain answer — we're done.
                return ai_msg

            self.log_info(
                "Tool calls requested",
                iteration=iteration,
                tools=[c.get("name") for c in tool_calls],
            )

            for call in tool_calls:
                result = await self._invoke_tool(call)
                current.append(AIMessage(content=result))

        self.log_error("Hit tool iteration cap — returning safe fallback")
        return AIMessage(
            content=(
                "I had trouble retrieving that information after several attempts. "
                "Please try rephrasing your question."
            )
        )

    async def _invoke_tool(self, call: dict) -> str:
        """Invoke a single tool call dict safely, returning JSON string output."""
        name = call.get("name", "")
        args = call.get("args") or {}
        tool = _TOOL_MAP.get(name)

        if tool is None:
            self.log_error(f"Unknown tool requested: {name}")
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            output = await tool.ainvoke(args)
            return str(output)
        except Exception as exc:
            self.log_error(f"Tool {name} raised an exception", exc=exc)
            return json.dumps({"error": str(exc)})

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _last_user_text(messages: list) -> str:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
        return ""
