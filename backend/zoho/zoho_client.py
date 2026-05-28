"""
zoho/zoho_client.py
────────────────────
ZohoClient — typed, async HTTP client for the Zoho Projects API v3.

All methods are fully async (httpx.AsyncClient).  The client is
stateless between calls — create a new instance per request or share
one within a request context.

API reference: https://www.zoho.com/projects/help/rest-api/

Error handling
──────────────
Every method that calls the API will raise ``httpx.HTTPStatusError``
on 4xx/5xx responses via ``resp.raise_for_status()``, except for
``_get_json()`` which returns an error dict instead of raising —
this is intentional so list methods can degrade gracefully.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────

def _api_v3_base() -> str:
    """Resolve the canonical Zoho Projects API v3 base URL from settings."""
    base = settings.ZOHO_API_BASE.rstrip("/")
    if "/api/v3" in base:
        return base
    # Legacy setting may end with /restapi — normalise it.
    if base.endswith("/restapi"):
        return base.replace("/restapi", "/api/v3")
    return "https://projectsapi.zoho.in/api/v3"


def _as_list(payload: Any) -> list:
    """
    Coerce an arbitrary Zoho API response body into a list.

    Zoho wraps arrays under different keys depending on the endpoint
    (``projects``, ``tasks``, ``users``, ``items``, etc.).  This helper
    walks those keys so callers always get a plain ``list``.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if payload.get("error"):
            logger.warning("Zoho API returned error payload: %s", payload)
            return []
        for key in (
            "projects", "projects_list",
            "tasks", "tasks_list",
            "users", "users_list",
            "items", "data",
        ):
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return []


# ── Client class ──────────────────────────────────────────────────

class ZohoClient:
    """
    Async client for Zoho Projects REST API v3.

    Args:
        access_token: A valid Zoho OAuth access token.
        portal_id:    The Zoho Projects portal (workspace) ID.

    All HTTP calls use ``httpx.AsyncClient`` with a 30-second timeout.
    """

    def __init__(self, access_token: str, portal_id: str) -> None:
        self._base = _api_v3_base()
        self._portal = portal_id
        self._headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Accept": "application/json",
        }

    # ── Internal helpers ─────────────────────────────────────────

    @property
    def _json_headers(self) -> dict:
        """Headers for JSON POST/PATCH requests."""
        return {**self._headers, "Content-Type": "application/json"}

    def _portal_url(self, *parts: str) -> str:
        """Build a URL rooted at /portal/{portal_id}/…"""
        path = "/".join(str(p).strip("/") for p in parts)
        return f"{self._base}/portal/{self._portal}/{path}"

    async def _get_json(self, url: str, params: Optional[dict] = None) -> Any:
        """
        GET a URL and return the parsed JSON body.

        On HTTP error, logs and returns ``{"error": ..., "status_code": ...}``
        instead of raising so list-type callers can degrade gracefully.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, headers=self._headers, params=params, timeout=30
            )
        if resp.status_code >= 400:
            logger.error("GET %s → HTTP %s", url, resp.status_code)
            return {"error": resp.text[:300], "status_code": resp.status_code}
        try:
            return resp.json()
        except Exception:
            return {"error": "non_json_response", "body": resp.text[:300]}

    # ── Portal ───────────────────────────────────────────────────

    async def list_portals(self) -> list:
        """Return all Zoho Projects portals accessible by this token."""
        url = f"{self._base}/portals"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, timeout=30)
            resp.raise_for_status()
        return _as_list(resp.json())

    # ── Projects ─────────────────────────────────────────────────

    async def list_projects(self) -> list:
        """Return all projects in the portal."""
        url = self._portal_url("projects")
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, timeout=30)
            resp.raise_for_status()
        return _as_list(resp.json())

    async def create_project(self, name: str, description: str = "") -> dict:
        """Create a new project and return the created project object."""
        url = self._portal_url("projects")
        body: dict[str, Any] = {"name": name, "project_type": "active"}
        if description:
            body["description"] = description
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._json_headers, json=body, timeout=30)
            resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"project": data}

    # ── Tasks ────────────────────────────────────────────────────

    async def list_tasks(
        self,
        project_id: str,
        filters: Optional[dict] = None,
    ) -> list:
        """
        Return tasks for *project_id*, optionally filtered.

        Supported filter keys (all optional):
            status   – e.g. "open", "closed", "in_progress"
            owner    – assignee name or user ID
            due_date – ISO date string, e.g. "2025-12-31"
        """
        url = self._portal_url("projects", project_id, "tasks")
        params: dict[str, Any] = {}
        if filters:
            if filters.get("status"):
                params["status"] = filters["status"]
            if filters.get("owner"):
                params["owner"] = filters["owner"]
            if filters.get("due_date"):
                params["due_date"] = filters["due_date"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, headers=self._headers, params=params, timeout=30
            )
            resp.raise_for_status()
        return _as_list(resp.json())

    async def get_task_details(self, project_id: str, task_id: str) -> dict:
        """Return full detail of a single task."""
        url = self._portal_url("projects", project_id, "tasks", task_id)
        data = await self._get_json(url)
        return data if isinstance(data, dict) else {"task": data}

    async def create_task(self, project_id: str, payload: dict) -> dict:
        """
        Create a task in *project_id*.

        Recognised payload keys:
            name (required), description, priority, person_responsible, due_date
        """
        url = self._portal_url("projects", project_id, "tasks")
        body: dict[str, Any] = {"name": payload["name"]}

        if payload.get("description"):
            body["description"] = payload["description"]
        if payload.get("priority"):
            body["priority"] = payload["priority"]
        if payload.get("due_date"):
            body["due_date"] = payload["due_date"]
        if payload.get("person_responsible"):
            body["person_responsible"] = payload["person_responsible"]

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._json_headers, json=body, timeout=30)
            resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"task": data}

    async def update_task(self, project_id: str, task_id: str, payload: dict) -> dict:
        """
        Patch a task's mutable fields.

        Recognised payload keys:
            name, status (name or numeric id), priority,
            due_date (YYYY-MM-DD), person_responsible (user id or name)
        """
        url = self._portal_url("projects", project_id, "tasks", task_id)
        body: dict[str, Any] = {}

        if payload.get("name"):
            body["name"] = payload["name"]

        if payload.get("status"):
            raw_status = payload["status"]
            # Zoho accepts either {"id": <int>} or {"name": <str>}
            body["status"] = (
                {"id": raw_status}
                if str(raw_status).isdigit()
                else {"name": raw_status}
            )

        if payload.get("priority"):
            body["priority"] = payload["priority"]

        if payload.get("due_date"):
            body["due_date"] = payload["due_date"]

        # ── BUG FIX: assignee was previously silently dropped ─────
        if payload.get("person_responsible"):
            body["person_responsible"] = payload["person_responsible"]

        async with httpx.AsyncClient() as client:
            resp = await client.patch(url, headers=self._json_headers, json=body, timeout=30)
            resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"task": data}

    async def delete_task(self, project_id: str, task_id: str) -> bool:
        """
        Move a task to the portal trash (soft delete).

        Returns ``True`` on success; raises ``httpx.HTTPStatusError`` on failure.
        """
        url = self._portal_url("projects", project_id, "tasks", task_id, "trash")
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers, timeout=30)
            resp.raise_for_status()
        return True

    # ── Members ──────────────────────────────────────────────────

    async def list_project_members(self, project_id: str) -> list:
        """
        Return members of *project_id*.

        Falls back to portal-level users if the project endpoint returns
        an empty list (common for newly created projects).
        """
        url = self._portal_url("projects", project_id, "users")
        data = await self._get_json(url)
        members = _as_list(data)
        if members:
            return members

        logger.info("No project-level members; falling back to portal users")
        portal_url = self._portal_url("users")
        portal_data = await self._get_json(portal_url)
        return _as_list(portal_data)

    # ── Utilisation ──────────────────────────────────────────────

    async def get_task_utilisation(self, project_id: str) -> dict:
        """
        Return a mapping of ``{member_name: task_count}`` for *project_id*.

        Sorted descending by task count so the most-loaded member is first.
        Unassigned tasks are grouped under the key ``"Unassigned"``.
        """
        tasks = await self.list_tasks(project_id)
        counts: Counter[str] = Counter()

        for task in tasks:
            owner_info = task.get("owner") or {}
            if isinstance(owner_info, dict):
                owner = owner_info.get("name") or ""
            else:
                owner = str(owner_info)

            owner = (
                owner
                or task.get("person_responsible_name", "")
                or task.get("owner_name", "")
                or "Unassigned"
            )
            counts[str(owner).strip() or "Unassigned"] += 1

        return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
