# Contributing to yt-download

Thanks for wanting to help. This is a small project with a deliberately narrow scope,
so a short read here saves everyone time.

## Project scope

`yt-download` is a **thin orchestration wrapper** around [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

**In scope** — anything that removes friction around the download:

- environment detection (proxy, JS runtime, `ffmpeg` / `ffprobe`)
- progress reporting, result summaries, clear error messages
- CLI ergonomics, sane defaults, graceful degradation
- packaging, docs, tests, CI

**Out of scope** — things that belong upstream:

- support for a specific site, format or DRM scheme → please contribute to `yt-dlp`
- a GUI, a web server, or a background daemon
- bypassing access controls, paywalls or authentication you do not have
- bundling `ffmpeg` / `ffprobe` / Node binaries into this repository (they are large and
  distribution-restricted — we detect them instead)

If you are unsure which side of the line your idea falls on, open a Feature request first.

## Development setup

```bash
git clone https://github.com/biolmz/yt-download.git
cd yt-download

python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"       # includes pytest and ruff
```

Run the checks:

```bash
pytest -q          # must stay fully offline — never hits the network
ruff check .       # must be clean
```

## Ground rules

1. **Keep the test suite offline.** Tests must never contact YouTube or any network service.
   Anything that needs the network goes behind a manual step, not CI.
2. **Stay a single module.** `yt_download.py` is meant to be readable, auditable and vendorable.
   Adding a dependency needs a very good reason.
3. **Only `yt-dlp` is a hard dependency.** Everything else — `ffmpeg`, `ffprobe`, Node,
   `curl_cffi` — must remain optional, with a documented degradation path.
4. **Degrade, never lose a download.** If an optional component is missing, fall back and print
   an actionable warning. Deleting a successful download because a post-processing step failed
   is a bug.
5. **Do not hardcode machine-specific paths.** Use the `_search_dirs()` / `_find_local_program()`
   helpers and honour the `YT_DL_*` environment variables.
6. **Be accurate in docs.** Only document flags that exist, and only claim behaviour that the
   code actually implements. Measured facts beat marketing.

## Adding a CLI flag

1. Add it to `parse_args()` in the appropriate argument group, with a one-line help string.
2. Wire it into `build_options()` — that function is the single place where CLI intent becomes
   yt-dlp options.
3. If it can fail or needs an external program, add the degradation path and a warning.
4. Add tests in `tests/test_yt_download.py` covering the happy path and the degraded path.
5. Document it in **both** `README.md` and `README.zh-CN.md`.
6. Add a `CHANGELOG.md` entry under `[Unreleased]`.

## Commit messages

Conventional Commits style, please:

```
feat: probe additional local proxy ports
fix: skip metadata embedding when ffprobe is missing
docs: clarify that ffmpeg and ffprobe are separate binaries
test: cover the no-ffmpeg fallback format
chore: bump yt-dlp in CI
```

## Pull requests

- Keep them focused — one logical change per PR.
- Fill in the PR template, including the verification section with a real run.
- Make sure `pytest` and `ruff check .` pass.
- Maintainers may ask you to split a PR if it mixes unrelated changes.

## Reporting bugs

Use the Bug report form. The more of this you include, the faster it gets fixed:

```
yt-download --version
yt-dlp --version
ffmpeg -version
ffprobe -version
node --version
```

plus the exact command you ran and its complete output, including the startup banner.

## Legal

By contributing you agree that your work is licensed under the [MIT License](LICENSE).
Please do not submit code whose purpose is to circumvent copyright protection or access controls.
