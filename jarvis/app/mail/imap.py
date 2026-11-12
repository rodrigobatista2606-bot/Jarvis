"""Postfach über IMAP (Gmail mit App-Passwort, funktioniert auch mit GMX, Web.de …)."""

from __future__ import annotations

import email
import imaplib
import logging
import re
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime

from .base import Mail, html_to_text

log = logging.getLogger(__name__)

_LIST_RE = re.compile(r'\((?P<flags>[^)]*)\) "(?P<sep>[^"]*)" (?P<name>.+)')


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _body_text(msg: Message) -> str:
    plain, rich = [], []
    for part in msg.walk() if msg.is_multipart() else [msg]:
        if part.get_content_maintype() == "multipart" or part.get_filename():
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_type() == "text/plain":
            plain.append(text)
        elif part.get_content_type() == "text/html":
            rich.append(html_to_text(text))
    return ("\n".join(plain) or "\n".join(rich)).strip()


class ImapMailbox:
    def __init__(self, name: str, host: str, user: str, password: str):
        self.name = name
        self.host, self.user, self.password = host, user, password
        self._conn: imaplib.IMAP4_SSL | None = None
        self._trash: str | None = None

    # -- Verbindung ---------------------------------------------------------
    def _connect(self) -> imaplib.IMAP4_SSL:
        if self._conn is not None:
            try:
                self._conn.noop()
                return self._conn
            except Exception:
                self._conn = None
        conn = imaplib.IMAP4_SSL(self.host)
        conn.login(self.user, self.password)
        conn.select("INBOX")
        self._conn = conn
        return conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    @staticmethod
    def _quote(folder: str) -> str:
        return '"' + folder.replace("\\", "\\\\").replace('"', '\\"') + '"'

    def _folders(self) -> list[tuple[str, str]]:
        typ, data = self._connect().list()
        result = []
        for line in data or []:
            match = _LIST_RE.match(line.decode(errors="replace"))
            if match:
                result.append((match["flags"], match["name"].strip('"')))
        return result

    def _trash_folder(self) -> str:
        if self._trash is None:
            for flags, name in self._folders():
                if "\\Trash" in flags:
                    self._trash = name
                    break
            else:
                self._trash = "[Gmail]/Trash" if "gmail" in self.host else "Trash"
        return self._trash

    # -- Lesen ----------------------------------------------------------------
    def fetch_since(self, since: datetime) -> list[Mail]:
        conn = self._connect()
        conn.select("INBOX")
        date = since.strftime("%d-%b-%Y")
        typ, data = conn.uid("SEARCH", None, f"SINCE {date}")
        uids = (data[0] or b"").split()
        mails = []
        for uid in uids:
            typ, parts = conn.uid("FETCH", uid, "(BODY.PEEK[])")  # PEEK = bleibt ungelesen
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
            if not raw:
                continue
            msg = email.message_from_bytes(raw)
            try:
                received = parsedate_to_datetime(msg.get("Date"))
                if received.tzinfo is None:
                    received = received.replace(tzinfo=timezone.utc)
            except Exception:
                received = datetime.now(timezone.utc)
            if received < since:
                continue
            mails.append(Mail(
                account=self.name,
                uid=uid.decode(),
                message_id=(msg.get("Message-ID") or "").strip(),
                sender=_decode(msg.get("From")),
                subject=_decode(msg.get("Subject")),
                received=received,
                body=_body_text(msg),
                headers={
                    "list-unsubscribe": msg.get("List-Unsubscribe", ""),
                    "precedence": msg.get("Precedence", ""),
                    "list-id": msg.get("List-Id", ""),
                },
            ))
        return mails

    # -- Aktionen ---------------------------------------------------------------
    def _move(self, mail: Mail, folder: str) -> None:
        conn = self._connect()
        conn.select("INBOX")
        typ, _ = conn.uid("MOVE", mail.uid, self._quote(folder))
        if typ != "OK":  # Server ohne MOVE: kopieren + als gelöscht markieren
            conn.uid("COPY", mail.uid, self._quote(folder))
            conn.uid("STORE", mail.uid, "+FLAGS", "(\\Deleted)")
            conn.expunge()

    def trash(self, mail: Mail) -> None:
        self._move(mail, self._trash_folder())

    def move_to_folder(self, mail: Mail, folder: str) -> None:
        if folder not in {name for _, name in self._folders()}:
            self._connect().create(self._quote(folder))
        self._move(mail, folder)


def gmail(address: str, app_password: str) -> ImapMailbox:
    return ImapMailbox("gmail", "imap.gmail.com", address, app_password.replace(" ", ""))
