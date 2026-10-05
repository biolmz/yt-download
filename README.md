# yt-download

> A batteries-included YouTube video/audio downloader that **figures out your environment for you**.

[![CI](https://github.com/biolmz/yt-download/actions/workflows/ci.yml/badge.svg)](https://github.com/biolmz/yt-download/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Powered by yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[中文说明 →](README.zh-CN.md)**

---

## Why another YouTube downloader?

`yt-dlp` is excellent, but in the real world it usually fails for boring environmental reasons:
you are behind a proxy, you have no JavaScript runtime, or you only installed `ffmpeg` and forgot
that `ffprobe` is a *separate program*. Each of those produces a confusing error at the very end
of an otherwise successful download.

`yt-download` is a thin, single-file CLI wrapper that removes that friction. It is **not** a fork of
`yt-dlp` — it drives the real thing, so you keep every extractor, every format and every upstream fix.

| Common failure | How yt-download handles it |
|---|---|
| `Tunnel connection failed: 502` / direct connection blocked | Probes the usual local proxy ports (`7897`, `7890`, `10809`, `10808`, `1080`, …) and switches automatically |
| `No supported JavaScript runtime could be found` (missing formats) | Locates `node` / `deno` / `bun` and wires it into yt-dlp |
| `Postprocessing: ffprobe not found` — file stuck in `.part/` | Detects `ffmpeg` **and** `ffprobe` separately; degrades gracefully instead of losing the download |
| Mixed `.part` leftovers and unclear results | Prints a clean summary with path and size for every file |

## Features

- **Quality presets** — `best` / `2160` / `1440` / `1080` / `720` / `480` / `360`, or let yt-dlp decide
- **Audio-only mode** — transcode to `mp3` / `m4a` / `opus` / `flac`, or grab the raw audio stream
- **Extras** — subtitles (manual + auto-generated), thumbnails (optionally embedded), `.info.json` metadata
- **Playlists & batches** — multiple URLs, `--playlist`, and `--download-archive` for resumable incremental scraping
- **Resilience** — retries, resumable partial downloads, `--rate-limit`, `--cookies-from-browser`, `--proxy`, `--player-client`
- **Smart degradation** — no `ffmpeg`? falls back to a single progressive file. No `ffprobe`? skips metadata embedding with a warning instead of crashing
- **Zero-config binary discovery** — `PATH`, `./bin/`, the script directory, or `YT_DL_*` env vars
- **A live progress bar** that does not flood your terminal
- **Single file, standard library only** (plus `yt-dlp`) — read it, audit it, vendor it

## Requirements

| Component | Required | Why |
|---|---|---|
| Python 3.9+ | ✅ | runtime |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | ✅ | the actual download engine |
| [ffmpeg](https://ffmpeg.org/download.html) | recommended | merging separate video/audio streams (1080p+), audio transcoding |
| [ffprobe](https://ffmpeg.org/download.html) | recommended | media inspection — **ships in the same archive as ffmpeg but is a separate binary** |
| [Node.js](https://nodejs.org/) | recommended | YouTube signature/PO-token extraction; without it some formats are missing |
| [curl_cffi](https://pypi.org/project/curl_cffi/) | optional | browser impersonation, helps with bot checks |

## Installation

**Option A — pipx (recommended for CLI tools)**

```bash
pipx install git+https://github.com/biolmz/yt-download.git
```

**Option B — pip**

```bash
pip install git+https://github.com/biolmz/yt-download.git
# with browser impersonation support:
pip install "yt-download[impersonate] @ git+https://github.com/biolmz/yt-download.git"
```

**Option C — clone and run the script directly** (nothing to install but `yt-dlp`)

```bash
git clone https://github.com/biolmz/yt-download.git
cd yt-download
pip install -r requirements.txt
python yt_download.py --help
```

**Option D — single file.** Download `yt_download.py`, then `pip install -U yt-dlp`. That is the whole tool.

## Quick start

```bash
# highest quality available
yt-download "https://www.youtube.com/watch?v=VIDEO_ID"

# 1080p into a specific folder
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080 -o ~/Videos

# audio only
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only --audio-format mp3

# video + subtitles + cover art + metadata
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" --subs --thumb --meta

# just look, do not download
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" --info-only
```

## CLI reference

```
yt-download [-h] [-V] [-o OUTPUT] [-q {2160,1440,1080,720,480,360,best}] [-t TEMPLATE]
            [--playlist] [--force] [--audio-only] [--audio-format AUDIO_FORMAT]
            [--audio-quality AUDIO_QUALITY] [--subs] [--subs-langs SUBS_LANGS]
            [--embed-subs] [--thumb] [--meta] [--save-json]
            [--cookies-from-browser BROWSER] [--cookies-file FILE] [--proxy PROXY]
            [--no-auto-proxy] [--rate-limit BYTES] [--player-client PLAYER_CLIENT]
            [--download-archive FILE] [--js-runtime NAME] [--js-runtime-path PATH]
            [--no-js-runtime] [--live-from-start] [--info-only] [--list-formats]
            [--ignore-errors] [--quiet]
            urls [urls ...]
```

<details>
<summary><b>All options</b></summary>

**Output & quality**

| Flag | Description |
|---|---|
| `-o, --output DIR` | Output directory (default: `./downloads` next to the script) |
| `-q, --quality Q` | `best` (default), `2160`, `1440`, `1080`, `720`, `480`, `360` |
| `-t, --template T` | Filename template, default `%(title)s [%(id)s].%(ext)s` |
| `--playlist` | Download the whole playlist (default: single video only) |
| `--force` | Overwrite existing files |

**Audio**

| Flag | Description |
|---|---|
| `--audio-only` | Download audio only |
| `--audio-format F` | `mp3` (default), `m4a`, `opus`, `flac`, `wav`, … |
| `--audio-quality N` | `0` (best) – `9` (worst), default `0` |

**Extras**

| Flag | Description |
|---|---|
| `--subs` | Download subtitles, including auto-generated ones |
| `--subs-langs L` | Comma-separated language list, default `zh-Hans,zh-Hant,en` |
| `--embed-subs` | Add subtitles as a container track (needs ffmpeg) |
| `--thumb` | Download the thumbnail (embedded into the file when ffmpeg is available) |
| `--meta` | Write `.info.json` metadata (embedded when ffprobe is available) |
| `--save-json` | Also write a summary `download_report.json` |

**Network**

| Flag | Description |
|---|---|
| `--cookies-from-browser B` | Read cookies from `chrome` / `edge` / `firefox` / `brave` / … |
| `--cookies-file F` | Use a Netscape-format `cookies.txt` |
| `--proxy URL` | Explicit proxy, e.g. `http://127.0.0.1:7890` |
| `--no-auto-proxy` | Disable local proxy-port probing |
| `--rate-limit BYTES` | Throttle to N bytes/second |
| `--player-client C` | Switch YouTube client, e.g. `web_safari,android` |
| `--download-archive F` | Skip already-downloaded videos (incremental scraping) |
| `--js-runtime NAME` / `--js-runtime-path PATH` / `--no-js-runtime` | Control the JS runtime |

**Misc**

| Flag | Description |
|---|---|
| `--live-from-start` | Download a live stream from the beginning |
| `--info-only` | Print metadata only, do not download |
| `--list-formats` | List every available format |
| `--ignore-errors` | Keep going when one item in a batch fails |
| `--quiet` | Hide the progress bar |
| `-V, --version` | Print the version |

</details>

## Environment variables

| Variable | Effect |
|---|---|
| `YT_DL_FFMPEG` | Absolute path to `ffmpeg` |
| `YT_DL_FFPROBE` | Absolute path to `ffprobe` |
| `YT_DL_NODE` | Absolute path to a JS runtime (`node` / `deno` / `bun`) |
| `YT_DL_PROXY` | Force a proxy, skipping direct-connection probing |

## How the auto-detection works

1. **Proxy** — probes `https://www.youtube.com/robots.txt` directly first. If that fails, it walks the
   common local proxy ports and uses the first one that answers with `200`.
2. **JS runtime** — looks for `node`, then `deno`, then `bun` on `PATH`, then in the standard install
   locations for your OS, and passes the result to yt-dlp as `js_runtimes`.
3. **ffmpeg / ffprobe** — resolved in this order: `YT_DL_*` env var → `PATH` → `./bin/` → the script
   directory → `imageio_ffmpeg` (ffmpeg only, if installed). Their directory is prepended to `PATH`
   and handed to yt-dlp via `ffmpeg_location`.

## Reliability notes

- **`ffprobe` is not optional when embedding.** `FFmpegMetadataPP` unconditionally calls
  `_fixup_chapters()`, which needs `ffprobe` to measure the duration whenever the *last chapter has no
  `end_time`* — routine for live-stream VODs. Without `ffprobe` the merge succeeds but the download is
  reported as failed. `yt-download` detects this and skips embedding rather than losing your file.
- **Subtitle endpoints are rate limited.** HTTP `429` on one language is normal and never aborts the
  video; `--subs-langs en` or a retry later usually works, and `--cookies-from-browser` helps a lot.
- **Playlists** are opt-in (`--playlist`) so that a URL carrying `&list=` does not surprise you with
  hundreds of files.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Tunnel connection failed: 502` | Direct connection blocked | Let auto-probing run, or pass `--proxy` |
| `No supported JavaScript runtime could be found` | No `node`/`deno` on the machine | Install Node.js, or set `YT_DL_NODE` |
| `Postprocessing: ffprobe not found`, file stuck in `.part/` | Only `ffmpeg` installed | Install `ffprobe` too (same archive as ffmpeg) |
| `Unable to download video subtitles ... 429` | Subtitle rate limit | Harmless; retry later or narrow `--subs-langs` |
| `Sign in to confirm you're not a bot` | YouTube bot check | `--cookies-from-browser chrome` |
| Formats are missing above 720p | No JS runtime, or `ffmpeg` missing | Install both |
| Download is very slow | Upstream CDN | Try `--player-client web_safari,android`, or check your proxy |

More detail: [`docs/troubleshooting.md`](docs/troubleshooting.md).

## Development

```bash
git clone https://github.com/biolmz/yt-download.git
cd yt-download
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
```

The test suite is fully offline — it never touches YouTube — and CI runs it on Linux, macOS and Windows
across Python 3.9 – 3.13.

## Legal & disclaimer

This project is a convenience wrapper around [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and contains no
extraction logic of its own.

- Use it only for content you are legally entitled to download — your own uploads, public-domain works,
  Creative Commons material, or content whose licence permits it.
- Downloading copyrighted material without permission may violate YouTube's Terms of Service and the
  copyright law of your jurisdiction. **You are responsible for how you use this tool.**
- Do not use it to redistribute or commercially exploit content you do not own.
- The authors provide this software "as is", without warranty of any kind, and accept no liability for
  misuse.

## Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

[MIT](LICENSE) © yt-download contributors
