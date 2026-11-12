"""Outlook.com / Hotmail über Microsoft Graph.

Microsoft erlaubt bei Outlook.com keine Anmeldung mit Passwort mehr über IMAP.
Darum meldet sich Jarvis einmalig per Gerätecode an: Jarvis schickt dir einen
Code per WhatsApp, du gibst ihn auf microsoft.com/devicelogin ein, fertig.
Danach bleibt die Anmeldung gespeichert (Datei /data/outlook_token.json).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import msal
import requests

from .base import Mail, html_to_text

log = logging.getLogger(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.ReadWrite"]
AUTHORITY = "https://login.microsoftonline.com/consumers"


class OutlookMailbox:
    name = "outlook"

    def __init__(self, client_id: str, cache_file: Path,
                 on_login_code: Callable[[str], None] | None = None):
        self.cache_file = cache_file
        self.cache = msal.SerializableTokenCache()
        if cache_file.exists():
            self.cache.deserialize(cache_file.read_text())
        self.app = msal.PublicClientApplication(
            client_id, authority=AUTHORITY, token_cache=self.cache)
        self.on_login_code = on_login_code
        self._folder_ids: dict[str, str] = {}

    # -- Anmeldung --------------------------------------------------------------
    def _save_cache(self) -> None:
        if self.cache.has_state_changed:
            self.cache_file.write_text(self.cache.serialize())
            self.cache_file.chmod(0o600)

    def _token(self) -> str:
        accounts = self.app.get_accounts()
        result = self.app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
        if not result:
            flow = self.app.initiate_device_flow(scopes=SCOPES)
            if "user_code" not in flow:
                raise RuntimeError(f"Outlook-Anmeldung fehlgeschlagen: {flow.get('error_description')}")
            text = (f"Outlook-Anmeldung für Jarvis: Öffne {flow['verification_uri']} "
                    f"und gib diesen Code ein: {flow['user_code']}")
            log.warning(text)
            if self.on_login_code:
                self.on_login_code(text)
            result = self.app.acquire_token_by_device_flow(flow)  # wartet bis max. 15 Min.
        self._save_cache()
        if "access_token" not in result:
            raise RuntimeError(f"Outlook-Anmeldung fehlgeschlagen: {result.get('error_description')}")
        return result["access_token"]

    def _request(self, method: str, path: str, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {self._token()}",
                   "Prefer": 'outlook.body-content-type="text"'}
        url = path if path.startswith("http") else GRAPH + path
        resp = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # -- Lesen ------------------------------------------------------------------
    def fetch_since(self, since: datetime) -> list[Mail]:
        stamp = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = (f"/me/mailFolders/inbox/messages?$filter=receivedDateTime ge {stamp}"
               "&$select=id,subject,from,receivedDateTime,internetMessageId,"
               "internetMessageHeaders,body&$top=50&$orderby=receivedDateTime desc")
        mails = []
        while url:
            data = self._request("GET", url)
            for item in data.get("value", []):
                sender = item.get("from", {}).get("emailAddress", {})
                headers = {h["name"].lower(): h["value"]
                           for h in item.get("internetMessageHeaders") or []}
                body = item.get("body", {})
                text = body.get("content", "")
                if body.get("contentType") == "html":
                    text = html_to_text(text)
                mails.append(Mail(
                    account=self.name,
                    uid=item["id"],
                    message_id=item.get("internetMessageId", ""),
                    sender=f'{sender.get("name", "")} <{sender.get("address", "")}>',
                    subject=item.get("subject") or "",
                    received=datetime.fromisoformat(item["receivedDateTime"].replace("Z", "+00:00")),
                    body=text,
                    headers={k: headers.get(k, "") for k in ("list-unsubscribe", "precedence", "list-id")},
                ))
            url = data.get("@odata.nextLink")
        return mails

    # -- Aktionen ---------------------------------------------------------------
    def _move(self, mail: Mail, destination_id: str) -> None:
        self._request("POST", f"/me/messages/{mail.uid}/move", json={"destinationId": destination_id})

    def trash(self, mail: Mail) -> None:
        self._move(mail, "deleteditems")

    def move_to_folder(self, mail: Mail, folder: str) -> None:
        if folder not in self._folder_ids:
            safe = folder.replace("'", "''")
            found = self._request("GET", f"/me/mailFolders?$filter=displayName eq '{safe}'")
            if found.get("value"):
                self._folder_ids[folder] = found["value"][0]["id"]
            else:
                self._folder_ids[folder] = self._request(
                    "POST", "/me/mailFolders", json={"displayName": folder})["id"]
        self._move(mail, self._folder_ids[folder])

    def close(self) -> None:
        pass
