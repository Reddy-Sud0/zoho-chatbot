from __future__ import annotations

from zoho.zoho_client import ZohoClient

DEMO_PROJECT_NAMES = [
    "Website Redesign",
    "Mobile App Launch",
    "API Integration",
    "Marketing Campaign",
    "Internal Operations",
]


async def ensure_demo_projects(access_token: str, portal_id: str, target_count: int = 5) -> dict:
    """
    Ensure at least `target_count` projects exist in the portal.
    Creates missing demo projects when the account has none/few.
    """
    client = ZohoClient(access_token=access_token, portal_id=portal_id)
    existing = await client.list_projects()
    created: list[str] = []

    if len(existing) >= target_count:
        return {
            "portal_id": portal_id,
            "existing_count": len(existing),
            "created": created,
            "message": f"Already have {len(existing)} project(s).",
        }

    need = target_count - len(existing)
    existing_names = {str(p.get("name", "")).lower() for p in existing}

    for name in DEMO_PROJECT_NAMES:
        if need <= 0:
            break
        if name.lower() in existing_names:
            continue
        await client.create_project(name=name, description=f"Auto-created demo project: {name}")
        created.append(name)
        need -= 1

    final_projects = await client.list_projects()
    return {
        "portal_id": portal_id,
        "existing_count": len(final_projects),
        "created": created,
        "projects": [{"id": p.get("id"), "name": p.get("name")} for p in final_projects],
        "message": f"Ready with {len(final_projects)} project(s).",
    }
