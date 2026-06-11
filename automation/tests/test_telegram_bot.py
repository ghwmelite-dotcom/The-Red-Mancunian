import telegram_bot


def test_call_posts_to_bot_api(monkeypatch):
    calls = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": {"message_id": 7}}

    def fake_post(url, data=None, files=None, timeout=None):
        calls.update(url=url, data=data, files=files)
        return FakeResp()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
    monkeypatch.setattr(telegram_bot.requests, "post", fake_post)
    result = telegram_bot.call("sendMessage", chat_id="42", text="hi")
    assert calls["url"] == "https://api.telegram.org/botTOK/sendMessage"
    assert calls["data"] == {"chat_id": "42", "text": "hi"}
    assert result == {"message_id": 7}


def test_send_alert_uses_chat_id_env(monkeypatch):
    sent = {}
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(telegram_bot, "call",
                        lambda method, **p: sent.update(method=method, **p))
    telegram_bot.send_alert("boom")
    assert sent == {"method": "sendMessage", "chat_id": "42", "text": "boom"}
