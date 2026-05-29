"""
main.py
────────
FastAPI application entry point for the Zoho AI Project Chatbot.

Endpoints
─────────
GET  /auth/login      – Redirect user to Zoho OAuth consent screen
GET  /auth/callback   – Exchange Zoho auth code for tokens; create session
POST /chat            – Main chat endpoint (authenticated via session_id)
GET  /health          – Liveness probe
GET  /projects        – Debug: list projects for the current session user

Authentication flow
────────────────────
1. Frontend calls GET /auth/login → backend redirects to Zoho OAuth.
2. Zoho redirects back to GET /auth/callback?code=… .
3. Callback exchanges the code for access + refresh tokens, persists
   them per user in SQLite, creates a session, and redirects the
   browser to the frontend /chat page with ?session_id=<uuid>.
4. Every subsequent POST /chat call includes session_id in the JSON
   body — the backend validates it, looks up the user, refreshes the
   token if needed, then invokes the LangGraph agent graph.

Token refresh
─────────────
``_ensure_fresh_token()`` silently refreshes the Zoho access token
when it will expire within 5 minutes, updating the DB row in place.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session as DbSession

from auth.zoho_oauth import ZohoOAuth
from config import settings
from database.db import get_db, init_db
from database.models import Session as UserSession
from database.models import Token, User
from graph.agent_graph import agent_graph
from memory.memory_store import MemoryStore
from schemas.chat_schema import ChatRequest, ChatResponse
from utils.message_format import normalize_reply_text
from zoho.bootstrap import ensure_demo_projects
from zoho.zoho_client import ZohoClient

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Zoho AI Project Chatbot",
    description=(
        "Multi-agent AI chatbot for Zoho Projects. "
        "Uses LangGraph (QueryAgent + ActionAgent + RouterAgent) "
        "with OAuth 2.0 per-user authentication and HIL confirmation."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def _startup() -> None:
    init_db()
    logger.info("Database initialised")

def _get_session(db: DbSession, session_id: str) -> UserSession:
    """Look up and return a session row, or raise 401."""
    sess = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid or expired session_id.")
    return sess

def _get_user(db: DbSession, user_id: str) -> User:
    """Look up and return a user row, or raise 401."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user

def _get_token(db: DbSession, user_id: str) -> Token:
    """Look up and return a token row, or raise 401."""
    token = db.query(Token).filter(Token.user_id == user_id).first()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="No OAuth token found. Please log in again.",
        )
    return token

async def _ensure_fresh_token(db: DbSession, token: Token) -> Token:
    """
    Silently refresh the Zoho access token if it will expire within
    5 minutes.  Updates the DB row in-place and returns the token.
    """
    if token.expires_at < datetime.utcnow() + timedelta(minutes=5):
        logger.info("Token expiring soon — refreshing for user %s", token.user_id)
        oauth = ZohoOAuth()
        refreshed = await oauth.refresh_access_token(token.refresh_token)
        token.access_token = refreshed["access_token"]
        token.expires_at = datetime.utcnow() + timedelta(
            seconds=int(refreshed.get("expires_in", 3600))
        )
        db.commit()
        logger.info("Token refreshed successfully for user %s", token.user_id)
    return token

def _html_error(title: str, body: str, status: int = 400) -> HTMLResponse:
    """Return a minimal but readable HTML error page."""
    return HTMLResponse(
        content=(
            f"<html><body style='font-family:system-ui;max-width:600px;margin:40px auto;'>"
            f"<h2>⚠️ {title}</h2><p>{body}</p>"
            f"<a href='/auth/login'>↩ Retry Zoho Login</a>"
            f"</body></html>"
        ),
        status_code=status,
    )

@app.get("/auth/login", summary="Start Zoho OAuth flow", response_model=None)
async def login() -> RedirectResponse:
    """Redirect the browser to the Zoho OAuth consent screen."""
    oauth = ZohoOAuth()
    url = oauth.get_authorization_url()
    logger.info("Redirecting to Zoho OAuth: %s", url[:80])
    return RedirectResponse(url)

@app.get("/auth/callback", summary="Handle Zoho OAuth callback", response_model=None)
async def callback(
    code: str | None = None,
    error: str | None = None,
    accounts_server: str | None = Query(default=None, alias="accounts-server"),
    db: DbSession = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """
    Exchange the Zoho authorisation code for tokens, persist the user
    record and session, then redirect the browser to the chat UI.
    """
    if error:
        return _html_error("Zoho Login Failed", f"Zoho returned: <code>{error}</code>")
    if not code:
        return _html_error("Missing Auth Code", "Zoho did not return an authorisation code.")

    existing_redirect = ZohoOAuth.get_redirect_for_code(code)
    if existing_redirect:
        logger.info("Replayed OAuth code — reusing saved redirect")
        return RedirectResponse(url=existing_redirect, status_code=302)

    oauth = ZohoOAuth()
    try:
        tokens = await oauth.exchange_code_for_tokens(code, accounts_url=accounts_server)
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        return _html_error("Token Exchange Failed", str(exc), status=500)

    access_token = tokens.get("access_token")
    if not access_token:
        err = tokens.get("error", "unknown_error")
        hint = (
            "Do not refresh this page — OAuth codes are single-use. Click Retry."
            if err == "invalid_code"
            else "Check ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, and ZOHO_REDIRECT_URI in .env."
        )
        return _html_error(
            "Token Exchange Failed",
            f"<pre>{json.dumps(tokens, indent=2)}</pre><p>{hint}</p>",
        )

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return _html_error(
            "Missing Refresh Token",
            "Zoho did not return a refresh token. "
            "Ensure <code>access_type=offline</code> and re-consent.",
        )

    try:
        portal_id = await oauth.get_portal_id(access_token)
    except ValueError as exc:
        return _html_error("Portal Lookup Failed", str(exc))

    try:
        await ensure_demo_projects(access_token, portal_id, target_count=5)
    except Exception as exc:
        logger.warning("Demo project bootstrap failed (non-fatal): %s", exc)

    user_info = await oauth.get_zoho_user_info(access_token, accounts_url=accounts_server) or {}
    zoho_user_id = str(user_info.get("ZUID") or user_info.get("zuid") or "")
    email = user_info.get("Email") or user_info.get("email") or ""
    name = user_info.get("Display_Name") or user_info.get("display_name") or ""

    if not zoho_user_id:
        zoho_user_id = email or f"zoho_{portal_id}"
    if not email:
        email = f"{zoho_user_id}@zoho.local"

    user = db.query(User).filter(User.zoho_user_id == zoho_user_id).first()
    if user:
        user.email = email or user.email
        user.name = name or user.name
        user.portal_id = portal_id
    else:
        user = User(
            zoho_user_id=zoho_user_id,
            email=email,
            name=name,
            portal_id=portal_id,
        )
        db.add(user)
        db.flush()

    expires_at = datetime.utcnow() + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    token = db.query(Token).filter(Token.user_id == user.id).first()
    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
    else:
        token = Token(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        db.add(token)

    session_id = str(uuid.uuid4())
    session = UserSession(session_id=session_id, user_id=user.id)
    db.add(session)
    db.commit()

    frontend_base = settings.FRONTEND_BASE_URL.rstrip("/")
    redirect_url = f"{frontend_base}/chat?session_id={session_id}"
    ZohoOAuth.remember_successful_code(code, redirect_url)

    logger.info("Login successful for user %s, session %s", email, session_id[:8])
    return RedirectResponse(url=redirect_url, status_code=302)

@app.post("/chat", response_model=ChatResponse, summary="Send a message to the AI agent")
async def chat(request: ChatRequest, db: DbSession = Depends(get_db)) -> ChatResponse:
    """
    Main conversational endpoint.

    The frontend sends every message here with a ``session_id``.
    This endpoint:
      1. Validates the session and refreshes the token if needed.
      2. Loads short-term + long-term memory context.
      3. Invokes the LangGraph agent graph.
      4. Persists updated memory (last_project_id, etc.).
      5. Returns the agent reply and HIL confirmation state.
    """
    sess = _get_session(db, request.session_id)
    user = _get_user(db, sess.user_id)
    token = _get_token(db, user.id)
    token = await _ensure_fresh_token(db, token)

    memory = MemoryStore(db)
    short_term = memory.get_all_short(request.session_id)
    long_term = await memory.get_all_long(user.id)

    pending_raw = memory.get_short(request.session_id, "pending_action")
    pending_from_memory: dict = {}
    if pending_raw:
        try:
            pending_from_memory = (
                json.loads(pending_raw) if isinstance(pending_raw, str) else pending_raw
            )
        except (json.JSONDecodeError, TypeError):
            pending_from_memory = {}

    awaiting_confirmation = bool(pending_from_memory) and request.confirmed is not None
    confirmed = bool(request.confirmed) if request.confirmed is not None else False

    state: dict = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": user.id,
        "session_id": request.session_id,
        "access_token": token.access_token,
        "portal_id": user.portal_id,
        "route": "",
        "pending_action": pending_from_memory if awaiting_confirmation else {},
        "awaiting_confirmation": awaiting_confirmation,
        "confirmed": confirmed,
        "short_term_context": short_term,
        "long_term_context": long_term,
    }

    try:
        result = await agent_graph.ainvoke(
            state,
            config={"configurable": {"thread_id": request.session_id}},
        )
    except Exception as exc:
        err_str = str(exc)
        logger.error("Agent graph invocation failed: %s", exc, exc_info=True)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
            raise HTTPException(
                status_code=429,
                detail=(
                    "The AI service is temporarily unavailable due to rate limiting. "
                    "Please wait a moment and try again."
                ),
            ) from exc
        raise HTTPException(status_code=500, detail=err_str) from exc

    messages = result.get("messages") or []
    last_msg = messages[-1] if messages else None
    raw_reply = getattr(last_msg, "content", None)
    reply = (
        normalize_reply_text(raw_reply)
        if raw_reply is not None
        else json.dumps(result, default=str)
    )

    awaiting = bool(result.get("awaiting_confirmation"))
    pending_action = result.get("pending_action") or None

    if awaiting and pending_action:
        memory.set_short(request.session_id, "pending_action", json.dumps(pending_action))
    else:
        memory.set_short(request.session_id, "pending_action", "")

    if not awaiting and user.portal_id:
        await _refresh_project_memory(token.access_token, user, memory, request.session_id)

    return ChatResponse(
        reply=reply,
        awaiting_confirmation=awaiting,
        pending_action=pending_action,
    )

async def _refresh_project_memory(
    access_token: str,
    user: User,
    memory: MemoryStore,
    session_id: str,
) -> None:
    """
    After a successful chat turn, sync the first/preferred project into
    both short-term and long-term memory so the agent can reference it
    in follow-up queries without the user repeating themselves.
    """
    try:
        client = ZohoClient(access_token=access_token, portal_id=user.portal_id)
        projects = await client.list_projects()
        if not projects:
            return
        first = projects[0]
        pid = str(first.get("id") or first.get("id_string") or "")
        pname = str(first.get("name") or "")
        if pid:
            memory.update_short(
                session_id,
                {"last_project_id": pid, "last_project_name": pname},
            )
            await memory.update_long(
                user.id,
                {"preferred_project_id": pid, "preferred_project_name": pname},
            )
    except Exception as exc:
        logger.warning("Could not refresh project memory: %s", exc)

@app.get("/health", summary="Liveness probe")
async def health() -> dict:
    """Returns 200 OK when the server is running."""
    return {"status": "ok", "version": "1.0.0"}

@app.get("/projects", summary="List projects (debug)")
async def list_projects(
    session_id: str,
    db: DbSession = Depends(get_db),
) -> dict:
    """
    Return all Zoho Projects for the authenticated user.
    Useful for setup verification and debugging.
    """
    sess = _get_session(db, session_id)
    user = _get_user(db, sess.user_id)
    token = _get_token(db, user.id)
    token = await _ensure_fresh_token(db, token)

    if not user.portal_id:
        raise HTTPException(
            status_code=400,
            detail="No portal_id on user record. Please log in again.",
        )

    client = ZohoClient(access_token=token.access_token, portal_id=user.portal_id)
    projects = await client.list_projects()
    return {
        "portal_id": user.portal_id,
        "count": len(projects),
        "projects": projects,
    }