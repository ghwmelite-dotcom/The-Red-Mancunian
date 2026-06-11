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


def test_deliver_sends_video_then_caption(tmp_path, monkeypatch):
    day = tmp_path
    (day / "2026-06-11-hall.mp4").write_bytes(b"vid")
    (day / "2026-06-11-hall-caption.txt").write_text("caption text", encoding="utf-8")
    (day / "2026-06-11-hall.json").write_text(json.dumps(
        {"hook": {"text": "HOOK"}, "category": "TRANSFER",
         "status": "REPORTED", "source": "Sky Sports"}), encoding="utf-8")

    sent = []
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(delivery.telegram_bot, "call",
                        lambda method, files=None, **p:
                        (sent.append((method, p)), {"message_id": 9})[1])
    delivery.deliver(day, "2026-06-11-hall", "777")

    assert sent[0][0] == "sendVideo"
    assert "HOOK" in sent[0][1]["caption"]
    keyboard = json.loads(sent[0][1]["reply_markup"])
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == "ok:777:2026-06-11-hall"
    assert sent[1] == ("sendMessage",
                       {"chat_id": "42", "text": "caption text",
                        "reply_to_message_id": 9})
