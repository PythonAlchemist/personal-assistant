"""Shared Google OAuth2 authentication for all Google services."""

from __future__ import annotations

from assistant import config

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_credentials(account: str = "personal"):
    """Load or refresh Google OAuth2 credentials, running auth flow if needed."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    token_path = config.google_token_path(account)
    creds_path = config.GOOGLE_CREDENTIALS_PATH

    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google credentials not found at {creds_path}.\n"
            "Download your OAuth2 credentials from Google Cloud Console:\n"
            "  1. Go to https://console.cloud.google.com/apis/credentials\n"
            "  2. Create an OAuth 2.0 Client ID (Desktop app)\n"
            "  3. Download the JSON and save it to: data/google_credentials.json"
        )

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            email = config.GOOGLE_ACCOUNTS.get(account, "")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0, login_hint=email if email else None)
        token_path.write_text(creds.to_json())

    return creds


def get_service(api: str, version: str, account: str = "personal"):
    """Build a Google API service client."""
    from googleapiclient.discovery import build

    creds = get_credentials(account)
    return build(api, version, credentials=creds)
