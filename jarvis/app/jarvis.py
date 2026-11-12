"""Der Kern: Mails holen, einordnen, aufräumen, Bescheid geben."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from .classifier import Classifier, Verdict
from .config import Config
from .digest import Digest
from .mail.base import Mail, Mailbox
from .notifier import Notifier
from .state import State

log = logging.getLogger(__name__)

NEWSLETTER_FOLDER = "Newsletter"
ACCOUNT_NAMES = {"gmail": "Gmail", "outlook": "Outlook"}


def in_quiet_hours(now: time, start: time, end: time) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end  # über Mitternacht, z. B. 22:00–07:00


class Jarvis:
    def __init__(self, cfg: Config, mailboxes: list[Mailbox], classifier: Classifier,
                 notifier: Notifier, state: State, digest: Digest,
                 clock: Callable[[], datetime] | None = None):
        self.cfg = cfg
        self.mailboxes = mailboxes
        self.classifier = classifier
        self.notifier = notifier
        self.state = state
        self.digest = digest
        self.tz = ZoneInfo(cfg.timezone)
        self.clock = clock or (lambda: datetime.now(self.tz))
        if self.state.first_start() is None:
            self.state.set("first_start", self.clock().isoformat())

    # -- Hilfen ---------------------------------------------------------------
    def now(self) -> datetime:
        return self.clock().astimezone(self.tz)

    def quiet(self) -> bool:
        return in_quiet_hours(self.now().time(), self.cfg.quiet_start, self.cfg.quiet_end)

    def _cutoff(self) -> datetime:
        first = self.state.first_start()
        cutoff = first - timedelta(days=self.cfg.days_back_on_first_start)
        # nie mehr als 3 Tage zurück abfragen – ältere Mails sind längst bearbeitet
        return max(cutoff, self.now() - timedelta(days=3))

    # -- Ein Durchlauf ----------------------------------------------------------
    def run_once(self) -> None:
        if not self.quiet():
            for text in self.state.take_pending_calls():
                self.notifier.call(text)

        important: list[tuple[Mail, Verdict]] = []
        for box in self.mailboxes:
            try:
                mails = box.fetch_since(self._cutoff())
            except Exception as e:
                log.error("%s: Mails konnten nicht abgerufen werden: %s", box.name, e)
                box.close()
                continue
            for mail in sorted(mails, key=lambda m: m.received):
                if self.state.is_processed(mail.key):
                    continue
                verdict = self.classifier.classify(mail)
                action = self._apply(box, mail, verdict)
                self.state.record(mail.key, self.now().date(), mail.account, mail.sender,
                                  mail.subject, verdict.category, verdict.summary, action)
                log.info("[%s] %s | %s → %s (%s)", mail.account, mail.sender, mail.subject,
                         verdict.category, action)
                if verdict.urgent:
                    self._alarm(mail, verdict)
                elif verdict.category == "wichtig":
                    important.append((mail, verdict))

        if important:
            self.notifier.whatsapp(self._important_text(important))

        self._maybe_evening_update()

    def _apply(self, box: Mailbox, mail: Mail, verdict: Verdict) -> str:
        if verdict.category in ("spam", "werbung"):
            planned, act = "Papierkorb", lambda: box.trash(mail)
        elif verdict.category == "newsletter":
            planned, act = f"Ordner {NEWSLETTER_FOLDER}", lambda: box.move_to_folder(mail, NEWSLETTER_FOLDER)
        else:
            return "bleibt im Posteingang"
        if self.cfg.test_mode:
            return f"Testmodus: würde → {planned}"
        try:
            act()
            return f"→ {planned}"
        except Exception as e:
            log.error("Konnte Mail '%s' nicht verschieben: %s", mail.subject, e)
            return f"Fehler beim Verschieben ({planned})"

    # -- Benachrichtigungen ------------------------------------------------------
    @staticmethod
    def _who(mail: Mail) -> str:
        name = mail.sender.split("<")[0].strip().strip('"')
        return name or mail.sender_address

    def _alarm(self, mail: Mail, verdict: Verdict) -> None:
        account = ACCOUNT_NAMES.get(mail.account, mail.account)
        self.notifier.whatsapp(
            f"🚨 *Dringende Mail* ({account})\n"
            f"Von: {self._who(mail)}\nBetreff: {mail.subject}\n\n{verdict.summary}")
        spoken = (f"Hallo, hier ist Jarvis. Du hast eine dringende Mail von {self._who(mail)}. "
                  f"Betreff: {mail.subject}. {verdict.summary}")
        if self.quiet():
            self.state.queue_call(spoken)
            log.info("Ruhezeit – Anruf wird nach %s nachgeholt", self.cfg.quiet_end.strftime("%H:%M"))
        else:
            self.notifier.call(spoken)

    def _important_text(self, items: list[tuple[Mail, Verdict]]) -> str:
        lines = [f"📬 *{len(items)} wichtige Mail{'s' if len(items) > 1 else ''}*"]
        for mail, verdict in items:
            lines.append(f"\n• *{self._who(mail)}*: {mail.subject}\n  {verdict.summary}")
        return "\n".join(lines)

    def _maybe_evening_update(self) -> None:
        if not self.cfg.evening_call_enabled:
            return
        now = self.now()
        today = now.date().isoformat()
        if now.time() < self.cfg.evening_call_time or self.state.get("evening_done") == today:
            return
        if self.quiet():
            return
        self.state.set("evening_done", today)
        entries = self.state.day_entries(now.date())
        spoken, written = self.digest.evening(entries, test_mode=self.cfg.test_mode)
        self.notifier.whatsapp(written)
        self.notifier.call(spoken)
