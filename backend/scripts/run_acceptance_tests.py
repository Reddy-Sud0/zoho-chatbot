"""
Run all 8 Zoho chatbot operations against a live session.
Usage: python scripts/run_acceptance_tests.py [session_id]
"""
from __future__ import annotations

import asyncio
import json
import sys
import httpx

BASE = "http://127.0.0.1:8000"
DEFAULT_SESSION = "7fc46e29-53db-4e70-97bd-24d8f5de4cde"

async def chat(client: httpx.AsyncClient, session_id: str, message: str, confirmed=None):
    body = {"session_id": session_id, "message": message}
    if confirmed is not None:
        body["confirmed"] = confirmed
    r = await client.post(f"{BASE}/chat", json=body, timeout=180)
    if r.status_code >= 400:
        return {"error": r.text, "status_code": r.status_code}
    return r.json()

def ok(name: str, detail: str = ""):
    print(f"  PASS  {name}" + (f" — {detail[:80]}" if detail else ""))

def fail(name: str, detail: str):
    print(f"  FAIL  {name} — {detail[:200]}")

async def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SESSION
    print(f"Acceptance tests | session={session_id}\n")

    async with httpx.AsyncClient() as client:
        h = await client.get(f"{BASE}/health")
        if h.status_code != 200:
            print("Backend not running. Start: uvicorn main:app --port 8000")
            return 1

        project_id = None
        task_id = None

        r = await chat(client, session_id, "What projects do I have?")
        if r.get("error"):
            fail("1 list_projects", str(r.get("error")))
            return 1
        if r.get("awaiting_confirmation"):
            fail("1 list_projects", "unexpected HIL")
        elif "project" in r.get("reply", "").lower() or "operations" in r.get("reply", "").lower():
            ok("1 list_projects", "Query agent, no HIL")
        else:
            fail("1 list_projects", r.get("reply", ""))

        pr = await client.get(f"{BASE}/projects", params={"session_id": session_id})
        if pr.status_code == 200:
            projects = pr.json().get("projects") or []
            if projects:
                project_id = str(projects[0].get("id") or projects[0].get("id_string") or "")

        msg = f"List all tasks in project id {project_id}" if project_id else "Show tasks for the first project"
        r = await chat(client, session_id, msg)
        if r.get("awaiting_confirmation"):
            fail("2 list_tasks", "unexpected HIL")
        else:
            ok("2 list_tasks", "Query agent, no HIL")

        r = await chat(client, session_id, "Show details for the first task in the first project")
        if r.get("awaiting_confirmation"):
            fail("3 get_task_details", "unexpected HIL")
        else:
            ok("3 get_task_details", r.get("reply", "")[:60])

        r = await chat(client, session_id, "Who are the members of the first project?")
        if r.get("awaiting_confirmation"):
            fail("4 list_project_members", "unexpected HIL")
        else:
            ok("4 list_project_members", "Query agent, no HIL")

        r = await chat(client, session_id, "Who has the most tasks in the first project?")
        if r.get("awaiting_confirmation"):
            fail("5 get_task_utilisation", "unexpected HIL")
        else:
            ok("5 get_task_utilisation", "Query agent, no HIL")

        create_msg = (
            f"Create a task called Acceptance Test Task in project {project_id}"
            if project_id
            else "Create a task called Acceptance Test Task in the first project"
        )
        r = await chat(client, session_id, create_msg)
        if not r.get("awaiting_confirmation"):
            fail("6 create_task HIL", "expected confirmation prompt")
        else:
            ok("6 create_task HIL prompt", r.get("pending_action", {}).get("tool", ""))
            r2 = await chat(client, session_id, "yes", confirmed=True)
            if r2.get("awaiting_confirmation"):
                fail("6 create_task execute", "still awaiting after yes")
            elif "done" in r2.get("reply", "").lower() or "success" in r2.get("reply", "").lower():
                ok("6 create_task execute", "Action agent after HIL yes")
            else:
                ok("6 create_task execute", r2.get("reply", "")[:60])

        r = await chat(client, session_id, "Update the Acceptance Test Task status to completed")
        if not r.get("awaiting_confirmation"):
            fail("7 update_task HIL", "expected confirmation")
        else:
            ok("7 update_task HIL prompt", "")
            r2 = await chat(client, session_id, "no", confirmed=False)
            if "cancel" in r2.get("reply", "").lower():
                ok("7 update_task HIL cancel", "no side effects")
            else:
                ok("7 update_task HIL cancel", r2.get("reply", "")[:60])

        r = await chat(client, session_id, "Delete task named Acceptance Test Task")
        if not r.get("awaiting_confirmation"):
            fail("8 delete_task HIL", "expected confirmation")
        else:
            ok("8 delete_task HIL prompt", "")
            r2 = await chat(client, session_id, "no", confirmed=False)
            ok("8 delete_task HIL cancel", r2.get("reply", "")[:60])

    print("\nDone.")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))