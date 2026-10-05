"""
离线测试套件 —— 全程不访问网络，也不真正下载任何视频。

覆盖：格式化工具函数、画质档位映射、yt-dlp options 生成、
以及三条降级路径（缺 ffmpeg / 缺 ffprobe / 显式代理）。
"""

import subprocess
import sys
from pathlib import Path

import pytest

import yt_download as ytd

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "yt_download.py"


# --------------------------------------------------------------- 格式化工具

@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "?"),
        (None, "?"),
        (512, "512.0B"),
        (1024, "1.0KB"),
        (1536, "1.5KB"),
        (1024 ** 2, "1.0MB"),
        (1024 ** 3, "1.0GB"),
        (1024 ** 4, "1.0TB"),
        (1024 ** 5, "1024.0TB"),
    ],
)
def test_human_bytes(value, expected):
    assert ytd.human_bytes(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "--:--"),
        (-5, "00:00"),
        (0, "00:00"),
        (59, "00:59"),
        (60, "01:00"),
        (1566.741, "26:06"),
        (3600, "1:00:00"),
        (7325, "2:02:05"),
    ],
)
def test_human_time(value, expected):
    assert ytd.human_time(value) == expected


# ------------------------------------------------------------------ 画质档位

def test_quality_presets_are_wellformed():
    assert "best" in ytd.QUALITY_PRESETS
    for name, (expr, desc) in ytd.QUALITY_PRESETS.items():
        assert expr, f"{name} 的格式表达式不能为空"
        assert desc, f"{name} 缺少说明文字"


@pytest.mark.parametrize("quality", ["2160", "1440", "1080", "720", "480", "360"])
def test_quality_presets_cap_height(quality):
    fmt, _ = ytd.QUALITY_PRESETS[quality]
    assert f"height<={quality}" in fmt


# ------------------------------------------------------- yt-dlp options 生成

def _opts(*argv, **kwargs):
    """构造一个合法的 args，并调用 build_options。"""
    args = ytd.parse_args(["https://example.invalid/watch?v=x", *argv])
    return ytd.build_options(args, kwargs.get("ffmpeg", "/usr/bin/ffmpeg"),
                             kwargs.get("proxy"), kwargs.get("ffprobe", "/usr/bin/ffprobe"))


def test_build_options_defaults():
    opts = _opts()
    assert opts["outtmpl"]["default"] == "%(title)s [%(id)s].%(ext)s"
    assert opts["noplaylist"] is True          # 默认不下整个播放列表
    assert "yesplaylist" not in opts
    assert opts["continuedl"] is True           # 断点续传
    assert opts["windowsfilenames"] is True
    assert opts["retries"] >= 10
    assert opts["_degraded"] is False
    assert opts["_no_probe"] is False


def test_playlist_is_opt_in():
    opts = _opts("--playlist")
    assert opts["yesplaylist"] is True
    assert "noplaylist" not in opts


@pytest.mark.parametrize("quality", ["2160", "1080", "720"])
def test_quality_selects_matching_format(quality):
    opts = _opts("-q", quality)
    assert opts["format"] == ytd.QUALITY_PRESETS[quality][0]


def test_audio_only_adds_extract_postprocessor():
    opts = _opts("--audio-only", "--audio-format", "mp3")
    assert opts["format"] == "ba/b"
    keys = [pp["key"] for pp in opts["postprocessors"]]
    assert "FFmpegExtractAudio" in keys


def test_metadata_embedded_when_ffprobe_present():
    opts = _opts("--meta")
    assert opts["writeinfojson"] is True
    meta_pp = next(pp for pp in opts["postprocessors"] if pp["key"] == "FFmpegMetadata")
    assert meta_pp["add_metadata"] is True
    assert meta_pp["add_infojson"] is False     # 避免一次多余的 ffprobe 调用
    assert opts["_no_probe"] is False


# ------------------------------------------------------------ 降级路径

def test_no_ffmpeg_falls_back_to_single_file():
    args = ytd.parse_args(["https://example.invalid/watch?v=x", "-q", "1080"])
    opts = ytd.build_options(args, ffmpeg=None, proxy=None, ffprobe=None)
    assert opts["_degraded"] is True
    assert opts["format"] == ytd.NO_FFMPEG_FALLBACK
    assert "ffmpeg_location" not in opts


def test_no_ffprobe_skips_metadata_embedding():
    """缺 ffprobe 时不能挂 FFmpegMetadata，否则直播回放会整步失败。"""
    args = ytd.parse_args(["https://example.invalid/watch?v=x", "--meta"])
    opts = ytd.build_options(args, ffmpeg="/usr/bin/ffmpeg", proxy=None, ffprobe=None)
    assert opts["_no_probe"] is True
    assert opts["writeinfojson"] is True        # sidecar 元数据仍然写
    keys = [pp["key"] for pp in opts.get("postprocessors", [])]
    assert "FFmpegMetadata" not in keys


def test_no_ffmpeg_audio_uses_raw_stream():
    args = ytd.parse_args(["https://example.invalid/watch?v=x", "--audio-only"])
    opts = ytd.build_options(args, ffmpeg=None, proxy=None, ffprobe=None)
    assert opts["format"] == "ba[ext=m4a]/ba/b"


# ---------------------------------------------------------------- 网络与代理

def test_proxy_is_passed_through():
    """代理由 run() 解析后传进 build_options（显式 --proxy / 自动探测 / 环境变量三选一）。"""
    opts = _opts(proxy="http://127.0.0.1:7890")
    assert opts["proxy"] == "http://127.0.0.1:7890"


def test_no_proxy_key_when_direct():
    assert "proxy" not in _opts(proxy=None)


def test_env_proxy_override_short_circuits_probing(monkeypatch):
    """设置了 YT_DL_PROXY 时应直接采用，不做端口探测。"""
    monkeypatch.setenv("YT_DL_PROXY", "http://127.0.0.1:9999")

    calls = []

    def fake_probe(proxy, timeout=4.0):
        calls.append(proxy)
        return proxy is not None

    monkeypatch.setattr(ytd, "_probe", fake_probe)
    proxy, reachable = ytd.detect_proxy(verbose=False)
    assert proxy == "http://127.0.0.1:9999"
    assert reachable is True
    assert calls == ["http://127.0.0.1:9999"]   # 不再逐个端口去试


def test_detect_proxy_returns_none_when_nothing_reachable(monkeypatch):
    monkeypatch.delenv("YT_DL_PROXY", raising=False)
    monkeypatch.setattr(ytd, "_probe", lambda proxy, timeout=4.0: False)
    proxy, reachable = ytd.detect_proxy(verbose=False)
    assert proxy is None
    assert reachable is False


# ------------------------------------------------------------ 程序查找逻辑

def test_search_dirs_includes_project_bin():
    dirs = ytd._search_dirs()
    assert ROOT in dirs
    assert ROOT / "bin" in dirs


def test_env_var_override_for_local_program(monkeypatch, tmp_path):
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setenv("YT_DL_FFMPEG", str(fake))
    assert ytd._find_local_program(("ffmpeg", "ffmpeg.exe"), "YT_DL_FFMPEG") == str(fake)


def test_find_ffprobe_none_when_absent(monkeypatch):
    monkeypatch.delenv("YT_DL_FFPROBE", raising=False)
    monkeypatch.setattr(ytd.shutil, "which", lambda name: None)
    monkeypatch.setattr(ytd, "_search_dirs", lambda: [])
    assert ytd.find_ffprobe(None) is None


# ------------------------------------------------------------------ 命令行

def _run(*argv):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True, text=True, timeout=60,
    )


def test_cli_version():
    r = _run("--version")
    assert r.returncode == 0
    assert ytd.__version__ in (r.stdout + r.stderr)


def test_cli_help_lists_core_flags():
    r = _run("--help")
    assert r.returncode == 0
    out = r.stdout
    for flag in ("--quality", "--audio-only", "--subs", "--info-only",
                 "--proxy", "--download-archive", "--cookies-from-browser"):
        assert flag in out


def test_cli_requires_at_least_one_url():
    r = _run()
    assert r.returncode != 0
