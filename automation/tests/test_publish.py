import json
from datetime import datetime, timezone

import pytest

import publish


def make_artifact(tmp_path, story_id="2026-06-11-hall",
                  rendered_at="2026-06-11T18:00:00+01:00"):
    day = tmp_path / "2026-06-11"
    day.mkdir()
    (day / f"{story_id}-youtube.mp4").write_bytes(b"vid")
    (day / f"{story_id}-youtube-caption.txt").write_text("desc", encoding="utf-8")
    (day / f"{story_id}.json").write_text(json.dumps(
        {"hook": {"text": "UNITED WANT A NEW LEFT-BACK"}}), encoding="utf-8")
    (day / "meta.json").write_text(json.dumps(
        {"run_id": "777", "story_ids": [story_id],
         "rendered_at": rendered_at}), encoding="utf-8")
    return tmp_path


def test_locate_finds_files(tmp_path):
    root = make_artifact(tmp_path)
    files = publish.locate(root, "2026-06-11-hall")
    assert files["mp4"].name == "2026-06-11-hall-youtube.mp4"
    assert files["meta"]["run_id"] == "777"


def test_title_format(tmp_path):
    root = make_artifact(tmp_path)
    files = publish.locate(root, "2026-06-11-hall")
    assert publish.title_for(files) == "UNITED WANT A NEW LEFT-BACK \U0001f534 #mufc"


def test_run_refuses_stale_artifact(tmp_path, monkeypatch):
    root = make_artifact(tmp_path, rendered_at="2026-06-10T06:00:00+01:00")
    sent = []
    monkeypatch.setattr(publish.telegram_bot, "call",
                        lambda method, **p: sent.append((method, p)) or {})
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    uploaded = []
    monkeypatch.setattr(publish.youtube_upload, "upload",
                        lambda *a, **k: uploaded.append(a) or "vid123")
    now = datetime(2026, 6, 11, 23, 0, tzinfo=timezone.utc)
    publish.run(root, "2026-06-11-hall", reply_to="9", privacy="unlisted", now=now)
    assert uploaded == []
    assert "stale" in sent[0][1]["text"].lower()


def test_run_uploads_and_replies(tmp_path, monkeypatch):
    root = make_artifact(tmp_path)
    sent = []
    monkeypatch.setattr(publish.telegram_bot, "call",
                        lambda method, **p: sent.append((method, p)) or {})
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(publish.youtube_upload, "upload",
                        lambda *a, **k: "vid123")
    now = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    publish.run(root, "2026-06-11-hall", reply_to="9", privacy="unlisted", now=now)
    assert "youtube.com/shorts/vid123" in sent[0][1]["text"]
    assert sent[0][1]["reply_to_message_id"] == "9"


def test_locate_missing_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        publish.locate(tmp_path, "2026-06-11-missing")


def test_alert_failure_sends_retry_button(monkeypatch):
    sent = []
    monkeypatch.setattr(publish.telegram_bot, "call",
                        lambda method, **p: sent.append((method, p)) or {})
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    publish._alert_failure("2026-06-11-hall", "777", ValueError("boom"))
    assert sent[0][0] == "sendMessage"
    kb = json.loads(sent[0][1]["reply_markup"])
    assert kb["inline_keyboard"][0][0]["callback_data"] == "ok:777:2026-06-11-hall"
    assert "boom" in sent[0][1]["text"]
