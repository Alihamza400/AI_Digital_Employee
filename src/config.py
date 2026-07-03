"""
Central configuration — loads from .env with pydantic-settings.
Secrets are individual env vars, reconstructed into credential objects in memory.
"""
from pathlib import Path
from typing import Any, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
    )

    vault_path: str = "AI_Employee_Vault"
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_project_id: str = ""
    gmail_refresh_token: str = ""
    calendar_client_id: str = ""
    calendar_client_secret: str = ""
    calendar_project_id: str = ""
    calendar_refresh_token: str = ""
    notify_email: str = ""
    approval_url: str = ""
    approval_port: int = 8080
    whatsapp_session: str = "AI_Employee_Vault/whatsapp_session"
    linkedin_session: str = "AI_Employee_Vault/linkedin_session"

    @property
    def vault(self) -> Path:
        return Path(self.vault_path)

    @property
    def gmail_client_config_dict(self) -> Dict[str, Any]:
        """Reconstruct Google OAuth client config from individual env vars."""
        if not self.gmail_client_id or not self.gmail_client_secret:
            return {}
        return {
            "installed": {
                "client_id": self.gmail_client_id,
                "client_secret": self.gmail_client_secret,
                "project_id": self.gmail_project_id or "",
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
                "auth_provider_x509_cert_url": GOOGLE_CERT_URL,
                "redirect_uris": ["http://localhost"],
            }
        }

    @property
    def gmail_token_dict(self) -> Dict[str, Any]:
        """Reconstruct OAuth token dict from individual env vars."""
        if not self.gmail_refresh_token or not self.gmail_client_id:
            return {}
        return {
            "token": "",
            "refresh_token": self.gmail_refresh_token,
            "token_uri": GOOGLE_TOKEN_URI,
            "client_id": self.gmail_client_id,
            "client_secret": self.gmail_client_secret,
            "scopes": GMAIL_SCOPES,
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": "",
        }

    @property
    def gmail_configured(self) -> bool:
        return bool(self.gmail_client_id and self.gmail_client_secret and self.gmail_refresh_token)

    @property
    def calendar_client_config_dict(self) -> Dict[str, Any]:
        """Reconstruct Google OAuth client config for Calendar from individual env vars."""
        if not self.calendar_client_id or not self.calendar_client_secret:
            return {}
        return {
            "installed": {
                "client_id": self.calendar_client_id,
                "client_secret": self.calendar_client_secret,
                "project_id": self.calendar_project_id or "",
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
                "auth_provider_x509_cert_url": GOOGLE_CERT_URL,
                "redirect_uris": ["http://localhost"],
            }
        }

    @property
    def calendar_token_dict(self) -> Dict[str, Any]:
        """Reconstruct OAuth token dict for Calendar (separate client)."""
        if not self.calendar_refresh_token or not self.calendar_client_id:
            return {}
        return {
            "token": "",
            "refresh_token": self.calendar_refresh_token,
            "token_uri": GOOGLE_TOKEN_URI,
            "client_id": self.calendar_client_id,
            "client_secret": self.calendar_client_secret,
            "scopes": CALENDAR_SCOPES,
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": "",
        }

    @property
    def calendar_configured(self) -> bool:
        return bool(self.calendar_client_id and self.calendar_client_secret and self.calendar_refresh_token)

    @property
    def whatsapp_session_path(self) -> Path:
        return Path(self.whatsapp_session)

    @property
    def linkedin_session_path(self) -> Path:
        return Path(self.linkedin_session)

    def to_dict(self) -> dict:
        return {
            'gmail_client_config': self.gmail_client_config_dict,
            'gmail_token_json': self.gmail_token_dict,
            'calendar_client_config': self.calendar_client_config_dict,
            'calendar_token_json': self.calendar_token_dict,
            'vault_path': self.vault_path,
            'notify_email': self.notify_email,
            'approval_url': self.approval_url,
            'approval_port': self.approval_port,
            'whatsapp_session': str(self.whatsapp_session_path),
            'linkedin_session': str(self.linkedin_session_path),
        }


settings = Settings()
