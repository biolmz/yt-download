#!/usr/bin/env python
"""
yt-download —— 开箱即用的 YouTube 视频 / 音频下载器（基于 yt-dlp）

用法示例：
    yt-download https://www.youtube.com/watch?v=dQw4w9WgXcQ
    yt-download <URL> -q 1080 -o ~/Videos
    yt-download <URL> --audio-only                 # 只取音频
    yt-download <URL> --subs --thumb --meta        # 顺带下字幕/封面/元数据
    yt-download <URL> --info-only                  # 只看信息，不下载
    yt-download <URL> --list-formats               # 列出所有清晰度
    yt-download <URL> --cookies-from-browser edge  # 需要登录/被风控拦截时
    yt-download <URL> --proxy http://127.0.0.1:7890
    yt-download <URL1> <URL2> --download-archive seen.txt   # 批量增量爬

自动处理的三件事：
    1) 代理      —— 直连不通时自动探测本地常见代理端口（7897/7890/10809 ...）
    2) JS 运行时 —— 自动找 node / deno / bun（新版 YouTube 提取必需，缺了会掉清晰度）
    3) ffmpeg/ffprobe —— 在 PATH、项目 bin/ 目录、脚本同目录中查找；
       ffmpeg 缺失 -> 降级为单文件格式；ffprobe 缺失 -> 跳过元数据嵌入

依赖：yt-dlp（pip install -U yt-dlp）。
可选但强烈建议：ffmpeg + ffprobe（注意这是两个独立程序）、node。
环境变量可用 YT_DL_FFMPEG / YT_DL_FFPROBE / YT_DL_NODE / YT_DL_PROXY 覆盖自动探测。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

__version__ = "1.0.0"
__all__ = ["main", "build_options", "find_ffmpeg", "find_ffprobe", "find_node",
           "detect_proxy", "human_bytes", "human_time", "QUALITY_PRESETS"]

PROJECT_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- 控制台 & 工具

def _fix_console() -> None:
    """Windows 控制台默认 GBK，中文进度条会炸成乱码，这里强制 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _search_dirs() -> list[Path]:
    """按优先级返回查找外部程序（ffmpeg/ffprobe/node）的目录列表。"""
    dirs = [PROJECT_ROOT]                    # 项目根目录（用户往往把 exe 扔这儿）
    dirs.append(PROJECT_ROOT / "bin")        # 约定的二进制目录
    try:
        dirs.append(Path.cwd())
        if Path.cwd() != PROJECT_ROOT:
            dirs.append(Path.cwd() / "bin")
    except OSError:
        pass
    return dirs


def _find_local_program(names: tuple[str, ...], env_var: str | None = None) -> str | None:
    """
    通用外部程序查找：环境变量 -> PATH -> 项目 bin/ -> 脚本同目录 -> 当前目录。
    names 里应同时包含 Windows 带 .exe 的名字和不带的名字。
    """
    if env_var:
        override = os.environ.get(env_var)
        if override:
            p = Path(override).expanduser()
            if p.is_file():
                return str(p)
    for name in names:
        exe = shutil.which(name)
        if exe:
            return exe
    for d in _search_dirs():
        for name in names:
            cand = d / name
            if cand.is_file():
                return str(cand)
    return None


def find_ffmpeg() -> str | None:
    """找一个可用的 ffmpeg：PATH -> 项目 bin/ -> 脚本同目录 -> imageio_ffmpeg。"""
    found = _find_local_program(("ffmpeg", "ffmpeg.exe"), "YT_DL_FFMPEG")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def find_ffprobe(ffmpeg: str | None = None) -> str | None:
    """
    找 ffprobe。注意：ffmpeg 和 ffprobe 是两个独立程序，只放 ffmpeg 是不够的。
    yt-dlp 在「章节缺少结束时间」「m3u8 修正」「拼接」等场景必须调 ffprobe，
    缺了会在最后一步 Postprocessing 报错，成品滞留 .part 目录。
    """
    names = ("ffprobe.exe", "ffprobe") if sys.platform == "win32" else ("ffprobe", "ffprobe.exe")
    found = _find_local_program(names, "YT_DL_FFPROBE")
    if found:
        return found
    if ffmpeg:
        # 跟 ffmpeg 同目录 / 上一级的 bin/ 里找（覆盖解压后没加 PATH 的发行版）
        base = Path(ffmpeg).parent
        for cand in (base, base.parent / "bin", base / "bin"):
            for name in names:
                if (cand / name).is_file():
                    return str(cand / name)
    return None


def find_node() -> str | None:
    """
    新版 YouTube 提取需要 JS 运行时（yt-dlp 默认只找 deno，多数机器没装）。
    本函数按 PATH -> 常见安装位置 找一个 JS 运行时，返回可执行文件路径。
    """
    env = os.environ.get("YT_DL_NODE")
    if env and Path(env).expanduser().is_file():
        return str(Path(env).expanduser())

    for name in ("node", "node.exe", "deno", "deno.exe", "bun", "bun.exe"):
        exe = shutil.which(name)
        if exe:
            return exe

    if sys.platform == "win32":
        roots = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "nodejs",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "nodejs",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/nodejs",
        ]
    else:
        roots = [Path("/usr/local/bin"), Path("/usr/bin"), Path("/opt/homebrew/bin")]

    for root in roots:
        for name in ("node", "node.exe", "deno", "bun"):
            cand = root / name
            if cand.is_file():
                return str(cand)
    return None


# ---------------------------------------------------------- 本地代理自动探测

# 常见代理软件默认端口（Clash/Verge、v2rayN、SSR、Mihomo ...）
PROXY_PORTS = [7897, 7890, 2080, 10809, 10808, 1080, 8888, 33210, 4780, 7078]
PROBE_URL = "https://www.youtube.com/robots.txt"


def _probe(proxy: str | None, timeout: float = 4.0) -> bool:
    """用一个极小请求测试能否到 YouTube；proxy=None 表示直连（忽略环境变量代理）。"""
    handlers = [urllib.request.ProxyHandler(
        {} if proxy is None else {"http": proxy, "https": proxy})]
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(PROBE_URL, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def detect_proxy(verbose: bool = True) -> tuple[str | None, bool]:
    """
    返回 (proxy_or_None, reachable)。
    顺序：环境变量 YT_DL_PROXY -> 直连 -> 依次试各本地代理端口。
    校园网/公司网络常把直连掐掉，这一步能省很多事。
    """
    env_proxy = os.environ.get("YT_DL_PROXY")
    if env_proxy:
        return env_proxy, _probe(env_proxy)

    if _probe(None):
        return None, True
    if verbose:
        print("  [网络] 直连不通，正在探测本地代理端口 ...")
    for port in PROXY_PORTS:
        proxy = f"http://127.0.0.1:{port}"
        if _probe(proxy):
            if verbose:
                print(f"  [网络] 使用代理 {proxy}")
            return proxy, True
    return None, False


def human_bytes(n: float | None) -> str:
    if not n:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    n = float(n)
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.1f}{units[i]}"


def human_time(sec: float | None) -> str:
    if sec is None:
        return "--:--"
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ------------------------------------------------------------------- 清晰度档位
# value = (yt-dlp format 表达式, 说明)
QUALITY_PRESETS: dict[str, tuple[str, str]] = {
    "best":  ("bv*+ba/b",            "最高画质（音视频分离，需 ffmpeg 合并）"),
    "2160":  ("bv*[height<=2160]+ba/b[height<=2160]", "4K"),
    "1440":  ("bv*[height<=1440]+ba/b[height<=1440]", "2K"),
    "1080":  ("bv*[height<=1080]+ba/b[height<=1080]", "1080p"),
    "720":   ("bv*[height<=720]+ba/b[height<=720]",   "720p"),
    "480":   ("bv*[height<=480]+ba/b[height<=480]",   "480p"),
    "360":   ("bv*[height<=360]+ba/b[height<=360]",   "360p"),
}

# 没有 ffmpeg 时的兜底：只能拿单文件渐进流（YouTube 上普通视频通常到 720p）
NO_FFMPEG_FALLBACK = "b[ext=mp4]/b[height<=720]/b"


# ----------------------------------------------------------------- 进度条回调
class ProgressPrinter:
    """把 yt-dlp 的进度回调渲染成单行进度条。"""

    def __init__(self, show: bool = True) -> None:
        self.show = show
        self._last_paint = 0.0
        self._title = ""
        self._started = time.time()

    def hook(self, d: dict) -> None:
        status = d.get("status")

        if status == "downloading":
            if not self.show:
                return
            now = time.time()
            if now - self._last_paint < 0.2:      # 限帧，别刷爆终端
                return
            self._last_paint = now

            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            pct = (done / total * 100) if total else 0.0
            speed = d.get("speed") or 0
            eta = d.get("eta")

            bar_len = 28
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)

            note = d.get("info_dict", {}).get("format_note") or ""
            line = (f"\r  {bar} {pct:5.1f}%  {human_bytes(done)}/{human_bytes(total)}"
                    f"  {human_bytes(speed)}/s  ETA {human_time(eta)}  {note}")
            sys.stdout.write(line[:150].ljust(min(len(line), 150)))
            sys.stdout.flush()

        elif status == "finished":
            if self.show:
                elapsed = time.time() - self._started
                sys.stdout.write(f"\r  下载完成，用时 {human_time(elapsed)}" + " " * 60 + "\n")
                sys.stdout.flush()
                self._started = time.time()

        elif status == "error":
            sys.stdout.write("\n  [错误] 该片段下载失败\n")


# --------------------------------------------------------------------- 下载主体

def build_options(args: argparse.Namespace, ffmpeg: str | None,
                  proxy: str | None = None, ffprobe: str | None = None) -> dict:
    """把命令行参数翻译成 yt-dlp 的 options 字典。"""
    outdir = Path(args.output).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)

    # 把 ffmpeg/ffprobe 所在目录塞进 PATH，yt-dlp 自己就能找齐两个程序
    for exe in (ffmpeg, ffprobe):
        if exe:
            d = str(Path(exe).parent)
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

    if args.audio_only:
        fmt = "ba/b"
    else:
        fmt, _ = QUALITY_PRESETS[args.quality]

    # ---- 没有 ffmpeg：降级 ----
    degraded = False
    degraded_probe = False
    if ffmpeg is None:
        if not args.audio_only:
            fmt = NO_FFMPEG_FALLBACK
            degraded = True

    opts: dict = {
        "format": fmt,
        "paths": {"home": str(outdir), "temp": str(outdir / ".part")},
        "outtmpl": {"default": args.template},
        "noprogress": True,
        "quiet": True,
        "no_warnings": False,
        "consoletitle": False,
        "ignoreerrors": args.ignore_errors,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
        "windowsfilenames": True,
        "trim_file_name": 150,
        "overwrites": args.force,
        "progress_hooks": [ProgressPrinter(show=not args.quiet_mode).hook],
        "postprocessor_hooks": [],
    }

    if args.cookies_from_browser:
        opts["cookiesfrombrowser"] = (args.cookies_from_browser,)
    if args.cookies_file:
        opts["cookiefile"] = args.cookies_file
    if proxy:
        opts["proxy"] = proxy
    if args.rate_limit:
        opts["ratelimit"] = args.rate_limit
    if args.playlist:
        opts["yesplaylist"] = True
    else:
        opts["noplaylist"] = True
    if args.download_archive:
        opts["download_archive"] = args.download_archive
    if args.player_client:
        opts["extractor_args"] = {"youtube": {"player_client": args.player_client.split(",")}}
    if args.live_from_start:
        opts["live_from_start"] = True

    # ---- JS 运行时（新版 YouTube 签名/PO token 解析需要）----
    if args.js_runtime:
        name = args.js_runtime.lower()
        opts["js_runtimes"] = {name: {"path": args.js_runtime_path} if args.js_runtime_path else {}}
    elif args.js_runtime is not False:
        node = find_node()
        if node:
            opts["js_runtimes"] = {"node": {"path": node}}

    # ---- 字幕 ----
    if args.subs:
        opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": args.subs_langs.split(","),
            "subtitlesformat": "srt/vtt/best",
        })
        # YouTube 对字幕接口限流很凶（429）。字幕拿不到不该拖累正片，
        # 所以开了 --subs 就打开容错，让 yt-dlp 记录错误后继续。
        opts["ignoreerrors"] = True
        opts["retries"] = max(opts["retries"], 10)

    # ---- 封面代理图 ----
    if args.thumb:
        opts["writethumbnail"] = True

    # ---- 元数据 JSON ----
    if args.meta:
        opts["writeinfojson"] = True

    # ---- 后处理（大多需要 ffmpeg；元数据嵌入还额外需要 ffprobe）----
    pps: list[dict] = []
    if args.audio_only and ffmpeg:
        pps.append({"key": "FFmpegExtractAudio",
                    "preferredcodec": args.audio_format,
                    "preferredquality": args.audio_quality})
    elif args.audio_only:
        # 无 ffmpeg：直接落原始音频流（m4a/webm），不转码
        opts["format"] = "ba[ext=m4a]/ba/b"

    if args.thumb and ffmpeg:
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    if args.meta:
        if ffprobe:
            # add_infojson=False：省掉一次可能失败的 probe，元数据照样写入
            pps.append({"key": "FFmpegMetadata", "add_metadata": True,
                        "add_chapters": True, "add_infojson": False})
        else:
            # 没有 ffprobe 时不要嵌入：章节缺 end_time 的视频会让整步失败
            degraded_probe = True
    if args.subs and ffmpeg and args.embed_subs:
        pps.append({"key": "FFmpegEmbedSubtitle"})
    if pps:
        opts["postprocessors"] = pps

    # ffmpeg 位置：给 yt-dlp 直接指路
    if ffmpeg:
        opts["ffmpeg_location"] = str(Path(ffmpeg).parent)

    opts["_degraded"] = degraded          # 无 ffmpeg 降级标记
    opts["_no_probe"] = degraded_probe    # 无 ffprobe 降级标记
    return opts


def pick_result_file(info: dict, outdir: Path) -> Path | None:
    """从 info 里推断最终落盘文件（后处理后路径可能变）。"""
    for key in ("filepath", "_filename"):
        p = info.get(key)
        if p and Path(p).is_file():
            return Path(p)
    reqs = info.get("requested_downloads") or []
    for r in reqs:
        p = r.get("filepath")
        if p and Path(p).is_file():
            return Path(p)
    vid = info.get("id")
    if vid:
        hits = sorted(outdir.glob(f"*[[]{vid}[]]*"), key=lambda x: x.stat().st_size, reverse=True)
        hits = [h for h in hits if h.suffix not in {".json", ".jpg", ".png", ".webp", ".vtt", ".srt"}]
        if hits:
            return hits[0]
    return None


def run(urls: list[str], args: argparse.Namespace) -> int:
    try:
        import yt_dlp
    except ImportError:
        print("缺少依赖 yt-dlp。请先安装：pip install -U yt-dlp")
        return 2

    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe(ffmpeg)
    outdir = Path(args.output).expanduser()

    # ---- 代理：显式指定 > 自动探测（探测结果在同一分钟内复用）----
    if args.proxy:
        proxy = args.proxy
    elif args.no_auto_proxy:
        proxy = None
    else:
        proxy, reachable = detect_proxy(verbose=not args.quiet_mode)
        if not reachable:
            print("  [警告] YouTube 当前不可达（直连和本地常见代理端口都失败）。")
            print("         确认代理软件已开启，或用 --proxy http://127.0.0.1:端口 显式指定。\n")

    node = None if args.js_runtime is False else (args.js_runtime_path or find_node())

    print("=" * 68)
    print("  yt-dlp 版本 :", yt_dlp.version.__version__)
    print("  输出目录    :", outdir)
    print("  ffmpeg      :", ffmpeg or "未检测到（自动降级为单文件格式，最高通常 720p）")
    print("  ffprobe     :", ffprobe or "未检测到（不影响下载，但无法嵌入元数据/封面）")
    print("  JS 运行时   :", node or "未检测到（部分清晰度可能缺失，建议装 node）")
    print("  代理        :", proxy or "直连")
    print("  清晰度      :", "仅音频" if args.audio_only else args.quality)
    print("=" * 68)

    # ---------- 只查信息 ----------
    if args.info_only:
        info_opts = {"quiet": True, "skip_download": True, "noplaylist": not args.playlist}
        if args.cookies_from_browser:
            info_opts["cookiesfrombrowser"] = (args.cookies_from_browser,)
        if proxy:
            info_opts["proxy"] = proxy
        if node:
            info_opts["js_runtimes"] = {Path(node).stem.lower(): {"path": node}}
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            for u in urls:
                try:
                    info = ydl.extract_info(u, download=False)
                except Exception as e:
                    print(f"  [失败] {u}\n         {e}")
                    continue
                entries = info.get("entries") if "entries" in info else [info]
                for it in entries:
                    if not it:
                        continue
                    print(f"  标题   : {it.get('title')}")
                    print(f"  频道   : {it.get('uploader')}")
                    print(f"  时长   : {human_time(it.get('duration'))}")
                    print(f"  发布   : {it.get('upload_date')}")
                    print(f"  观看   : {it.get('view_count')}")
                    print(f"  地址   : {it.get('webpage_url')}")
                    print("-" * 68)
        return 0

    # ---------- 只列格式 ----------
    if args.list_formats:
        lf_opts: dict = {"quiet": True, "listformats": True}
        if proxy:
            lf_opts["proxy"] = proxy
        with yt_dlp.YoutubeDL(lf_opts) as ydl:
            ydl.download(urls)
        return 0

    # ---------- 正式下载 ----------
    opts = build_options(args, ffmpeg, proxy, ffprobe)
    degraded = opts.pop("_degraded", False)
    no_probe = opts.pop("_no_probe", False)
    if degraded:
        print("  [提示] 无 ffmpeg，已改用单文件渐进格式（画质上限较低）。")
        print("         装好 ffmpeg 并加进 PATH 后即可下 1080p/4K。\n")
    if no_probe:
        print("  [提示] 无 ffprobe，跳过元数据嵌入（.info.json 依旧会写到输出目录）。")
        print("         ffmpeg 与 ffprobe 是两个独立程序，需要同时具备。\n")

    fails: list[tuple[str, str]] = []
    results: list[tuple[str, Path | None, dict]] = []

    with yt_dlp.YoutubeDL(opts) as ydl:
        for u in urls:
            print(f"\n>> {u}")
            try:
                info = ydl.extract_info(u, download=True)
            except Exception as e:
                print(f"  [失败] {type(e).__name__}: {e}")
                fails.append((u, str(e)))
                continue

            entries = info.get("entries") if "entries" in info else [info]
            for it in entries:
                if not it:
                    continue
                path = pick_result_file(it, outdir)
                results.append((it.get("title") or "?", path, it))

    # ---------- 汇总 ----------
    print("\n" + "=" * 68)
    print("  下载结果")
    print("=" * 68)
    for title, path, _info in results:
        size = human_bytes(path.stat().st_size) if path and path.is_file() else "?"
        rel = path.name if path else "（文件未定位到，请检查输出目录）"
        print(f"  [OK] {title[:50]}")
        print(f"       {rel}  ({size})")
    for u, err in fails:
        print(f"  [失败] {u}\n         {err}")

    # ---------- 元数据落盘 ----------
    if args.save_json and results:
        dump = outdir / "download_report.json"
        payload = [{
            "title": it.get("title"), "id": it.get("id"),
            "uploader": it.get("uploader"), "duration": it.get("duration"),
            "upload_date": it.get("upload_date"), "view_count": it.get("view_count"),
            "webpage_url": it.get("webpage_url"),
            "file": (str(p) if p else None),
            "file_size": (p.stat().st_size if p and p.is_file() else None),
        } for _, p, it in results]
        dump.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  元数据清单已写入：{dump}")

    # ---------- 清掉空的临时目录 ----------
    tmp = outdir / ".part"
    try:
        if tmp.is_dir() and not any(tmp.iterdir()):
            tmp.rmdir()
    except OSError:
        pass

    print(f"\n  成功 {len(results)} 个，失败 {len(fails)} 个。")
    return 0 if not fails else 1


# ------------------------------------------------------------------------ CLI

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="yt-download",
        description="开箱即用的 YouTube 视频/音频下载器（基于 yt-dlp）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="例：yt-download https://youtu.be/xxxx -q 1080 --subs --meta",
    )
    p.add_argument("urls", nargs="+", help="一个或多个视频 / 播放列表 URL")
    p.add_argument("-V", "--version", action="version",
                   version=f"%(prog)s {__version__}")

    g1 = p.add_argument_group("输出与画质")
    g1.add_argument("-o", "--output", default=str(PROJECT_ROOT / "downloads"),
                    help="输出目录（默认脚本旁的 downloads/）")
    g1.add_argument("-q", "--quality", default="best", choices=sorted(QUALITY_PRESETS),
                    help="画质档位，默认 best")
    g1.add_argument("-t", "--template", default="%(title)s [%(id)s].%(ext)s",
                    help="文件名模板，默认 %%(title)s [%%(id)s].%%(ext)s")
    g1.add_argument("--playlist", action="store_true", help="下载整个播放列表（默认只下单个视频）")
    g1.add_argument("--force", action="store_true", help="已存在时强制覆盖")

    g2 = p.add_argument_group("纯音频")
    g2.add_argument("--audio-only", action="store_true", help="只下载音频")
    g2.add_argument("--audio-format", default="mp3", help="音频格式，默认 mp3（需 ffmpeg）")
    g2.add_argument("--audio-quality", default="0", help="音频质量 0(最好)-9(最差)，默认 0")

    g3 = p.add_argument_group("附加内容")
    g3.add_argument("--subs", action="store_true", help="下载字幕（含自动生成）")
    g3.add_argument("--subs-langs", default="zh-Hans,zh-Hant,en",
                    help="字幕语言，逗号分隔，默认 zh-Hans,zh-Hant,en")
    g3.add_argument("--embed-subs", action="store_true", help="把字幕嵌入视频（需 ffmpeg）")
    g3.add_argument("--thumb", action="store_true", help="下载封面图")
    g3.add_argument("--meta", action="store_true", help="写入元数据 .info.json")
    g3.add_argument("--save-json", action="store_true", help="额外输出一份汇总 download_report.json")

    g4 = p.add_argument_group("网络与风控")
    g4.add_argument("--cookies-from-browser", metavar="BROWSER",
                    help="从浏览器读 Cookie：chrome / edge / firefox / brave ...")
    g4.add_argument("--cookies-file", metavar="FILE", help="使用 cookies.txt")
    g4.add_argument("--proxy", help="显式指定代理，如 http://127.0.0.1:7897")
    g4.add_argument("--no-auto-proxy", action="store_true",
                    help="关闭本地代理端口自动探测（默认会试 7897/7890/10809 等）")
    g4.add_argument("--rate-limit", type=float, metavar="BYTES", help="限速（字节/秒）")
    g4.add_argument("--player-client", help="换 YouTube 客户端，如 web_safari,android")
    g4.add_argument("--download-archive", metavar="FILE",
                    help="下载归档文件，已下过的自动跳过（增量爬取用）")
    g4.add_argument("--js-runtime", metavar="NAME", default=None,
                    help="JS 运行时名称（默认自动找 node；可选 deno/bun/quickjs）")
    g4.add_argument("--js-runtime-path", metavar="PATH", help="JS 运行时可执行文件全路径")
    g4.add_argument("--no-js-runtime", dest="js_runtime", action="store_const", const=False,
                    help="禁用 JS 运行时")

    g5 = p.add_argument_group("其他")
    g5.add_argument("--live-from-start", action="store_true",
                    help="直播回放从头开始下（默认只下从此刻起的部分）")
    g5.add_argument("--info-only", action="store_true", help="只打印视频信息，不下载")
    g5.add_argument("--list-formats", action="store_true", help="列出所有可用格式")
    g5.add_argument("--ignore-errors", action="store_true", help="批量时遇错继续")
    g5.add_argument("--quiet", dest="quiet_mode", action="store_true", help="不显示进度条")

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _fix_console()
    args = parse_args(argv)
    try:
        return run(args.urls, args)
    except KeyboardInterrupt:
        print("\n  已手动中断。")
        return 130


if __name__ == "__main__":
    sys.exit(main())
