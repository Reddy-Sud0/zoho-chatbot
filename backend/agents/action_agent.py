"""
agents/action_agent.py
──────────────────────
ActionAgent — handles ALL write operations against Zoho Projects.

Human-in-the-Loop (HIL) protocol
──────────────────────────────────
Write operations use a mandatory two-phase commit pattern:

  Phase 1 — PLAN  (state.awaiting_confirmation is False on entry)
  ──────────────────────────────────────────────────────────────
    1. The LLM analyses the user's request.
    2. The LLM returns a structured JSON plan:
         { "tool": str, "description": str, "params": dict }
    3. The agent stores the plan in ``state["pending_action"]`` and
       sets ``state["awaiting_confirmation"] = True``.
    4. A human-readable "I am about to …" message is returned to the UI.
    5. The graph ends — control returns to the caller (FastAPI).

  Phase 2 — EXECUTE  (state.awaiting_confirmation is True on entry)
  ──────────────────────────────────────────────────────────────────
    The user has responded via ``POST /chat`` with ``confirmed=true`` or
    ``confirmed=false``.

    • confirmed=True  → execute the stored tool call.
    • confirmed=False → discard the plan and return a cancellation message.

Responsibilities
────────────────
  Tools available: create_task, update_task, delete_task.
  The agent MUST NOT call any read tool.

Design notes
────────────
  * The LLM is instructed to output ONLY JSON in Phase 1 — no prose.
  * If the LLM output cannot be parsed as JSON, the agent falls back to
    a safe "cannot determine action" reply rather than hallucinating.
  * All Zoho credentials (access_token, portal_id) are injected from
    state — never passed by the user.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Final

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.base_agent import BaseAgent
from tools.zoho_tools import create_task, delete_task, update_task

logger = logging.getLogger(__name__)

_WRITE_TOOLS: Final = [create_task, update_task, delete_task]
_WRITE_TOOL_NAMES: Final[frozenset[str]] = frozenset(t.name for t in _WRITE_TOOLS)
_TOOL_MAP: Final = {t.name: t for t in _WRITE_TOOLS}

_PLAN_SYSTEM_TEMPLATE = """\
You are a Zoho Projects write-action planner.

Your ONLY job is to produce a JSON plan for a write operation.
Do NOT execute the operation. Do NOT add any explanation.
Output ONLY valid JSON — no markdown fences, no extra text.

Available tools:
  • create_task  – params: project_id (required), name (required),
                            assignee (optional), due_date (optional, YYYY-MM-DD),
                            priority (optional: High/Medium/Low)
  • update_task  – params: project_id (required), task_id (required),
                            status (optional), assignee (optional),
                            due_date (optional), priority (optional)
  • delete_task  – params: project_id (required), task_id (required)

JSON schema:
{{
  "tool": "<tool_name>",
  "description": "<one sentence describing exactly what will happen>",
  "params": {{ <key>: <value>, ... }}
}}

Use project_id / task_id from context when the user does not supply them.

=== Short-term context ===
{short_term}

=== Long-term context ===
{long_term}\
"""

class ActionAgent(BaseAgent):
    """
    Write agent with mandatory Human-in-the-Loop confirmation.

    Phase 1 (plan): Asks LLM to produce a structured action plan and
    returns it to the user for confirmation without executing anything.

    Phase 2 (execute): Runs the previously confirmed plan against the
    Zoho API, or cancels cleanly on user rejection.
    """

    async def run(self, state: dict) -> dict:
        if state.get("awaiting_confirmation") and state.get("pending_action"):
            return await self._execute_phase(state)
        return await self._plan_phase(state)

    async def _plan_phase(self, state: dict) -> dict:
        """Ask the LLM to build a write plan; do NOT execute it."""
        user_message = self._last_user_text(state["messages"])
        self.log_info("Planning write action", preview=user_message[:60])

        system_prompt = _PLAN_SYSTEM_TEMPLATE.format(
            short_term=json.dumps(state.get("short_term_context") or {}, ensure_ascii=False),
            long_term=json.dumps(state.get("long_term_context") or {}, ensure_ascii=False),
        )

        try:
            llm = self.get_llm()
            response = await llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message),
                ]
            )
            raw = self._strip_json_fences(str(response.content).strip())
            plan = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            self.log_error("Could not parse LLM plan output", exc=exc)
            state["messages"].append(
                AIMessage(
                    content=(
                        "I couldn't determine what write action to perform. "
                        "Could you be more specific? For example: "
                        '"Create a task called X in project Y" or '
                        '"Delete task 123 from project ABC".'
                    )
                )
            )
            return state
        except Exception as exc:
            err_str = str(exc)
            self.log_error("LLM API call failed in plan phase", exc=exc)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                state["messages"].append(
                    AIMessage(
                        content=(
                            "⚠️ The AI service is temporarily busy due to rate limiting. "
                            "Please wait 30–60 seconds and try again."
                        )
                    )
                )
            elif "API_KEY" in err_str.upper() or "INVALID_ARGUMENT" in err_str:
                state["messages"].append(
                    AIMessage(
                        content=(
                            "⚠️ The AI service could not be reached (invalid or missing API key). "
                            "Please check the GOOGLE_API_KEY in backend/.env."
                        )
                    )
                )
            else:
                state["messages"].append(
                    AIMessage(
                        content=(
                            f"⚠️ The AI service returned an error: {err_str[:200]}. "
                            "Please try again in a moment."
                        )
                    )
                )
            return state

        tool_name = plan.get("tool", "")
        if tool_name not in _WRITE_TOOL_NAMES:
            self.log_error(f"LLM returned invalid tool name: {tool_name}")
            state["messages"].append(
                AIMessage(
                    content=(
                        "I could not identify a valid write action from your request. "
                        "Please specify **create**, **update**, or **delete**."
                    )
                )
            )
            return state

        params = plan.get("params") or {}
        project_id = str(params.get("project_id") or "").strip()
        task_id = str(params.get("task_id") or "").strip()

        if not project_id or not project_id.isdigit():

            short_ctx = state.get("short_term_context") or {}
            long_ctx = state.get("long_term_context") or {}
            fallback_pid = (
                str(short_ctx.get("last_project_id") or "")
                or str(long_ctx.get("preferred_project_id") or "")
            ).strip()
            if fallback_pid and fallback_pid.isdigit():
                params["project_id"] = fallback_pid
                plan["params"] = params
                self.log_info("Resolved project_id from memory context", pid=fallback_pid)
            else:
                state["messages"].append(
                    AIMessage(
                        content=(
                            "❓ I need to know **which project** to use for this action.\n\n"
                            "Please say something like:\n"
                            '- "Create a task called X **in project [project name]**"\n'
                            '- "Delete task Y **from project [project name]**"\n\n'
                            "Or first ask me to **List my projects** so you can see the available project names."
                        )
                    )
                )
                return state

        if tool_name in ("update_task", "delete_task") and not task_id:
            state["messages"].append(
                AIMessage(
                    content=(
                        "❓ I need the **task ID** to update or delete a task.\n\n"
                        "Please ask me to **list tasks** in the project first so you can see the task IDs."
                    )
                )
            )
            return state

        if tool_name == "create_task" and not str(params.get("name") or "").strip():
            state["messages"].append(
                AIMessage(
                    content="❓ What should the new task be **named**? Please specify a task name."
                )
            )
            return state

        description = plan.get("description") or f"perform: {tool_name}"
        state["pending_action"] = plan
        state["awaiting_confirmation"] = True

        self.log_info("Plan ready, awaiting confirmation", tool=tool_name)
        state["messages"].append(
            AIMessage(
                content=(
                    f"**Confirmation required** ✋\n\n"
                    f"I am about to **{description}**\n\n"
                    "Please click **Yes, Proceed** to confirm or **Cancel** to abort.\n"
                    "_No changes have been made yet._"
                )
            )
        )
        return state

    async def _execute_phase(self, state: dict) -> dict:
        """Execute the confirmed plan, or cancel cleanly."""
        if not state.get("confirmed"):
            self.log_info("User cancelled the pending action")
            state["awaiting_confirmation"] = False
            state["pending_action"] = {}
            state["messages"].append(
                AIMessage(content="❌ **Cancelled.** No changes were made.")
            )
            return state

        plan = state.get("pending_action") or {}
        tool_name: str = plan.get("tool", "")
        params: dict = dict(plan.get("params") or {})

        params["access_token"] = state["access_token"]
        params["portal_id"] = state["portal_id"]

        tool = _TOOL_MAP.get(tool_name)
        if tool is None:
            self.log_error(f"Cannot execute unknown tool: {tool_name}")
            state["awaiting_confirmation"] = False
            state["pending_action"] = {}
            state["messages"].append(
                AIMessage(content=f"⚠️ Cannot execute unknown action: `{tool_name}`.")
            )
            return state

        self.log_info("Executing confirmed action", tool=tool_name, params=list(params.keys()))

        try:
            result = await tool.ainvoke(params)
            state["messages"].append(
                AIMessage(
                    content=(
                        f"✅ **Done!** The action completed successfully.\n\n"
                        f"**Result:** {self._summarise_result(result)}"
                    )
                )
            )
        except Exception as exc:
            self.log_error("Tool execution failed", exc=exc)
            err_str = str(exc)

            if "403" in err_str or "Forbidden" in err_str:
                friendly = (
                    "⚠️ **Permission denied** — your Zoho OAuth token does not have write access.\n\n"
                    "Please **log out and log in again** to refresh your permissions, "
                    "then try the action again."
                )
            elif "404" in err_str or "Not Found" in err_str:
                friendly = (
                    "⚠️ **Not found** — the project or task ID was not recognised by Zoho.\n\n"
                    "Please ask me to **List my projects** / **List tasks** first "
                    "to get the correct IDs."
                )
            elif "400" in err_str or "Bad Request" in err_str:
                friendly = (
                    "⚠️ **Bad request** — Zoho rejected the parameters.\n\n"
                    f"Details: `{err_str[:300]}`\n\n"
                    "Please check the task name, date format (YYYY-MM-DD), and priority value."
                )
            elif "401" in err_str or "Unauthorized" in err_str:
                friendly = (
                    "⚠️ **Session expired** — your Zoho access token is no longer valid.\n\n"
                    "Please **log out and log in again** to get a fresh token."
                )
            else:
                friendly = (
                    f"⚠️ The action failed: `{err_str[:300]}`\n\n"
                    "No changes were applied. Please try again."
                )
            state["messages"].append(AIMessage(content=friendly))
        finally:
            state["awaiting_confirmation"] = False
            state["pending_action"] = {}

        return state

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        """Remove ```json … ``` or ``` … ``` fences from LLM output."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        return text

    @staticmethod
    def _summarise_result(result: str) -> str:
        """Turn raw JSON tool output into a brief readable summary."""
        try:
            data = json.loads(result)
            if isinstance(data, dict):

                inner = data.get("tasks") or data.get("task") or data.get("project") or data
                if isinstance(inner, list) and inner:
                    inner = inner[0]
                if isinstance(inner, dict):
                    for key in ("name", "id", "deleted", "status", "message"):
                        if key in inner:
                            return f"`{key}`: {inner[key]}"
            return str(data)[:200]
        except (json.JSONDecodeError, TypeError):
            return str(result)[:200]

    @staticmethod
    def _last_user_text(messages: list) -> str:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
        return ""