"""Tests for configuration and credential management."""

from pathlib import Path
from src.config import Settings, GOOGLE_AUTH_URI, GOOGLE_TOKEN_URI, GMAIL_SCOPES, CALENDAR_SCOPES


def test_settings_default_values():
    s = Settings()
    assert s.vault_path == "AI_Employee_Vault"
    assert isinstance(s.vault, Path)
    assert s.approval_port == 8080
    assert not s.gmail_configured
    assert not s.calendar_configured


def test_settings_custom_values():
    s = Settings(
        vault_path="Custom_Vault",
        notify_email="boss@example.com",
        approval_port=9090,
        approval_url="https://custom.domain",
    )
    assert s.vault == Path("Custom_Vault")
    assert s.notify_email == "boss@example.com"
    assert s.approval_port == 9090
    assert s.approval_url == "https://custom.domain"


def test_gmail_client_config_reconstruction():
    s = Settings(
        gmail_client_id="client_123",
        gmail_client_secret="secret_abc",
        gmail_project_id="proj_xyz",
    )
    config = s.gmail_client_config_dict
    assert "installed" in config
    installed = config["installed"]
    assert installed["client_id"] == "client_123"
    assert installed["client_secret"] == "secret_abc"
    assert installed["project_id"] == "proj_xyz"
    assert installed["auth_uri"] == GOOGLE_AUTH_URI
    assert installed["token_uri"] == GOOGLE_TOKEN_URI


def test_gmail_token_dict_reconstruction():
    s = Settings(
        gmail_client_id="client_123",
        gmail_client_secret="secret_abc",
        gmail_refresh_token="refresh_999",
    )
    token = s.gmail_token_dict
    assert token["client_id"] == "client_123"
    assert token["client_secret"] == "secret_abc"
    assert token["refresh_token"] == "refresh_999"
    assert token["scopes"] == GMAIL_SCOPES
    assert s.gmail_configured is True


def test_calendar_reconstruction():
    s = Settings(
        calendar_client_id="cal_123",
        calendar_client_secret="cal_sec",
        calendar_refresh_token="cal_ref",
    )
    assert s.calendar_configured is True
    config = s.calendar_client_config_dict
    assert config["installed"]["client_id"] == "cal_123"
    token = s.calendar_token_dict
    assert token["refresh_token"] == "cal_ref"
    assert token["scopes"] == CALENDAR_SCOPES


def test_to_dict_export():
    s = Settings(notify_email="test@example.com")
    d = s.to_dict()
    assert isinstance(d, dict)
    assert d["notify_email"] == "test@example.com"
    assert "gmail_client_config" in d
    assert "calendar_token_json" in d


def test_opencode_reasoning_settings():
    """The reasoning engine must be configurable — the default model may be unfunded."""
    s = Settings()
    assert s.opencode_model == ""
    assert s.opencode_agent == "ai-employee"
    assert s.opencode_timeout == 300

    custom = Settings(
        opencode_model="google/gemini-3.6-flash",
        opencode_agent="ai-employee",
        opencode_timeout=120,
    )
    assert custom.opencode_model == "google/gemini-3.6-flash"
    assert custom.opencode_timeout == 120

    exported = custom.to_dict()
    assert exported["opencode_model"] == "google/gemini-3.6-flash"
    assert exported["opencode_agent"] == "ai-employee"
