from __future__ import annotations

import json
from typing import Annotated, List, TypedDict, Optional, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from tools.zoho_tools import (
    list_projects,
    list_tasks,
    get_task_details,
    list_project_members,
    get_task_utilisation,
    create_task,
    update_task,
    delete_task,
)


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    session_id: str
    access_token: str
    portal_id: str
    route: str
    pending_action: dict
    awaiting_confirmation: bool
    confirmed: bool
    short_term_context: dict
    long_term_context: dict


def _llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


def _last_user_text(messages: list[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


def _route_by_keywords(message: str) -> str:
    lower = message.lower()
    write_hints = (
        "create",
        "add ",
        "update",
        "delete",
        "remove",
        "assign",
        "change",
        "modify",
        "mark ",
        "set ",
    )
    if any(h in lower for h in write_hints):
        return "action"
    return "query"


async def router_node(state: AgentState) -> AgentState:
    """
    Send the last user message to Claude with this system prompt:

    'You are a router. Classify the user message as either READ or WRITE.
    READ = listing, showing, fetching, getting information
    WRITE = creating, updating, deleting, assigning, changing
    Reply with ONLY one word: READ or WRITE'

    Set state["route"] = "query" or "action"
    """
    msg = _last_user_text(state["messages"])
    llm = _llm()
    res = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a router. Classify the user message as either READ or WRITE.\n"
                    "READ = listing, showing, fetching, getting information\n"
                    "WRITE = creating, updating, deleting, assigning, changing\n"
                    "Reply with ONLY one word: READ or WRITE"
                )
            ),
            HumanMessage(content=msg),
        ]
    )
    label = str(res.content).strip().upper()
    if "WRITE" in label:
        state["route"] = "action"
    elif "READ" in label:
        state["route"] = "query"
    else:
        state["route"] = _route_by_keywords(msg)
    return state


async def _run_tool_loop(llm, tools: list, messages: list[BaseMessage]) -> AIMessage:
    bound = llm.bind_tools(tools)
    current: list[BaseMessage] = list(messages)
    for _ in range(6):
        ai = await bound.ainvoke(current)
        current.append(ai)
        tool_calls = getattr(ai, "tool_calls", None) or []
        if not tool_calls:
            return ai
        for call in tool_calls:
            name = call.get("name")
            args = call.get("args") or {}
            tool = next((t for t in tools if t.name == name), None)
            if tool is None:
                current.append(AIMessage(content=f"Tool not found: {name}"))
                continue
            try:
                out = await tool.ainvoke(args)
            except Exception as exc:
                out = json.dumps({"error": str(exc)})
            current.append(AIMessage(content=str(out)))
    return AIMessage(content="I couldn't complete the request due to too many tool steps.")


async def query_node(state: AgentState) -> AgentState:
    """
    Read-only agent.
    """
    llm = _llm()
    tools = [list_projects, list_tasks, get_task_details, list_project_members, get_task_utilisation]
    msg = _last_user_text(state["messages"])
    sys = (
        "You are a Zoho Projects assistant. You can only READ data.\n"
        "You have access to these tools: list_projects, list_tasks, get_task_details, "
        "list_project_members, get_task_utilisation.\n\n"
        f"Context from memory:\n{json.dumps(state.get('short_term_context') or {}, ensure_ascii=False)}\n"
        f"{json.dumps(state.get('long_term_context') or {}, ensure_ascii=False)}\n\n"
        "Use the right tool, get the data, and return a clear friendly response.\n"
        "Format for chat UI using markdown only:\n"
        "- Start with a short sentence.\n"
        "- Use bullet lists (* item) for multiple projects/tasks.\n"
        "- Never return JSON, Python dict/list, or code blocks.\n"
        "- Never include signatures or metadata."
    )
    ai = await _run_tool_loop(
        llm,
        tools,
        [
            SystemMessage(content=sys),
            HumanMessage(
                content=(
                    f"{msg}\n\n"
                    f"access_token={state['access_token']}\nportal_id={state['portal_id']}"
                )
            ),
        ],
    )
    state["messages"].append(ai)
    return state


async def action_node(state: AgentState) -> AgentState:
    """
    Action agent — WITH HIL (two-step: propose → confirm → execute).
    Tools available: create_task, update_task, delete_task
    """
    llm = _llm()
    tools = [create_task, update_task, delete_task]
    write_tools = {t.name for t in tools}

    # Step 2: user already confirmed or cancelled via /chat (confirmed flag)
    if state.get("awaiting_confirmation") and state.get("pending_action"):
        if not state.get("confirmed"):
            state["awaiting_confirmation"] = False
            state["pending_action"] = {}
            state["messages"].append(AIMessage(content="Cancelled. No changes were made."))
            return state

        pending = state.get("pending_action") or {}
        tool_name = pending.get("tool")
        params = dict(pending.get("params") or {})
        params.setdefault("access_token", state["access_token"])
        params.setdefault("portal_id", state["portal_id"])

        tool = next((t for t in tools if t.name == tool_name), None)
        if not tool:
            state["awaiting_confirmation"] = False
            state["pending_action"] = {}
            state["messages"].append(AIMessage(content=f"Unknown action tool: {tool_name}"))
            return state

        out = await tool.ainvoke(params)
        state["awaiting_confirmation"] = False
        state["pending_action"] = {}
        state["messages"].append(
            AIMessage(content=f"Done! The action was completed successfully.\n\nResult: {out}")
        )
        return state

    # Step 1: plan write action and ask for confirmation (no tool execution)
    sys = (
        "You are a Zoho Projects assistant that can ONLY perform WRITE actions.\n"
        "Your job: decide which tool to call and with what parameters.\n"
        "DO NOT execute the tool yet.\n"
        "Return ONLY a JSON object with keys: tool, description, params.\n"
        "tool must be one of: create_task, update_task, delete_task.\n"
        "params must include required ids (project_id, and task_id if needed).\n"
        "For create_task params must include: project_id, name.\n"
        "Use project_id from short_term_context preferred_project_id when user does not specify.\n"
        f"short_term_context={json.dumps(state.get('short_term_context') or {}, ensure_ascii=False)}\n"
        f"long_term_context={json.dumps(state.get('long_term_context') or {}, ensure_ascii=False)}"
    )
    msg = _last_user_text(state["messages"])
    res = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=msg)])
    raw = str(res.content).strip()
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()
    try:
        pending = json.loads(raw)
    except Exception:
        pending = {
            "tool": "create_task",
            "description": "perform the requested change",
            "params": {},
        }

    tool_name = pending.get("tool")
    if tool_name not in write_tools:
        state["messages"].append(
            AIMessage(content="I could not determine a valid write action. Please specify create, update, or delete.")
        )
        return state

    state["pending_action"] = pending
    state["awaiting_confirmation"] = True
    description = pending.get("description") or f"run {tool_name}"
    state["messages"].append(
        AIMessage(
            content=(
                f"**Confirmation required**\n\n"
                f"I am about to: {description}\n\n"
                "Please click **Yes, proceed** or **Cancel** below."
            )
        )
    )
    return state


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router_node", router_node)
    graph.add_node("query_node", query_node)
    graph.add_node("action_node", action_node)

    graph.add_edge(START, "router_node")
    graph.add_conditional_edges("router_node", lambda s: s["route"], {"query": "query_node", "action": "action_node"})
    graph.add_edge("query_node", END)
    graph.add_edge("action_node", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


agent_graph = build_agent_graph()
