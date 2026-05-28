import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ZOHO_CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "")
    ZOHO_CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "")
    ZOHO_REDIRECT_URI: str = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/auth/callback")
    ZOHO_ACCOUNTS_URL: str = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.in")
    ZOHO_API_BASE: str = os.getenv("ZOHO_API_BASE", "https://projectsapi.zoho.in/api/v3")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./zoho_chatbot.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")


settings = Settings()
