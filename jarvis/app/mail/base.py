"""Gemeinsame Bausteine für alle Postfächer."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class Mail:
    account: str            # z. B. "gmail" oder "outlook"
    uid: str                # Kennung im Postfach (für Verschieben/Löschen)
    message_id: str         # stabile Kennung, auch nach dem Verschieben
    sender: str
    subject: str
    received: datetime
    body: str
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.account}:{self.message_id or self.uid}"

    @property
    def sender_address(self) -> str:
        match = re.search(r"<([^>]+)>", self.sender)
        return (match.group(1) if match else self.sender).strip().lower()


class Mailbox(Protocol):
    name: str

    def fetch_since(self, since: datetime) -> list[Mail]: ...
    def trash(self, mail: Mail) -> None: ...
    def move_to_folder(self, mail: Mail, folder: str) -> None: ...
    def close(self) -> None: ...


_TAG = re.compile(r"<[^>]+>")
_STYLE = re.compile(r"<(style|script)[^>]*>.*?</\1>", re.S | re.I)
_SPACE = re.compile(r"[ \t\r\f\v]+")
_LINES = re.compile(r"\n\s*\n+")


def html_to_text(raw: str) -> str:
    text = _STYLE.sub(" ", raw)
    text = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", text, flags=re.I)
    text = html.unescape(_TAG.sub(" ", text)).replace("\xa0", " ")
    text = _SPACE.sub(" ", text)
    return _LINES.sub("\n\n", text).strip()
