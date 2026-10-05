# Examples

Copy-paste starting points. Adjust the URLs and paths.

| Script | What it does |
|---|---|
| `archive_a_channel.sh` | Download every new upload of a channel into dated folders, resumable across runs |
| `audio_only_batch.sh` | Turn a list of URLs into `mp3` files with metadata and cover art |
| `archive_a_channel.ps1` | The channel archival recipe for Windows / PowerShell |

**The one flag worth internalising is `--download-archive`.** It writes one line per finished video
to a text file and skips those on every later run. That turns any script here into something safe to
put on a schedule — rerun it as often as you like and only new videos get fetched.

```bash
yt-download "https://www.youtube.com/@channel/videos" \
  --playlist \
  --download-archive ~/.cache/yt-download/channel.txt \
  -o ~/Videos/channel
```

See the [main README](../README.md) for the full flag reference.
