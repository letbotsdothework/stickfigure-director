#!/usr/bin/env python3
"""Upload a video to YouTube via YouTube Data API v3 (OAuth2).

Follows https://developers.google.com/youtube/data/guides/uploading_a_video

Usage:
  python3 upload_youtube.py --file VIDEO.mp4 --title "..." \
      [--description "..."] [--tags "a,b,c"] [--category 24] \
      [--privacyStatus private|unlisted|public] \
      [--publish-at "2026-11-20T09:00:00Z"] [--thumbnail THUMB.jpg]

Auth:
  - Reads CLIENT_SECRETS (OAuth client) + TOKEN (stored refresh token).
  - First run: opens the OAuth consent flow in the local browser; the
    resulting refresh token is saved to TOKEN for later runs.
"""
import argparse, os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = os.environ.get("YT_CLIENT_SECRETS", "client_secrets.json")
TOKEN = os.environ.get("YT_TOKEN", "token.json")
CHUNK = 8 * 1024 * 1024  # 8 MB chunks for resumable upload


def get_credentials():
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--category", default="24", help="24=Entertainment 28=Science&Tech 22=People&Blogs")
    ap.add_argument("--privacyStatus", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", default=None, help="ISO8601 (z.B. 2026-11-20T09:00:00Z); nur sinnvoll mit --privacyStatus private")
    ap.add_argument("--thumbnail", default=None)
    args = ap.parse_args()

    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": args.title,
            "description": args.description,
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "categoryId": args.category,
        },
        "status": {"privacyStatus": args.privacyStatus},
    }
    if args.publish_at:
        body["status"]["publishAt"] = args.publish_at

    media = MediaFileUpload(args.file, chunksize=CHUNK, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"uploaded {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"UPLOADED id={video_id}  url=https://youtu.be/{video_id}")

    if args.thumbnail:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(args.thumbnail)).execute()
        print("thumbnail set")


if __name__ == "__main__":
    main()
