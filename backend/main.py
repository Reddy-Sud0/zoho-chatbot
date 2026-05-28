from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import uuid

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session as DbSession

from langchain_core.messages import HumanMessage

from config import settings
from auth.zoho_oauth import ZohoOAuth
from database.db import get_db, init_db
from database.models import User, Token, Session as UserSession
from graph.agent_graph import agent_graph
from memory.memory_store import MemoryStore
from zoho.bootstrap import ensure_demo_projects
from zoho.zoho_client import ZohoClient
from schemas.chat_schema import ChatRequest, ChatResponse
from utils.message_format import normalize_reply_text


app = FastAPI(title="Zoho AI Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    init_db()


def _get_session(db: DbSession, session_id: str) -> UserSession:
    sess = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    return sess


def _get_user(db: DbSession, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def _get_token(db: DbSession, user_id: str) -> Token:
    token = db.query(Token).filter(Token.user_id == user_id).first()
    if not token:
        raise HTTPException(status_code=401, detail="Token not found")
    return token


async def _ensure_fresh_token(db: DbSession, token: Token) -> Token:
    if token.expires_at < datetime.utcnow() + timedelta(minutes=5):
        oauth = ZohoOAuth()
        refreshed = await oauth.refresh_access_token(token.refresh_token)
        token.access_token = refreshed["access_token"]
        token.expires_at = datetime.utcnow() + timedelta(seconds=int(refreshed.get("expires_in", 3600)))
        db.commit()
    return token


@app.get("/auth/login")
async def login():
    oauth = ZohoOAuth()
    return RedirectResponse(oauth.get_authorization_url())


@app.get("/auth/callback")
async def callback(
    code: str | None = None,
    error: str | None = None,
    accounts_server: str | None = Query(default=None, alias="accounts-server"),
    db=Depends(get_db),
):
    if error:
        return HTMLResponse(
            content=(
                "<h3>Zoho login failed</h3>"
                f"<p>Error: {error}</p>"
                "<p>Please go back and try login again.</p>"
                "<a href='/auth/login'>Retry Zoho Login</a>"
            ),
            status_code=400,
        )
    if not code:
        return HTMLResponse(
            content=(
                "<h3>Missing OAuth code</h3>"
                "<p>Zoho did not return an authorization code.</p>"
                "<a href='/auth/login'>Retry Zoho Login</a>"
            ),
            status_code=400,
        )

    existing_redirect = ZohoOAuth.get_redirect_for_code(code)
    if existing_redirect:
        return RedirectResponse(url=existing_redirect, status_code=302)

    oauth = ZohoOAuth()
    try:
        tokens = await oauth.exchange_code_for_tokens(code, accounts_url=accounts_server)
        access_token = tokens.get("access_token")
        if not access_token:
            err = tokens.get("error", "unknown_error")
            hint = (
                "Do not refresh this page. Click Retry and complete login once."
                if err == "invalid_code"
                else "Check Zoho Client ID/Secret and redirect URI in .env and API Console."
            )
            return HTMLResponse(
                content=(
                    "<h3>Zoho token exchange failed</h3>"
                    f"<pre>{json.dumps(tokens, indent=2)}</pre>"
                    f"<p><b>redirect_uri used:</b> {settings.ZOHO_REDIRECT_URI}</p>"
                    f"<p>{hint}</p>"
                    "<a href='/auth/login'>Retry Zoho Login</a>"
                ),
                status_code=400,
            )
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            return HTMLResponse(
                content=(
                    "<h3>Missing refresh token</h3>"
                    "<p>Zoho did not return a refresh token. Please re-consent and ensure access_type=offline.</p>"
                    "<a href='/auth/login'>Retry Zoho Login</a>"
                ),
                status_code=400,
            )

        portal_id = await oauth.get_portal_id(access_token)
        bootstrap = await ensure_demo_projects(access_token, portal_id, target_count=5)

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
            user = User(zoho_user_id=zoho_user_id, email=email, name=name, portal_id=portal_id)
            db.add(user)
            db.commit()
            db.refresh(user)

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

        frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
        redirect_url = f"{frontend_base}/chat?session_id={session_id}"
        ZohoOAuth.remember_successful_code(code, redirect_url)
        return RedirectResponse(url=redirect_url, status_code=302)
    except HTTPException:
        raise
    except ValueError as exc:
        return HTMLResponse(
            content=(
                "<h3>Zoho login setup issue</h3>"
                f"<p>{str(exc)}</p>"
                "<p>Token exchange may have worked, but Projects portal lookup failed.</p>"
                "<a href='/auth/login'>Retry Zoho Login</a>"
            ),
            status_code=400,
        )
    except Exception as exc:
        return HTMLResponse(
            content=(
                "<h3>Zoho callback error</h3>"
                f"<p>{str(exc)}</p>"
                "<p>Please retry login once. If it repeats, share this message.</p>"
                "<a href='/auth/login'>Retry Zoho Login</a>"
            ),
            status_code=500,
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db=Depends(get_db)):
    sess = _get_session(db, request.session_id)
    user = _get_user(db, sess.user_id)
    token = _get_token(db, user.id)
    token = await _ensure_fresh_token(db, token)

    memory_store = MemoryStore(db)
    short_term = memory_store.get_all_short(request.session_id)
    long_term = await memory_store.get_all_long(user.id)

    pending_raw = memory_store.get_short(request.session_id, "pending_action")
    pending_from_memory = {}
    if pending_raw:
        try:
            pending_from_memory = json.loads(pending_raw) if isinstance(pending_raw, str) else pending_raw
        except Exception:
            pending_from_memory = {}

    awaiting_confirmation = bool(pending_from_memory) and request.confirmed is not None
    confirmed = bool(request.confirmed) if request.confirmed is not None else False

    state = {
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
        result = await agent_graph.ainvoke(state, config={"configurable": {"thread_id": request.session_id}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    messages = result.get("messages") or []
    last = messages[-1] if messages else None
    raw_reply = getattr(last, "content", None) if last is not None else None
    reply = normalize_reply_text(raw_reply) if raw_reply is not None else json.dumps(result, default=str)

    awaiting = bool(result.get("awaiting_confirmation"))
    pending_action = result.get("pending_action") or None

    if awaiting and pending_action:
        memory_store.set_short(request.session_id, "pending_action", json.dumps(pending_action))
    else:
        memory_store.set_short(request.session_id, "pending_action", "")

    # Keep memory in sync for "first project" / preferred project flows
    if not awaiting and user.portal_id:
        try:
            client = ZohoClient(access_token=token.access_token, portal_id=user.portal_id)
            projects = await client.list_projects()
            if projects:
                first = projects[0]
                pid = str(first.get("id") or first.get("id_string") or "")
                pname = str(first.get("name") or "")
                if pid:
                    memory_store.set_short(request.session_id, "last_project_id", pid)
                    memory_store.set_short(request.session_id, "last_project_name", pname)
                    await memory_store.set_long(user.id, "preferred_project_id", pid)
                    await memory_store.set_long(user.id, "preferred_project_name", pname)
        except Exception:
            pass

    return ChatResponse(reply=reply, awaiting_confirmation=awaiting, pending_action=pending_action)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/projects")
async def list_projects(session_id: str, db=Depends(get_db)):
    """List all projects for the logged-in user's portal (debug/setup)."""
    sess = _get_session(db, session_id)
    user = _get_user(db, sess.user_id)
    token = _get_token(db, user.id)
    token = await _ensure_fresh_token(db, token)
    if not user.portal_id:
        raise HTTPException(status_code=400, detail="No portal_id on user. Please login again.")
    client = ZohoClient(access_token=token.access_token, portal_id=user.portal_id)
    projects = await client.list_projects()
    return {"portal_id": user.portal_id, "count": len(projects), "projects": projects}
