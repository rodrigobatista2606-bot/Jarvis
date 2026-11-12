from datetime import datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.classifier import Classifier, Verdict, _matches, mail_prompt
from app.config import Config
from app.jarvis import Jarvis, in_quiet_hours
from app.mail.base import Mail, html_to_text
from app.state import State

TZ = ZoneInfo("Europe/Berlin")


class Clock:
    def __init__(self, dt):
        self.dt = dt

    def __call__(self):
        return self.dt


class FakeBox:
    name = "gmail"

    def __init__(self, mails):
        self.mails = mails
        self.trashed, self.moved = [], []

    def fetch_since(self, since):
        return [m for m in self.mails if m.received >= since]

    def trash(self, mail):
        self.trashed.append(mail.uid)

    def move_to_folder(self, mail, folder):
        self.moved.append((mail.uid, folder))

    def close(self):
        pass


class FakeClassifier:
    def __init__(self, verdicts):
        self.verdicts = verdicts

    def classify(self, mail):
        return self.verdicts[mail.uid]


class FakeNotifier:
    def __init__(self):
        self.messages, self.calls = [], []

    def whatsapp(self, text):
        self.messages.append(text)

    def call(self, text):
        self.calls.append(text)


class FakeDigest:
    def evening(self, entries, test_mode):
        return f"spoken {len(entries)}", f"written {len(entries)}"


def mail(uid, received, sender="Shop <info@shop.de>", subject="Hallo"):
    return Mail("gmail", uid, f"<{uid}@x>", sender, subject, received, "Text")


def make(tmp_path, now, mails, verdicts, **cfg):
    config = Config(**({"anthropic_api_key": "x", "my_phone": "+49"} | cfg))
    box = FakeBox(mails)
    notifier = FakeNotifier()
    clock = Clock(now)
    j = Jarvis(config, [box], FakeClassifier(verdicts), notifier,
               State(tmp_path / "s.db"), FakeDigest(), clock=clock)
    return j, box, notifier, clock


def v(cat, summary="Zusammenfassung"):
    return Verdict(cat, cat == "dringend", summary, "")


NOON = datetime(2026, 11, 12, 12, 0, tzinfo=TZ)


def test_test_mode_touches_nothing(tmp_path):
    mails = [mail("1", NOON), mail("2", NOON)]
    j, box, n, _ = make(tmp_path, NOON, mails, {"1": v("spam"), "2": v("newsletter")})
    j.run_once()
    assert box.trashed == [] and box.moved == []
    actions = [e["action"] for e in j.state.day_entries(NOON.date())]
    assert all(a.startswith("Testmodus") for a in actions)


def test_live_mode_sorts(tmp_path):
    mails = [mail("1", NOON), mail("2", NOON), mail("3", NOON), mail("4", NOON)]
    verdicts = {"1": v("spam"), "2": v("werbung"), "3": v("newsletter"), "4": v("normal")}
    j, box, n, _ = make(tmp_path, NOON, mails, verdicts, test_mode=False)
    j.run_once()
    assert box.trashed == ["1", "2"]
    assert box.moved == [("3", "Newsletter")]
    assert n.messages == [] and n.calls == []


def test_each_mail_processed_once(tmp_path):
    j, box, n, _ = make(tmp_path, NOON, [mail("1", NOON)], {"1": v("wichtig")})
    j.run_once()
    j.run_once()
    assert len(n.messages) == 1
    assert "1 wichtige Mail" in n.messages[0]


def test_urgent_calls_and_writes(tmp_path):
    m = mail("1", NOON, sender="Finanzamt <post@finanzamt.de>", subject="Bescheid")
    j, box, n, _ = make(tmp_path, NOON, [m], {"1": v("dringend", "Frist 30.11.")})
    j.run_once()
    assert len(n.calls) == 1 and "Finanzamt" in n.calls[0] and "Frist 30.11." in n.calls[0]
    assert "Dringende Mail" in n.messages[0]


def test_urgent_in_quiet_hours_is_called_in_the_morning(tmp_path):
    night = datetime(2026, 11, 12, 23, 30, tzinfo=TZ)
    j, box, n, clock = make(tmp_path, night, [mail("1", night)], {"1": v("dringend")})
    j.run_once()
    assert n.calls == [] and len(n.messages) == 1  # WhatsApp sofort, Anruf später
    clock.dt = datetime(2026, 11, 13, 7, 5, tzinfo=TZ)
    j.run_once()
    assert len(n.calls) == 1


def test_evening_update_once_per_day(tmp_path):
    j, box, n, clock = make(tmp_path, NOON, [mail("1", NOON)], {"1": v("normal")})
    j.run_once()
    assert n.calls == []
    clock.dt = NOON.replace(hour=19, minute=3)
    j.run_once()
    j.run_once()
    assert n.calls == ["spoken 1"] and n.messages == ["written 1"]


def test_evening_update_can_be_disabled(tmp_path):
    evening = NOON.replace(hour=20)
    j, box, n, _ = make(tmp_path, evening, [], {}, evening_call_enabled=False)
    j.run_once()
    assert n.calls == []


def test_old_mails_are_ignored_on_first_start(tmp_path):
    old = NOON - timedelta(days=5)
    j, box, n, _ = make(tmp_path, NOON, [mail("1", old), mail("2", NOON)],
                        {"1": v("wichtig"), "2": v("normal")})
    j.run_once()
    keys = [e["key"] for e in j.state.day_entries(NOON.date())]
    assert keys == ["gmail:<2@x>"]


def test_fetch_error_does_not_crash(tmp_path):
    j, box, n, _ = make(tmp_path, NOON, [], {})
    box.fetch_since = lambda since: (_ for _ in ()).throw(OSError("offline"))
    j.run_once()


@pytest.mark.parametrize("now,expected", [
    (time(23, 0), True), (time(3, 0), True), (time(6, 59), True),
    (time(7, 0), False), (time(12, 0), False), (time(21, 59), False),
])
def test_quiet_hours_over_midnight(now, expected):
    assert in_quiet_hours(now, time(22, 0), time(7, 0)) is expected


def test_sender_matching():
    assert _matches("max@firma.de", ["firma.de"])
    assert _matches("max@mail.firma.de", ["@firma.de"])
    assert _matches("max@firma.de", ["max@firma.de"])
    assert not _matches("max@nichtfirma.de", ["firma.de"])
    assert not _matches("anna@firma.de", ["max@firma.de"])


def test_never_delete_and_always_urgent_override_claude():
    c = Classifier.__new__(Classifier)
    c.never_delete, c.always_urgent = ["verein.de"], ["finanzamt.de"]
    c._ask_claude = lambda m: Verdict("newsletter", False, "", "")
    assert c.classify(mail("1", NOON, sender="V <a@verein.de>")).category == "normal"
    assert c.classify(mail("1", NOON, sender="FA <a@finanzamt.de>")).category == "dringend"
    assert c.classify(mail("1", NOON, sender="X <a@x.de>")).category == "newsletter"


def _response(text, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)])


def test_claude_answer_is_parsed_and_refusal_keeps_mail():
    c = Classifier("key", "claude-opus-5-5", [], [])
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return _response('{"category":"spam","official_sender":false,"summary":"s","reason":"r"}')

    c.client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    assert c.classify(mail("1", NOON)).category == "spam"
    assert calls[0]["output_config"]["format"]["type"] == "json_schema"

    c.client.beta.messages.create = lambda **k: _response("", stop="refusal")
    assert c.classify(mail("1", NOON)).category == "normal"


def test_prompt_marks_newsletter_hints_and_truncation():
    m = mail("1", NOON)
    m.headers = {"list-unsubscribe": "<mailto:x>"}
    m.body = "a" * 10000
    p = mail_prompt(m)
    assert "List-Unsubscribe" in p and "gekürzt" in p


def test_html_to_text():
    assert html_to_text("<style>x{}</style><p>Hallo&nbsp;<b>Welt</b></p>") == "Hallo Welt"


def test_imap_reads_mail_without_marking_it_read():
    from app.mail.imap import ImapMailbox
    raw = (b"From: =?utf-8?q?M=C3=BCller?= <m@x.de>\r\nSubject: Rechnung\r\n"
           b"Date: Thu, 12 Nov 2026 10:00:00 +0100\r\nMessage-ID: <abc@x>\r\n"
           b"List-Unsubscribe: <mailto:u@x.de>\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
           b"<p>Betrag: 12 &euro;</p>")
    commands = []

    class Conn:
        def noop(self): return "OK", []
        def select(self, box): return "OK", []
        def uid(self, cmd, *args):
            commands.append((cmd, args))
            if cmd == "SEARCH":
                return "OK", [b"7"]
            return "OK", [(b"7 (BODY[] {123}", raw), b")"]
        def list(self):
            return "OK", [b'(\\HasNoChildren \\Trash) "/" "[Gmail]/Papierkorb"']

    box = ImapMailbox("gmail", "imap.gmail.com", "u", "p")
    box._conn = Conn()
    [m] = box.fetch_since(NOON - timedelta(days=1))
    assert m.sender == "Müller <m@x.de>" and m.body == "Betrag: 12 €"
    assert m.headers["list-unsubscribe"] and m.key == "gmail:<abc@x>"
    assert ("FETCH", (b"7", "(BODY.PEEK[])")) in commands
    box.trash(m)
    assert commands[-1] == ("MOVE", ("7", '"[Gmail]/Papierkorb"'))
