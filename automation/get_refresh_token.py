"""One-time: obtain a Google OAuth refresh token for YouTube uploads.

Prereqs (see automation/SETUP.md): a Google Cloud project with the YouTube
Data API v3 enabled and an OAuth client of type "Desktop app".

Run LOCALLY (it opens a browser):
    set GOOGLE_CLIENT_ID=...        (PowerShell: $env:GOOGLE_CLIENT_ID="...")
    set GOOGLE_CLIENT_SECRET=...
    python automation/get_refresh_token.py

Prints the refresh token - store it as the GOOGLE_REFRESH_TOKEN repo secret.
"""
import http.server
import os
import urllib.parse
import webbrowser

import requests

PORT = 8765
REDIRECT = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main():
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    auth_url = ("https://accounts.google.com/o/oauth2/v2/auth?" +
                urllib.parse.urlencode({
                    "client_id": client_id, "redirect_uri": REDIRECT,
                    "response_type": "code", "scope": SCOPE,
                    "access_type": "offline", "prompt": "consent"}))
    print("Opening browser - sign in as the channel owner (@theredmancunianway)...")
    webbrowser.open(auth_url)

    code_holder = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code_holder["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Done - return to the terminal.")

        def log_message(self, *a):
            pass

    with http.server.HTTPServer(("localhost", PORT), Handler) as srv:
        srv.handle_request()

    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "code": code_holder["code"], "redirect_uri": REDIRECT,
        "grant_type": "authorization_code"}, timeout=30)
    resp.raise_for_status()
    print("\nGOOGLE_REFRESH_TOKEN =", resp.json()["refresh_token"])


if __name__ == "__main__":
    main()
