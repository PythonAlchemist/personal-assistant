"""Gmail integration."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from assistant.services.google_auth import get_service


def _get_service(account: str = "personal"):
    return get_service("gmail", "v1", account)


def get_profile(account: str = "personal") -> dict:
    """Get the authenticated user's email profile."""
    service = _get_service(account)
    profile = service.users().getProfile(userId="me").execute()
    return {
        "email": profile["emailAddress"],
        "messages_total": profile.get("messagesTotal", 0),
        "threads_total": profile.get("threadsTotal", 0),
    }


def list_messages(
    account: str = "personal",
    query: str = "",
    max_results: int = 20,
    label_ids: list[str] | None = None,
) -> list[dict]:
    """List messages matching a query. Returns message summaries."""
    service = _get_service(account)
    kwargs = {"userId": "me", "maxResults": max_results}
    if query:
        kwargs["q"] = query
    if label_ids:
        kwargs["labelIds"] = label_ids

    result = service.users().messages().list(**kwargs).execute()
    messages = result.get("messages", [])

    # Fetch headers for each message
    summaries = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        summaries.append(_parse_message_metadata(detail))

    return summaries


def read_message(message_id: str, account: str = "personal") -> dict:
    """Read a full message by ID."""
    service = _get_service(account)
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    return _parse_full_message(msg)


def search(query: str, account: str = "personal", max_results: int = 20) -> list[dict]:
    """Search messages using Gmail query syntax."""
    return list_messages(account=account, query=query, max_results=max_results)


def list_labels(account: str = "personal") -> list[dict]:
    """List all labels."""
    service = _get_service(account)
    result = service.users().labels().list(userId="me").execute()
    return [
        {"id": l["id"], "name": l["name"], "type": l.get("type", "")}
        for l in result.get("labels", [])
    ]


def send_message(
    to: str,
    subject: str,
    body: str,
    account: str = "personal",
    cc: str = "",
    bcc: str = "",
    html: bool = False,
) -> dict:
    """Send an email."""
    service = _get_service(account)

    if html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body, "html"))
    else:
        message = MIMEText(body)

    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": result["id"], "thread_id": result.get("threadId", "")}


def reply_to_message(
    message_id: str,
    body: str,
    account: str = "personal",
    html: bool = False,
) -> dict:
    """Reply to an existing message."""
    service = _get_service(account)

    # Get original message for headers
    original = service.users().messages().get(userId="me", id=message_id, format="metadata",
        metadataHeaders=["From", "To", "Subject", "Message-ID"]).execute()

    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
    thread_id = original.get("threadId", "")

    subject = headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    reply_to = headers.get("From", "")

    if html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body, "html"))
    else:
        message = MIMEText(body)

    message["to"] = reply_to
    message["subject"] = subject
    message["In-Reply-To"] = headers.get("Message-ID", "")
    message["References"] = headers.get("Message-ID", "")

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw, "threadId": thread_id}
    ).execute()
    return {"id": result["id"], "thread_id": result.get("threadId", "")}


def mark_read(message_id: str, account: str = "personal") -> None:
    """Mark a message as read."""
    service = _get_service(account)
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def mark_unread(message_id: str, account: str = "personal") -> None:
    """Mark a message as unread."""
    service = _get_service(account)
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": ["UNREAD"]}
    ).execute()


def get_unread_count(account: str = "personal") -> int:
    """Get count of unread messages in inbox."""
    service = _get_service(account)
    result = service.users().messages().list(
        userId="me", q="is:unread in:inbox", maxResults=1
    ).execute()
    return result.get("resultSizeEstimate", 0)


def _parse_message_metadata(msg: dict) -> dict:
    """Parse message metadata into a clean dict."""
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    labels = msg.get("labelIds", [])
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "unread": "UNREAD" in labels,
        "labels": labels,
    }


def _parse_full_message(msg: dict) -> dict:
    """Parse a full message including body text."""
    parsed = _parse_message_metadata(msg)
    parsed["body"] = _extract_body(msg.get("payload", {}))
    return parsed


def _extract_body(payload: dict) -> str:
    """Extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart — look for text/plain first, then text/html
    parts = payload.get("parts", [])
    for mime in ("text/plain", "text/html"):
        for part in parts:
            if part.get("mimeType") == mime and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            # Nested multipart
            if part.get("parts"):
                for subpart in part["parts"]:
                    if subpart.get("mimeType") == mime and subpart.get("body", {}).get("data"):
                        return base64.urlsafe_b64decode(subpart["body"]["data"]).decode("utf-8", errors="replace")

    return "(no body)"
