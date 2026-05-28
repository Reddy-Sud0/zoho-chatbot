"""
graph/agent_graph.py
────────────────────
LangGraph stateful graph wiring the three agent classes together.

Architecture
────────────
                ┌─────────────┐
    START ──►   │ router_node │
                └──────┬──────┘
                       │  state["route"]
              ┌────────┴────────┐
              │                 │
         "query"           "action"
              │                 │
       ┌──────▼──────┐   ┌──────▼──────┐
       │ query_node  │   │ action_node │
       └──────┬──────┘   └──────┬──────┘
              │                 │
              └────────┬────────┘
                      END

State schema (AgentState)
──────────────────────────
messages              – conversation history (accumulated via add_messages)
user_id               – DB primary key of the authenticated user
session_id            – UUID of the current browser session
access_token          – Zoho OAuth access token (refreshed upstream)
portal_id             – Zoho Projects portal id
route                 – "query" | "action"  (set by router)
pending_action        – { tool, description, params } or {}
awaiting_confirmation – True when HIL prompt is outstanding
confirmed             – True / False passed in by the frontend
short_term_context    – {key: value} from MemoryStore.get_all_short()
long_term_context     – {key: value} from MemoryStore.get_all_long()

Checkpointing
─────────────
MemorySaver is used so that LangGraph carries the full message history
between ainvoke() calls on the same thread_id (= session_id).  This
gives the LLM access to prior turns for free, complementing the
explicit short/long-term context injected per request.
"""

from __future__ import annotations

from typing import Annotated, Any, List

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agents import ActionAgent, QueryAgent, RouterAgent

# ── Singleton agent instances (one per process lifetime) ─────────
_router = RouterAgent()
_query = QueryAgent()
_action = ActionAgent()


# ── State schema ─────────────────────────────────────────────────

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


# ── Node wrappers (thin async functions that delegate to agents) ──

async def router_node(state: AgentState) -> AgentState:
    """Router node — delegates to RouterAgent.run()."""
    return await _router.run(state)  # type: ignore[arg-type]


async def query_node(state: AgentState) -> AgentState:
    """Query node — delegates to QueryAgent.run()."""
    return await _query.run(state)  # type: ignore[arg-type]


async def action_node(state: AgentState) -> AgentState:
    """Action node — delegates to ActionAgent.run()."""
    return await _action.run(state)  # type: ignore[arg-type]


def _select_agent(state: AgentState) -> str:
    """Conditional edge: read route flag and pick the next node."""
    return state.get("route", "query")


# ── Graph construction ────────────────────────────────────────────

def build_agent_graph() -> Any:
    """
    Build and compile the LangGraph stateful graph.

    Returns a compiled graph ready for ``await graph.ainvoke(state, config)``.
    """
    graph: StateGraph = StateGraph(AgentState)

    # Nodes
    graph.add_node("router_node", router_node)
    graph.add_node("query_node", query_node)
    graph.add_node("action_node", action_node)

    # Edges
    graph.add_edge(START, "router_node")
    graph.add_conditional_edges(
        "router_node",
        _select_agent,
        {"query": "query_node", "action": "action_node"},
    )
    graph.add_edge("query_node", END)
    graph.add_edge("action_node", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ── Module-level compiled graph (imported by main.py) ────────────
agent_graph = build_agent_graph()
