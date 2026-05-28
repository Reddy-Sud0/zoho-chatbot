from __future__ import annotations

from collections import Counter
from typing import Any
import httpx

from config import settings


def _api_v3_base() -> str:
    base = settings.ZOHO_API_BASE.rstrip("/")
    if base.endswith("/restapi"):
        return base.replace("/restapi", "/api/v3")
    if "/api/v3" in base:
        return base
    return "https://projectsapi.zoho.in/api/v3"


def _as_list(payload: Any) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if payload.get("error"):
            return []
        for key in ("projects", "projects_list", "tasks", "tasks_list", "users", "users_list", "items", "data"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return []


class ZohoClient:
    def __init__(self, access_token: str, portal_id: str):
        self.api_base = _api_v3_base()
        self.headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Accept": "application/json",
        }
        self.portal_id = portal_id

    async def _get_json(self, url: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, params=params, timeout=30)
            if resp.status_code >= 400:
                return {"error": resp.text[:300], "status_code": resp.status_code}
            try:
                return resp.json()
            except Exception:
                return {"error": "non_json_response", "body": (resp.text or "")[:300]}

    async def list_portals(self) -> list:
        """GET /api/v3/portals"""
        url = f"{self.api_base}/portals"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return _as_list(resp.json())

    async def list_projects(self) -> list:
        """GET /api/v3/portal/{portal_id}/projects"""
        url = f"{self.api_base}/portal/{self.portal_id}/projects"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return _as_list(resp.json())

    async def create_project(self, name: str, description: str = "") -> dict:
        """POST /api/v3/portal/{portal_id}/projects"""
        url = f"{self.api_base}/portal/{self.portal_id}/projects"
        body = {"name": name, "project_type": "active"}
        if description:
            body["description"] = description
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"project": data}

    async def list_tasks(self, project_id: str, filters: dict = {}) -> list:
        """GET /api/v3/portal/{portal_id}/projects/{project_id}/tasks"""
        url = f"{self.api_base}/portal/{self.portal_id}/projects/{project_id}/tasks"
        params: dict[str, Any] = {}
        if filters.get("status"):
            params["status"] = filters["status"]
        if filters.get("owner"):
            params["owner"] = filters["owner"]
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            return _as_list(resp.json())

    async def get_task_details(self, project_id: str, task_id: str) -> dict:
        url = f"{self.api_base}/portal/{self.portal_id}/projects/{project_id}/tasks/{task_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"task": data}

    async def create_task(self, project_id: str, payload: dict) -> dict:
        url = f"{self.api_base}/portal/{self.portal_id}/projects/{project_id}/tasks"
        body = {"name": payload.get("name")}
        if payload.get("description"):
            body["description"] = payload["description"]
        if payload.get("priority"):
            body["priority"] = payload["priority"]
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"task": data}

    async def update_task(self, project_id: str, task_id: str, payload: dict) -> dict:
        url = f"{self.api_base}/portal/{self.portal_id}/projects/{project_id}/tasks/{task_id}"
        body = {}
        if payload.get("name"):
            body["name"] = payload["name"]
        if payload.get("status"):
            body["status"] = {"id": payload["status"]} if str(payload["status"]).isdigit() else {"name": payload["status"]}
        if payload.get("priority"):
            body["priority"] = payload["priority"]
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"task": data}

    async def delete_task(self, project_id: str, task_id: str) -> bool:
        url = f"{self.api_base}/portal/{self.portal_id}/projects/{project_id}/tasks/{task_id}/trash"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
        return True

    async def list_project_members(self, project_id: str) -> list:
        url = f"{self.api_base}/portal/{self.portal_id}/projects/{project_id}/users"
        data = await self._get_json(url)
        members = _as_list(data)
        if members:
            return members
        # Fallback: portal-level users
        portal_users_url = f"{self.api_base}/portal/{self.portal_id}/users"
        portal_data = await self._get_json(portal_users_url)
        return _as_list(portal_data)

    async def get_task_utilisation(self, project_id: str) -> dict:
        tasks = await self.list_tasks(project_id, {})
        counts: Counter[str] = Counter()
        for t in tasks:
            owner = (
                (t.get("owner") or {}).get("name")
                if isinstance(t.get("owner"), dict)
                else t.get("person_responsible_name")
            ) or t.get("owner_name") or t.get("owner") or "Unassigned"
            counts[str(owner)] += 1
        return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
