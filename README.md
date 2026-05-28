# Zoho AI Project Chatbot

## Architecture Overview

Three-layer system:

- UI (Next.js) → chat interface + confirmation dialog (HIL)
- FastAPI backend → OAuth, session validation, token refresh, chat endpoint
- LangGraph agents → router (READ/WRITE), query agent (read-only tools), action agent (write-only tools with HIL) → Zoho Projects REST API

SQLite (SQLAlchemy) stores:

- Users, tokens, sessions
- Long-term memory key/value pairs per user

Short-term memory is in-memory per session.

## Setup Steps

1. Clone the repo
2. Create Zoho OAuth app at `api-console.zoho.com`
3. Copy `backend/.env.example` → `backend/.env` and fill values
4. Backend install:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

5. Frontend install:

```bash
cd frontend
npm install
npm run dev
```

6. Open:
   - `http://localhost:3000` (frontend)
   - `http://localhost:8000/health` (backend)

## OAuth Configuration Guide

- Go to `api-console.zoho.com`
- Create **Server-based Application**
- Set redirect URI to `http://localhost:8000/auth/callback`
- Copy Client ID and Secret into `backend/.env`

## Environment Variables

See `backend/.env.example`.

- `ZOHO_CLIENT_ID`: Zoho OAuth client id
- `ZOHO_CLIENT_SECRET`: Zoho OAuth client secret
- `ZOHO_REDIRECT_URI`: callback URL (default `http://localhost:8000/auth/callback`)
- `ZOHO_ACCOUNTS_URL`: accounts host (default India: `https://accounts.zoho.in`)
- `ZOHO_API_BASE`: Zoho Projects base (default India: `https://projectsapi.zoho.in/restapi`)
- `ANTHROPIC_API_KEY`: Claude key for router + agents
- `DATABASE_URL`: SQLite connection string
- `SECRET_KEY`: reserved for future secure cookies/JWT (keep 32+ chars)

## Known Limitations

- Config defaults target **Zoho India region** (`zoho.in`)
- SQLite is used for simplicity — use PostgreSQL for production
- Long-term memory stores only the latest saved values per key
