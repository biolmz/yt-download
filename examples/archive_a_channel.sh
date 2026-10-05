#!/usr/bin/env bash
#
# Archive a channel: fetch every upload, 1080p, resumable, rerunnable safely.
#
#   ./archive_a_channel.sh "https://www.youtube.com/@SomeChannel"
#
# Safe to put in cron: already-downloaded videos are skipped via the archive file,
# so a second run only fetches what is new.

set -euo pipefail

CHANNEL_URL="${1:?usage: $0 <channel-or-playlist-url> [output-dir]}"
OUT_DIR="${2:-$HOME/Videos/yt-archive}"
ARCHIVE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/yt-download"
ARCHIVE_FILE="$ARCHIVE_DIR/channel.txt"

mkdir -p "$OUT_DIR" "$ARCHIVE_DIR"

echo "Channel : $CHANNEL_URL"
echo "Output  : $OUT_DIR"
echo "Archive : $ARCHIVE_FILE"
echo

yt-download "$CHANNEL_URL" \
  --playlist \
  --quality 1080 \
  --download-archive "$ARCHIVE_FILE" \
  --subs --subs-langs en \
  --thumb \
  --meta \
  --save-json \
  --ignore-errors \
  --output "$OUT_DIR" \
  --template "%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s"

echo
echo "Done. Finished videos are recorded in $ARCHIVE_FILE"
echo "Run again later to pick up only the new uploads."
