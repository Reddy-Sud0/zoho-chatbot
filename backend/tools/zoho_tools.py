"""
tools/zoho_tools.py
────────────────────
LangChain tool definitions for all 8 Zoho Projects operations.

Each tool is a thin async wrapper around ``ZohoClient``.  Tools carry
no business logic — they simply translate typed parameters into the
correct ``ZohoClient`` method call and return serialised JSON.

Tools are split by responsibility:

  READ tools  (used by QueryAgent only)
  ──────────────────────────────────────
    list_projects       – all projects for the authenticated user
    list_tasks          – tasks in a project with optional filters
    get_task_details    – full detail of one task
    list_project_members – members + roles in a project
    get_task_utilisation – task-load summary per member

  WRITE tools  (used by ActionAgent only, after HIL confirmation)
  ────────────────────────────────────────────────────────────────
    create_task  – create a new task
    update_task  – update status / assignee / due-date / priority
    delete_task  – soft-delete (move to trash)

Authentication
──────────────
``access_token`` and ``portal_id`` are injected into every tool call
by the agents from ``AgentState`` — users never see or provide them.
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import tool

from zoho.zoho_client import ZohoClient


# ── READ tools ────────────────────────────────────────────────────

@tool
async def list_projects(access_token: str, portal_id: str) -> str:
    """
    Fetch all Zoho Projects for the authenticated user's portal.

    Returns a JSON array of project objects, each containing:
    ``id``, ``name``, ``status``, ``description``.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.list_projects()
    return json.dumps(data, ensure_ascii=False)


@tool
async def list_tasks(
    access_token: str,
    portal_id: str,
    project_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """
    List tasks in a project with optional filters.

    Args:
        project_id: ID of the Zoho project.
        status:     Filter by task status (e.g. "open", "closed").
        assignee:   Filter by assignee name or user ID.
        due_date:   Filter by due date in YYYY-MM-DD format.

    Returns a JSON array of task objects.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    filters: dict = {}
    if status:
        filters["status"] = status
    if assignee:
        filters["owner"] = assignee
    if due_date:
        filters["due_date"] = due_date  # BUG FIX: was silently dropped before
    data = await client.list_tasks(project_id=project_id, filters=filters)
    return json.dumps(data, ensure_ascii=False)


@tool
async def get_task_details(
    access_token: str,
    portal_id: str,
    project_id: str,
    task_id: str,
) -> str:
    """
    Fetch full details of a single task by its ID.

    Returns a JSON object with all task fields including description,
    status, assignee, due date, priority, and subtasks.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.get_task_details(project_id=project_id, task_id=task_id)
    return json.dumps(data, ensure_ascii=False)


@tool
async def list_project_members(
    access_token: str,
    portal_id: str,
    project_id: str,
) -> str:
    """
    Get all members of a project along with their roles.

    Returns a JSON array of user objects containing ``name``, ``email``,
    and ``role``.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.list_project_members(project_id=project_id)
    return json.dumps(data, ensure_ascii=False)


@tool
async def get_task_utilisation(
    access_token: str,
    portal_id: str,
    project_id: str,
) -> str:
    """
    Summarise task load per team member across a project.

    Returns a JSON object mapping member name → number of assigned tasks,
    sorted descending (most-loaded member first).
    Unassigned tasks appear under the key "Unassigned".
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.get_task_utilisation(project_id=project_id)
    return json.dumps(data, ensure_ascii=False)


# ── WRITE tools ───────────────────────────────────────────────────

@tool
async def create_task(
    access_token: str,
    portal_id: str,
    project_id: str,
    name: str,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """
    Create a new task in a Zoho project.

    Args:
        project_id: Target project ID.
        name:       Task name (required).
        assignee:   Assignee user ID or name (optional).
        due_date:   Due date in YYYY-MM-DD format (optional).
        priority:   One of "High", "Medium", "Low" (optional).

    Returns a JSON object representing the created task.

    ⚠️  ALWAYS requires human confirmation before this tool is called.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    payload: dict = {"name": name}
    if assignee:
        payload["person_responsible"] = assignee
    if due_date:
        payload["due_date"] = due_date
    if priority:
        payload["priority"] = priority
    data = await client.create_task(project_id=project_id, payload=payload)
    return json.dumps(data, ensure_ascii=False)


@tool
async def update_task(
    access_token: str,
    portal_id: str,
    project_id: str,
    task_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """
    Update one or more fields of an existing task.

    Args:
        project_id: Project that owns the task.
        task_id:    ID of the task to update.
        status:     New status name or numeric id (optional).
        assignee:   New assignee user ID or name (optional).
        due_date:   New due date in YYYY-MM-DD format (optional).
        priority:   One of "High", "Medium", "Low" (optional).

    Returns a JSON object representing the updated task.

    ⚠️  ALWAYS requires human confirmation before this tool is called.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    payload: dict = {}
    if status:
        payload["status"] = status
    if assignee:
        payload["person_responsible"] = assignee  # BUG FIX: was dropped before
    if due_date:
        payload["due_date"] = due_date
    if priority:
        payload["priority"] = priority
    data = await client.update_task(
        project_id=project_id, task_id=task_id, payload=payload
    )
    return json.dumps(data, ensure_ascii=False)


@tool
async def delete_task(
    access_token: str,
    portal_id: str,
    project_id: str,
    task_id: str,
) -> str:
    """
    Delete (soft-delete / trash) a task by its ID.

    The task is moved to the portal trash and can be restored within
    the Zoho Projects UI.  Returns ``{"deleted": true}`` on success.

    ⚠️  ALWAYS requires explicit human confirmation before this tool is called.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    ok = await client.delete_task(project_id=project_id, task_id=task_id)
    return json.dumps({"deleted": ok}, ensure_ascii=False)
