from datetime import datetime, timezone

import youtube_upload


def test_is_stale():
    now = datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc)
    assert youtube_upload.is_stale("2026-06-11T18:00:00+01:00", now, max_hours=12)
    assert not youtube_upload.is_stale("2026-06-12T08:00:00+01:00", now, max_hours=12)


def test_build_metadata_truncates_title_and_sets_privacy():
    meta = youtube_upload.build_metadata("X" * 120, "desc", "unlisted")
    assert len(meta["snippet"]["title"]) == 100
    assert meta["snippet"]["categoryId"] == "17"          # Sports
    assert meta["status"] == {"privacyStatus": "unlisted",
                              "selfDeclaredMadeForKids": False}


def test_get_access_token(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "AT"}

    posted = {}

    def fake_post(url, data=None, timeout=None):
        posted.update(url=url, data=data)
        return FakeResp()

    for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"):
        monkeypatch.setenv(k, k.lower())
    monkeypatch.setattr(youtube_upload.requests, "post", fake_post)
    assert youtube_upload.get_access_token() == "AT"
    assert posted["url"] == "https://oauth2.googleapis.com/token"
    assert posted["data"]["grant_type"] == "refresh_token"
