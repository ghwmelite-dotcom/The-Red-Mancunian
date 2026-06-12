import json

import pytest

import delivery


def test_build_callback_format():
    assert delivery.build_callback("ok", "1234", "2026-06-11-hall") == \
        "ok:1234:2026-06-11-hall"


def test_build_callback_rejects_over_64_bytes():
    with pytest.raises(ValueError):
        delivery.build_callback("ok", "16234567890", "x" * 60)


def test_summary_lines(tmp_path):
    s = {"hook": {"text": "UNITED WANT A NEW LEFT-BACK"},
         "category": "TRANSFER", "status": "REPORTED", "source": "Sky Sports"}
    text = delivery.summary(s)
    assert "UNITED WANT A NEW LEFT-BACK" in text
    assert "TRANSFER" in text and "REPORTED" in text and "Sky Sports" in text


def _stage_story(day, story_id, hook="HOOK GOES HERE NOW"):
    (day / f"{story_id}.mp4").write_bytes(b"vid")
    (day / f"{story_id}-caption.txt").write_text("caption text", encoding="utf-8")
    (day / f"{story_id}.json").write_text(json.dumps(
        {"hook": {"text": hook}, "category": "TRANSFER",
         "status": "REPORTED", "source": "Sky Sports"}), encoding="utf-8")


def test_deliver_sends_video_then_caption(tmp_path, monkeypatch):
    day = tmp_path
    _stage_story(day, "2026-06-11-hall", hook="HOOK")
    monkeypatch.setattr(delivery.dedupe, "LEDGER_PATH", day / "delivered.json")

    sent = []
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(delivery.telegram_bot, "call",
                        lambda method, files=None, **p:
                        (sent.append((method, p)), {"message_id": 9})[1])
    assert delivery.deliver(day, "2026-06-11-hall", "777", []) is True

    assert sent[0][0] == "sendVideo"
    assert "HOOK" in sent[0][1]["caption"]
    keyboard = json.loads(sent[0][1]["reply_markup"])
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == "ok:777:2026-06-11-hall"
    assert sent[1] == ("sendMessage",
                       {"chat_id": "42", "text": "caption text",
                        "reply_to_message_id": 9})


def test_deliver_skips_story_already_in_ledger(tmp_path, monkeypatch):
    day = tmp_path
    _stage_story(day, "2026-06-11-hall")
    monkeypatch.setattr(delivery.dedupe, "LEDGER_PATH", day / "delivered.json")
    ledger = [{"id": "2026-06-11-hall", "tokens": ["anything"],
               "sent_at": "2026-06-11T12:00:00+01:00"}]

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(delivery.telegram_bot, "call",
                        lambda *a, **p: pytest.fail("must not call Telegram"))
    assert delivery.deliver(day, "2026-06-11-hall", "777", ledger) is False
    assert len(ledger) == 1                      # nothing new recorded


def test_deliver_records_before_caption_message(tmp_path, monkeypatch):
    """If the caption sendMessage fails, the video must already be in the
    ledger so a retry does not re-send it."""
    day = tmp_path
    _stage_story(day, "2026-06-11-hall")
    monkeypatch.setattr(delivery.dedupe, "LEDGER_PATH", day / "delivered.json")
    ledger = []

    def call(method, files=None, **p):
        if method == "sendMessage":
            raise RuntimeError("telegram down")
        return {"message_id": 9}
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(delivery.telegram_bot, "call", call)

    with pytest.raises(RuntimeError):
        delivery.deliver(day, "2026-06-11-hall", "777", ledger)
    assert [e["id"] for e in ledger] == ["2026-06-11-hall"]
    assert (day / "delivered.json").exists()     # persisted, not just in memory
