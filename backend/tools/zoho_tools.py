from __future__ import annotations

import json
from typing import Optional
from langchain_core.tools import tool

from zoho.zoho_client import ZohoClient


@tool
async def list_projects(access_token: str, portal_id: str) -> str:
    """Fetch all Zoho Projects for the authenticated user"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.list_projects()
    return json.dumps(data)


@tool
async def list_tasks(
    access_token: str,
    portal_id: str,
    project_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
) -> str:
    """List tasks in a project. Optional filters: status, assignee"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    filters = {}
    if status:
        filters["status"] = status
    if assignee:
        filters["owner"] = assignee
    data = await client.list_tasks(project_id=project_id, filters=filters)
    return json.dumps(data)


@tool
async def get_task_details(access_token: str, portal_id: str, project_id: str, task_id: str) -> str:
    """Get full details of a single task by its ID"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.get_task_details(project_id=project_id, task_id=task_id)
    return json.dumps(data)


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
    """Create a new task in a Zoho project"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    payload = {"name": name}
    if assignee:
        payload["person_responsible"] = assignee
    if due_date:
        payload["due_date"] = due_date
    if priority:
        payload["priority"] = priority
    data = await client.create_task(project_id=project_id, payload=payload)
    return json.dumps(data)


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
    """Update an existing task's status, assignee, due date or priority"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    payload = {}
    if status:
        payload["status"] = status
    if assignee:
        payload["person_responsible"] = assignee
    if due_date:
        payload["due_date"] = due_date
    if priority:
        payload["priority"] = priority
    data = await client.update_task(project_id=project_id, task_id=task_id, payload=payload)
    return json.dumps(data)


@tool
async def delete_task(access_token: str, portal_id: str, project_id: str, task_id: str) -> str:
    """Delete a task. ALWAYS requires human confirmation before calling this."""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    ok = await client.delete_task(project_id=project_id, task_id=task_id)
    return json.dumps({"deleted": ok})


@tool
async def list_project_members(access_token: str, portal_id: str, project_id: str) -> str:
    """Get all members of a project along with their roles"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.list_project_members(project_id=project_id)
    return json.dumps(data)


@tool
async def get_task_utilisation(access_token: str, portal_id: str, project_id: str) -> str:
    """Summarise task load per member — who has how many tasks"""
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    data = await client.get_task_utilisation(project_id=project_id)
    return json.dumps(data)
