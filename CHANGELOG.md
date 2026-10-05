# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-05

First public release. Extracted from a working internal script after it survived a real-world
download of a 26-minute 1080p live-stream VOD on a network where YouTube was unreachable
without a proxy.

### Added

- Single-file CLI (`yt_download.py`, ~600 lines, standard library only) driving `yt-dlp`.
- Quality presets: `best`, `2160`, `1440`, `1080`, `720`, `480`, `360`.
- Audio-only mode with transcoding to `mp3` / `m4a` / `opus` / `flac`, or raw stream passthrough.
- Extras: subtitles (manual + auto-generated), thumbnails, embedded metadata, `.info.json`.
- Playlist support and multi-URL batching with `--download-archive` for incremental scraping.
- Resilience options: retries, resumable downloads, `--rate-limit`, `--cookies-from-browser`,
  `--cookies-file`, `--proxy`, `--player-client`, `--live-from-start`.
- **Automatic local proxy detection** — probes `youtube.com/robots.txt` directly, then walks
  common proxy ports (`7897`, `7890`, `2080`, `10809`, `10808`, `1080`, `8888`, `33210`, `4780`, `7078`).
- **Automatic JS runtime detection** for `node` / `deno` / `bun`, passed to yt-dlp as `js_runtimes`.
- **Separate `ffmpeg` and `ffprobe` detection** with zero-config lookup order:
  `YT_DL_*` env var → `PATH` → `./bin/` → script directory → `imageio_ffmpeg`.
- **Graceful degradation** instead of failure:
  - no `ffmpeg` → falls back to a single progressive format (typically ≤720p);
  - no `ffprobe` → skips metadata embedding and still writes the `.info.json` sidecar.
- Subtitle download failures are non-fatal, so an HTTP `429` on one language cannot abort the video.
- Live progress bar with percentage, throughput and ETA, throttled to avoid flooding the terminal.
- Final summary listing every output file with its size, plus an optional `download_report.json`.
- `YT_DL_FFMPEG`, `YT_DL_FFPROBE`, `YT_DL_NODE`, `YT_DL_PROXY` environment variable overrides.
- Offline test suite (44 tests) covering format selection, option mapping and all degradation paths.
- CI across Linux, macOS and Windows on Python 3.9 – 3.13, plus wheel/sdist build validation.
- Documentation in English (`README.md`) and Chinese (`README.zh-CN.md`), with a deep
  [`docs/troubleshooting.md`](docs/troubleshooting.md).

### Fixed

- **`Postprocessing: ffprobe not found` after a successful merge.** yt-dlp's
  `FFmpegMetadataPP.run()` calls `_fixup_chapters()` unconditionally, which needs `ffprobe` to
  measure the duration whenever the **last chapter has no `end_time`** — routine for live-stream
  VODs. The merge had already succeeded, yet the whole download was reported as failed and the
  finished file was left stranded in `downloads/.part/`. Metadata embedding is now skipped
  (with a warning) when `ffprobe` is unavailable.
- **`argparse` crash on `--help`.** The filename-template help text contained `%(title)s`, which
  `argparse` tried to interpolate, raising `KeyError: 'title'`. Escaped to `%%(title)s`.
- Windows consoles defaulting to a legacy code page, which garbled non-ASCII titles and the
  progress bar; stdout/stderr are now forced to UTF-8.
- Empty `downloads/.part/` directories are now cleaned up after a run.

[Unreleased]: https://github.com/biolmz/yt-download/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/biolmz/yt-download/releases/tag/v1.0.0
