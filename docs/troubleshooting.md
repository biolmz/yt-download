# Troubleshooting

Every entry below comes from a failure actually observed in the wild, with the real root cause
rather than a guess. Start by reading the **startup banner** — it tells you which components were
found:

```
====================================================================
  yt-dlp 版本 : 2026.08.19
  输出目录    : ./downloads
  ffmpeg      : ./bin/ffmpeg.exe
  ffprobe     : 未检测到（不影响下载，但无法嵌入元数据/封面）
  JS 运行时   : /usr/local/bin/node
  代理        : http://127.0.0.1:7897
  清晰度      : 1080
====================================================================
```

---

## 1. Network

### `Tunnel connection failed: 502 Bad Gateway`

**Cause** — a proxy is configured (often via the `HTTPS_PROXY` environment variable) but is not
actually able to reach YouTube, or the direct route is blocked entirely.

**Fix**

1. Let the built-in probe run — it tries the direct connection, then the common local ports.
2. If your client is on a non-standard port, pass it explicitly:

   ```bash
   yt-download <url> --proxy http://127.0.0.1:8080
   ```

3. To make it permanent for your shell:

   ```bash
   export YT_DL_PROXY=http://127.0.0.1:7890      # Linux / macOS
   setx YT_DL_PROXY http://127.0.0.1:7890       # Windows, new shells only
   ```

4. Ports probed automatically, in order: `7897`, `7890`, `2080`, `10809`, `10808`, `1080`, `8888`,
   `33210`, `4780`, `7078`. If yours is missing, open a PR — it is a one-line change in
   `PROXY_PORTS`.

**Note** — probing only ever tests `https://www.youtube.com/robots.txt`, a few hundred bytes.

### Download is extremely slow

The throughput ceiling is usually the CDN edge you were assigned, not the tool.

- Try a different YouTube client: `--player-client web_safari,android`
- Check whether the proxy itself is the bottleneck (test with `--no-auto-proxy` on a network
  where YouTube is reachable directly).
- Throttling is off by default; if you passed `--rate-limit`, remember the value is **bytes per
  second**, so `--rate-limit 1048576` is 1 MiB/s.

---

## 2. `ffprobe not found` — the most common confusing failure

### Symptom

Video and audio download to 100%, the merge appears to work, and then:

```
ERROR: Postprocessing: ffprobe not found. Please install or provide the path using --ffmpeg-location
ERROR: [youtube] <id>: ...
  成功 0 个，失败 1 个。
```

A finished, perfectly playable file is left behind in `downloads/.part/`.

### Root cause

`ffmpeg` and `ffprobe` are **two separate programs**, even though they ship in the same archive.
Most people install only `ffmpeg`.

yt-dlp's `FFmpegMetadataPP.run()` calls `self._fixup_chapters(info)` before doing anything else.
That helper only calls `ffprobe` when the **last chapter has no `end_time`**:

```python
def _fixup_chapters(self, info):
    last_chapter = traverse_obj(info, ('chapters', -1))
    if last_chapter and not last_chapter.get('end_time'):
        last_chapter['end_time'] = self._get_real_video_duration(info['filepath'])   # -> ffprobe
```

Live-stream VODs are exactly this case: the final "chapter" is still open-ended. So a download can
succeed completely and still be reported as a failure.

### Fix

Install `ffprobe` as well. It is inside the same download as `ffmpeg`:

| Platform | How |
|---|---|
| Windows | Download a build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [BtbN](https://github.com/BtbN/FFmpeg-Builds/releases), unzip, and put **both** `ffmpeg.exe` and `ffprobe.exe` in `./bin/` |
| macOS | `brew install ffmpeg` (installs both) |
| Debian/Ubuntu | `sudo apt install ffmpeg` (installs both) |
| Arch | `sudo pacman -S ffmpeg` |

If your binary lives somewhere unusual:

```bash
export YT_DL_FFPROBE=/opt/ffmpeg/bin/ffprobe
```

**What yt-download does about it** — when `ffprobe` is missing it now skips the embedding step
entirely, prints `[提示] 无 ffprobe，跳过元数据嵌入`, and still writes the `.info.json` sidecar.
Your download is never thrown away.

### Recovering a stranded file

The merged file in `downloads/.part/` is complete. Move it up one level and rename the extension:

```bash
mv downloads/.part/*.mkv downloads/
```

---

## 3. Missing high-resolution formats

### `No supported JavaScript runtime could be found`

```
WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is enabled by default;
to use another runtime add --js-runtimes RUNTIME[:PATH] ...
```

**Cause** — modern YouTube extraction needs a JavaScript runtime to compute signatures and PO
tokens. yt-dlp enables only `deno` by default, and almost nobody has `deno` installed.

**Fix** — install Node.js (the common choice), or point at an existing binary:

```bash
yt-download <url> --js-runtime node
yt-download <url> --js-runtime-path /opt/node/bin/node
export YT_DL_NODE=/opt/node/bin/node       # persistent
```

yt-download detects `node`, `deno` and `bun` automatically and passes them to yt-dlp, so in most
cases installing Node.js is all you need.

### Formats cap out at 720p or 360p

Two independent causes, check both:

| Cause | Check | Fix |
|---|---|---|
| No `ffmpeg` | banner says `ffmpeg: 未检测到` | Install `ffmpeg`; without it yt-download can only take a single progressive stream |
| No JS runtime | banner says `JS 运行时: 未检测到` | Install Node.js |

---

## 4. Subtitles

### `Unable to download video subtitles for 'zh-Hans': HTTP Error 429: Too Many Requests`

**Cause** — YouTube rate-limits the timedtext endpoint aggressively, per language and per IP.

**Not a problem** — this is a warning, not a failure. The video, audio, thumbnail and the other
subtitle languages are unaffected. yt-download sets yt-dlp's error tolerance whenever `--subs` is
used, precisely so this cannot abort the download.

**Fix**

- Narrow the scope: `--subs-langs en`
- Retry later — the limit is time-based
- Use cookies: `--cookies-from-browser chrome`

### No subtitles at all

- Confirm the video has any: `--list-formats` and `--info-only` reveal available tracks.
- `--subs` fetches manual **and** auto-generated tracks. `--embed-subs` additionally requires
  `ffmpeg`.

---

## 5. Bot checks and sign-in walls

### `Sign in to confirm you're not a bot`

**Fix, in order of least intrusive:**

1. `pip install curl_cffi` — enables browser impersonation; yt-download needs no extra flags for
   this, yt-dlp uses it automatically once present.
2. `--cookies-from-browser chrome` (or `edge`, `firefox`, `brave`). Close the browser first —
   some browsers lock their cookie database while running.
3. `--cookies-file cookies.txt` — export in Netscape format, e.g. with a browser extension.
4. Try another client: `--player-client web_safari,android`.

Treat exported cookies like passwords: `cookies.txt` is already in `.gitignore`, keep it out of
repositories, chats and screenshots.

### `Requested format is not available`

Sometimes a specific client does not expose a given format. Either drop `-q` (let yt-dlp choose),
or change the client with `--player-client`. Run `--list-formats` to see what the current client
actually offers.

---

## 6. Headless servers (no display, no media libraries)

yt-dlp itself needs no display, but a minimal server may lack shared libraries:

```bash
# Debian/Ubuntu, minimum for ffmpeg-based post-processing
sudo apt install ffmpeg
# if libav* complains about missing codecs, install the full set
sudo apt install libavcodec-extra
```

For a truly stateless container, mount a volume for `downloads/` and set
`--download-archive` on persistent storage so reruns skip completed videos.

---

## 7. Windows specifics

- **Garbled titles or progress bar** — fixed. The tool forces UTF-8 on stdout/stderr; if you still
  see mojibake in an old terminal, run `chcp 65001` first.
- **Path length limits** — very long titles can exceed the legacy `MAX_PATH`. yt-download limits
  filenames to 150 characters and enables `windowsfilenames` sanitisation. For stubborn cases,
  change the template:

  ```bash
  yt-download <url> -t "%(id)s.%(ext)s"
  ```

- **`'yt-download' is not recognized`** — either the Scripts directory is not on `PATH`, or you
  installed with `pip install --user`. Call the module instead: `python yt_download.py <url>`.

---

## 8. Still stuck?

1. Update first — most "bugs" are stale extractors:

   ```bash
   pip install -U yt-dlp
   ```

2. Reproduce with upstream yt-dlp directly, to see whether the problem is in the wrapper at all:

   ```bash
   yt-dlp -v --simulate "<url>"
   ```

3. If it fails there too, it is an extractor issue and belongs at
   [yt-dlp/issues](https://github.com/yt-dlp/yt-dlp/issues).

4. Otherwise open a Bug report and include the startup banner, your exact command, and the full
   output.
