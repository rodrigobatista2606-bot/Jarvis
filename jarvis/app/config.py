"""Einstellungen laden.

Als Home-Assistant-Add-on stehen die Einstellungen in /data/options.json
(das Formular im Add-on-Tab "Konfiguration"). Für lokale Tests kann der Pfad
über die Umgebungsvariable JARVIS_OPTIONS umgestellt werden.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

DATA_DIR = Path(os.environ.get("JARVIS_DATA", "/data"))
OPTIONS_FILE = Path(os.environ.get("JARVIS_OPTIONS", DATA_DIR / "options.json"))


def _parse_time(value: str) -> time:
    hours, minutes = value.strip().split(":")
    return time(int(hours), int(minutes))


@dataclass
class Config:
    # Claude
    anthropic_api_key: str = ""
    model: str = "claude-opus-5-5"

    # Gmail (IMAP mit App-Passwort)
    gmail_address: str = ""
    gmail_app_password: str = ""

    # Outlook (Microsoft Graph, Anmeldung per Gerätecode)
    outlook_enabled: bool = False
    outlook_client_id: str = ""

    # Twilio (WhatsApp + Anrufe)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""      # z. B. +4915112345678 (ohne "whatsapp:")
    twilio_call_from: str = ""          # Nummer, von der Jarvis anruft
    whatsapp_template_sid: str = ""     # Vorlage für Nachrichten außerhalb des 24-h-Fensters
    my_phone: str = ""                  # deine Handynummer, z. B. +4917612345678
    call_voice: str = "Polly.Vicki"

    # Verhalten
    test_mode: bool = True              # nur melden, nichts verschieben/löschen
    check_interval_minutes: int = 10
    evening_call_time: time = field(default_factory=lambda: time(19, 0))
    evening_call_enabled: bool = True
    quiet_start: time = field(default_factory=lambda: time(22, 0))
    quiet_end: time = field(default_factory=lambda: time(7, 0))
    timezone: str = "Europe/Berlin"
    days_back_on_first_start: int = 1
    never_delete: list[str] = field(default_factory=list)   # Adressen oder Domains
    always_urgent: list[str] = field(default_factory=list)  # Adressen oder Domains
    extra_instructions: str = ""        # eigene Regeln in Alltagssprache

    @classmethod
    def load(cls, path: Path = OPTIONS_FILE) -> "Config":
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        cfg = cls()
        for key, value in raw.items():
            if not hasattr(cfg, key) or value is None:
                continue
            if key in ("evening_call_time", "quiet_start", "quiet_end"):
                value = _parse_time(value)
            setattr(cfg, key, value)
        cfg.never_delete = [s.strip().lower() for s in cfg.never_delete if s.strip()]
        cfg.always_urgent = [s.strip().lower() for s in cfg.always_urgent if s.strip()]
        return cfg

    def problems(self) -> list[str]:
        """Fehlende Pflichtangaben, verständlich formuliert."""
        out = []
        if not self.anthropic_api_key:
            out.append("Claude-API-Schlüssel (anthropic_api_key) fehlt.")
        if not (self.gmail_address and self.gmail_app_password) and not self.outlook_enabled:
            out.append("Kein Postfach eingerichtet (Gmail oder Outlook).")
        if self.gmail_address and not self.gmail_app_password:
            out.append("Gmail-App-Passwort (gmail_app_password) fehlt.")
        if self.outlook_enabled and not self.outlook_client_id:
            out.append("Outlook ist aktiviert, aber outlook_client_id fehlt.")
        if not self.my_phone:
            out.append("Deine Handynummer (my_phone) fehlt.")
        return out
