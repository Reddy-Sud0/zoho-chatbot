"""
config.py
──────────
Application-wide settings loaded from environment variables / .env.

Uses a plain dataclass approach for zero extra dependencies beyond
python-dotenv (already in requirements.txt).  Each field is typed and
has a sensible default so the app boots in development without a
fully-configured .env.

Environment variable reference
───────────────────────────────
ZOHO_CLIENT_ID         Zoho OAuth app client ID
ZOHO_CLIENT_SECRET     Zoho OAuth app client secret
ZOHO_REDIRECT_URI      OAuth callback URL (must match Zoho console)
ZOHO_ACCOUNTS_URL      Zoho accounts server (region-dependent)
ZOHO_API_BASE          Zoho Projects API base URL (region-dependent)
GOOGLE_API_KEY         Gemini API key (used by LangChain automatically)
DATABASE_URL           SQLAlchemy connection string
SECRET_KEY             ≥32-char random secret for session signing
FRONTEND_BASE_URL      Where the Next.js UI is hosted
LOG_LEVEL              Python logging level (default: INFO)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:

    ZOHO_CLIENT_ID: str = field(
        default_factory=lambda: os.getenv("ZOHO_CLIENT_ID", "")
    )
    ZOHO_CLIENT_SECRET: str = field(
        default_factory=lambda: os.getenv("ZOHO_CLIENT_SECRET", "")
    )
    ZOHO_REDIRECT_URI: str = field(
        default_factory=lambda: os.getenv(
            "ZOHO_REDIRECT_URI", "http://localhost:8000/auth/callback"
        )
    )
    ZOHO_ACCOUNTS_URL: str = field(
        default_factory=lambda: os.getenv(
            "ZOHO_ACCOUNTS_URL", "https://accounts.zoho.in"
        )
    )
    ZOHO_API_BASE: str = field(
        default_factory=lambda: os.getenv(
            "ZOHO_API_BASE", "https://projectsapi.zoho.in/api/v3"
        )
    )

    GOOGLE_API_KEY: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )

    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///./zoho_chatbot.db"
        )
    )

    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", "")
    )

    FRONTEND_BASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "FRONTEND_BASE_URL", "http://localhost:3000"
        )
    )
    LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    def validate(self) -> None:
        """
        Raise ``ValueError`` for any required-but-missing configuration.
        Called at startup so misconfiguration is caught early.
        """
        missing = []
        if not self.ZOHO_CLIENT_ID:
            missing.append("ZOHO_CLIENT_ID")
        if not self.ZOHO_CLIENT_SECRET:
            missing.append("ZOHO_CLIENT_SECRET")
        if not self.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please check backend/.env (copy from .env.example)."
            )

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)