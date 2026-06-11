"""Upload a Short to YouTube via resumable upload (no Google SDK needed).

Env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
Quota: one upload costs 1600 of the 10,000 daily units (= 6 uploads/day max).
"""
import os
from datetime import datetime

import requests

UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")


def is_stale(rendered_at_iso: str, now: datetime, max_hours: int = 12) -> bool:
    rendered = datetime.fromisoformat(rendered_at_iso)
    return (now - rendered).total_seconds() > max_hours * 3600


def build_metadata(title: str, description: str, privacy: str) -> dict:
    return {
        "snippet": {"title": title[:100], "description": description,
                    "categoryId": "17"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }


def get_access_token() -> str:
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def upload(mp4_path: str, title: str, description: str, privacy: str) -> str:
    """Returns the YouTube video id."""
    token = get_access_token()
    size = os.path.getsize(mp4_path)
    start = requests.post(UPLOAD_URL, json=build_metadata(title, description, privacy),
                          headers={"Authorization": f"Bearer {token}",
                                   "X-Upload-Content-Type": "video/mp4",
                                   "X-Upload-Content-Length": str(size)},
                          timeout=60)
    start.raise_for_status()
    session_url = start.headers["Location"]
    with open(mp4_path, "rb") as fh:
        done = requests.put(session_url, data=fh,
                            headers={"Content-Type": "video/mp4",
                                     "Content-Length": str(size)},
                            timeout=600)
    done.raise_for_status()
    return done.json()["id"]
