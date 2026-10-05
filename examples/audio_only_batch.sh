#!/usr/bin/env bash
#
# Turn a list of URLs into tagged mp3 files.
#
#   ./audio_only_batch.sh urls.txt ./music
#
# urls.txt: one URL per line, blank lines and # comments ignored.

set -euo pipefail

LIST_FILE="${1:?usage: $0 <urls.txt> [output-dir]}"
OUT_DIR="${2:-./audio}"
ARCHIVE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/yt-download"
ARCHIVE_FILE="$ARCHIVE_DIR/audio.txt"

[[ -f "$LIST_FILE" ]] || { echo "No such file: $LIST_FILE" >&2; exit 1; }

# Strip comments and blank lines into an array.
mapfile -t URLS < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$LIST_FILE")
(( ${#URLS[@]} )) || { echo "No URLs found in $LIST_FILE" >&2; exit 1; }

echo "Processing ${#URLS[@]} URL(s) -> $OUT_DIR"
mkdir -p "$OUT_DIR" "$ARCHIVE_DIR"

yt-download "${URLS[@]}" \
  --audio-only \
  --audio-format mp3 \
  --audio-quality 0 \
  --meta \
  --thumb \
  --download-archive "$ARCHIVE_FILE" \
  --ignore-errors \
  --output "$OUT_DIR" \
  --template "%(artist,uploader)s - %(title)s [%(id)s].%(ext)s"

echo "Done. See $OUT_DIR"
