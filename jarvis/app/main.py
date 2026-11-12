"""Startpunkt: Einstellungen laden, Postfächer verbinden, alle paar Minuten prüfen."""

from __future__ import annotations

import logging
import signal
import sys
import time

from .classifier import Classifier
from .config import DATA_DIR, Config
from .digest import Digest
from .jarvis import Jarvis
from .mail.imap import gmail
from .mail.outlook import OutlookMailbox
from .notifier import Notifier
from .state import State

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%d.%m. %H:%M:%S")
log = logging.getLogger("jarvis")


def main() -> int:
    cfg = Config.load()
    problems = cfg.problems()
    if problems:
        for p in problems:
            log.error("Einstellung fehlt: %s", p)
        log.error("Bitte im Add-on unter 'Konfiguration' ergänzen und neu starten.")
        return 1

    notifier = Notifier(cfg.twilio_account_sid, cfg.twilio_auth_token, cfg.twilio_whatsapp_from,
                        cfg.twilio_call_from, cfg.my_phone, cfg.whatsapp_template_sid, cfg.call_voice)
    mailboxes = []
    if cfg.gmail_address:
        mailboxes.append(gmail(cfg.gmail_address, cfg.gmail_app_password))
    if cfg.outlook_enabled:
        mailboxes.append(OutlookMailbox(cfg.outlook_client_id, DATA_DIR / "outlook_token.json",
                                        on_login_code=notifier.whatsapp))

    jarvis = Jarvis(
        cfg, mailboxes,
        Classifier(cfg.anthropic_api_key, cfg.model, cfg.never_delete, cfg.always_urgent,
                   cfg.extra_instructions),
        notifier, State(DATA_DIR / "jarvis.db"), Digest(cfg.anthropic_api_key, cfg.model))

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    names = ", ".join(b.name for b in mailboxes)
    log.info("Jarvis gestartet. Postfächer: %s. Testmodus: %s", names, "an" if cfg.test_mode else "aus")
    if jarvis.state.get("hello_sent") is None:
        notifier.whatsapp(
            f"👋 Hallo, hier ist Jarvis. Ich passe ab jetzt auf deine Mails auf ({names}).\n"
            + ("🧪 Testmodus ist an: Ich sortiere nur im Kopf und lösche noch nichts. "
               "Im Abend-Update siehst du, was ich getan hätte." if cfg.test_mode else ""))
        jarvis.state.set("hello_sent", "1")

    while running:
        try:
            jarvis.run_once()
        except Exception:
            log.exception("Unerwarteter Fehler im Durchlauf – nächster Versuch beim nächsten Intervall")
        for _ in range(cfg.check_interval_minutes * 60):
            if not running:
                break
            time.sleep(1)

    for box in mailboxes:
        box.close()
    log.info("Jarvis beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
