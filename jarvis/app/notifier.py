"""WhatsApp-Nachrichten und Anrufe über Twilio."""

from __future__ import annotations

import json
import logging
from xml.sax.saxutils import escape

from twilio.rest import Client

log = logging.getLogger(__name__)

WHATSAPP_LIMIT = 1500  # Twilio erlaubt 1600 Zeichen; Vorlagen-Variablen weniger


class Notifier:
    def __init__(self, account_sid: str, auth_token: str, whatsapp_from: str,
                 call_from: str, my_phone: str, template_sid: str = "",
                 voice: str = "Polly.Vicki"):
        self.client = Client(account_sid, auth_token) if account_sid and auth_token else None
        self.whatsapp_from = whatsapp_from
        self.call_from = call_from or whatsapp_from
        self.my_phone = my_phone
        self.template_sid = template_sid
        self.voice = voice

    def whatsapp(self, text: str) -> None:
        if not self.client or not self.whatsapp_from:
            log.info("[WhatsApp nicht eingerichtet] %s", text)
            return
        text = text if len(text) <= WHATSAPP_LIMIT else text[:WHATSAPP_LIMIT - 1] + "…"
        args = {"from_": f"whatsapp:{self.whatsapp_from}", "to": f"whatsapp:{self.my_phone}"}
        if self.template_sid:
            # Vorlage mit einer Variablen {{1}} – funktioniert auch, wenn du Jarvis
            # in den letzten 24 Stunden nicht geschrieben hast.
            args |= {"content_sid": self.template_sid,
                     "content_variables": json.dumps({"1": text[:1000]})}
        else:
            args["body"] = text
        try:
            self.client.messages.create(**args)
            log.info("WhatsApp gesendet (%d Zeichen)", len(text))
        except Exception as e:
            log.error("WhatsApp konnte nicht gesendet werden: %s", e)

    def call(self, text: str) -> None:
        if not self.client or not self.call_from:
            log.info("[Anruf nicht eingerichtet] %s", text)
            return
        say = f'<Say language="de-DE" voice="{escape(self.voice)}">{escape(text)}</Say>'
        twiml = (f"<Response><Pause length=\"1\"/>{say}<Pause length=\"2\"/>"
                 f'<Say language="de-DE" voice="{escape(self.voice)}">Ich wiederhole.</Say>'
                 f"{say}</Response>")
        try:
            self.client.calls.create(to=self.my_phone, from_=self.call_from, twiml=twiml)
            log.info("Anruf gestartet")
        except Exception as e:
            log.error("Anruf fehlgeschlagen: %s", e)
