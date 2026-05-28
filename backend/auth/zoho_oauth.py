from __future__ import annotations

from urllib.parse import urlencode
import httpx

from config import settings


def _safe_json(resp: httpx.Response) -> dict:
    text = (resp.text or "").strip()
    if not text:
        return {
            "error": "empty_response",
            "status_code": resp.status_code,
            "url": str(resp.request.url),
            "body": "",
        }
    try:
        data = resp.json()
        if isinstance(data, list):
            return {"items": data}
        if isinstance(data, dict):
            return data
        return {"data": data}
    except Exception:
        return {
            "error": "non_json_response",
            "status_code": resp.status_code,
            "url": str(resp.request.url),
            "body": text[:500],
        }

# OAuth codes are single-use; browsers may hit /auth/callback twice.
_processed_codes: dict[str, str] = {}


class ZohoOAuth:
    def get_authorization_url(self) -> str:
        """
        Build and return the Zoho OAuth authorization URL.
        Scopes needed:
          ZohoProjects.portals.READ
          ZohoProjects.projects.READ
          ZohoProjects.tasks.ALL
          ZohoProjects.users.READ
        Use response_type=code, access_type=offline
        """
        params = {
            "scope": ",".join(
                [
                    "AaaServer.profile.READ",
                    "ZohoProjects.portals.READ",
                    "ZohoProjects.projects.READ",
                    "ZohoProjects.projects.CREATE",
                    "ZohoProjects.tasks.ALL",
                    "ZohoProjects.users.READ",
                ]
            ),
            "client_id": settings.ZOHO_CLIENT_ID,
            "response_type": "code",
            "access_type": "offline",
            "redirect_uri": settings.ZOHO_REDIRECT_URI,
            "prompt": "consent",
        }
        return f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/auth?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, accounts_url: str | None = None) -> dict:
        """
        POST to {ZOHO_ACCOUNTS_URL}/oauth/v2/token
        with grant_type=authorization_code, code=code,
        client_id, client_secret, redirect_uri
        Returns: { access_token, refresh_token, expires_in }
        """
        base = (accounts_url or settings.ZOHO_ACCOUNTS_URL).rstrip("/")
        url = f"{base}/oauth/v2/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
            "redirect_uri": settings.ZOHO_REDIRECT_URI.strip(),
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                data=data,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            payload = _safe_json(resp)
            if resp.status_code >= 400 or payload.get("error"):
                return payload
            return payload

    async def refresh_access_token(self, refresh_token: str, accounts_url: str | None = None) -> dict:
        """
        POST to {ZOHO_ACCOUNTS_URL}/oauth/v2/token
        with grant_type=refresh_token
        Returns new access_token and expires_in
        """
        base = (accounts_url or settings.ZOHO_ACCOUNTS_URL).rstrip("/")
        url = f"{base}/oauth/v2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data, timeout=30)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def remember_successful_code(code: str, redirect_url: str) -> None:
        _processed_codes[code] = redirect_url

    @staticmethod
    def get_redirect_for_code(code: str) -> str | None:
        return _processed_codes.get(code)

    async def get_zoho_user_info(self, access_token: str, accounts_url: str | None = None) -> dict | None:
        """
        GET https://accounts.zoho.in/oauth/user/info
        with Authorization: Zoho-oauthtoken {access_token}
        Returns: { ZUID, Email, Display_Name }
        """
        base = (accounts_url or settings.ZOHO_ACCOUNTS_URL).rstrip("/")
        url = f"{base}/oauth/user/info"
        async with httpx.AsyncClient() as client:
            # Zoho accounts user-info can vary by auth scheme depending on account/DC.
            for auth_header in (f"Zoho-oauthtoken {access_token}", f"Bearer {access_token}"):
                resp = await client.get(url, headers={"Authorization": auth_header}, timeout=30)
                if resp.status_code < 400:
                    data = _safe_json(resp)
                    if data.get("error"):
                        continue
                    return data
            return None

    async def get_portal_id(self, access_token: str) -> str:
        """
        GET /api/v3/portals
        Returns the first portal id (required for all project API calls).
        """
        base = settings.ZOHO_API_BASE.rstrip("/")
        if base.endswith("/restapi"):
            base = base.replace("/restapi", "/api/v3")
        if "/api/v3" not in base:
            base = "https://projectsapi.zoho.in/api/v3"

        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Accept": "application/json",
        }
        url = f"{base}/portals"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30)
            data = _safe_json(resp)
            if data.get("error") or resp.status_code >= 400:
                raise ValueError(
                    "Could not fetch Zoho Projects portal. "
                    f"HTTP {resp.status_code}: {data.get('body') or data.get('error')}. "
                    "Open https://projects.zoho.in and ensure Zoho Projects is enabled for your account."
                )

            portals = data.get("items") or data.get("portals") or data.get("data") or []
            if not portals:
                raise ValueError(
                    "No Zoho Projects portal found. Please sign up for Zoho Projects at "
                    "https://projects.zoho.in and try login again."
                )

            first = portals[0]
            portal_id = first.get("id_string") or first.get("id") or first.get("portal_id")
            if not portal_id:
                raise ValueError("Portal response received but portal id was missing.")
            return str(portal_id)
