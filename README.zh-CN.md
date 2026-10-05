# yt-download

> 一个「自己会看环境」的 YouTube 视频 / 音频下载器。

[![CI](https://github.com/biolmz/yt-download/actions/workflows/ci.yml/badge.svg)](https://github.com/biolmz/yt-download/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Powered by yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-red.svg)](https://github.com/yt-dlp/yt-dlp)

**[English →](README.md)**

---

## 为什么还要做一个下载器？

`yt-dlp` 本身非常强，但它真正跑不起来的原因往往跟技术无关——要么你挂了代理，要么机器上
没有 JS 运行时，要么你只装了 `ffmpeg` 而不知道 `ffprobe` 是个**独立的程序**。
这些问题的报错都出现在下载的**最后一步**，前面几十兆流量白跑。

`yt-download` 是一层很薄的单文件 CLI 封装，专门消掉这些摩擦。它**不是** `yt-dlp` 的 fork，
而是驱动原版，所以上游的每个站点支持、每种格式、每次修复你都能吃到。

| 常见翻车现场 | yt-download 怎么处理 |
|---|---|
| `Tunnel connection failed: 502`、直连不通 | 自动探测常见本地代理端口（`7897`/`7890`/`10809`/`10808`/`1080` …）并切换 |
| `No supported JavaScript runtime could be found`，清晰度缺失 | 自动定位 `node` / `deno` / `bun` 并交给 yt-dlp |
| `Postprocessing: ffprobe not found`，成品卡在 `.part/` | 分别识别 `ffmpeg` 和 `ffprobe`；缺了就降级，绝不让整个下载白费 |
| `.part` 里一堆残留、结果说不清 | 结束时打印每个文件的路径与体积 |

## 特性

- **画质档位**：`best` / `2160` / `1440` / `1080` / `720` / `480` / `360`
- **纯音频**：转码成 `mp3` / `m4a` / `opus` / `flac`，或直接取原始音频流
- **附加内容**：字幕（人工 + 自动生成）、封面（可选嵌入）、`.info.json` 元数据
- **播放列表与批量**：支持多 URL、`--playlist`、`--download-archive` 增量爬取
- **抗造**：自动重试、断点续传、`--rate-limit` 限速、`--cookies-from-browser`、`--proxy`
- **优雅降级**：没有 `ffmpeg` 就退化为单文件格式；没有 `ffprobe` 就跳过元数据嵌入并提示
- **零配置找程序**：`PATH` → `./bin/` → 脚本目录 → `YT_DL_*` 环境变量
- **单文件、只用标准库**（外加 `yt-dlp`），方便阅读、审计、内嵌

## 依赖

| 组件 | 必需 | 用途 |
|---|---|---|
| Python 3.9+ | ✅ | 运行环境 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | ✅ | 真正的下载引擎 |
| [ffmpeg](https://ffmpeg.org/download.html) | 强烈建议 | 合并音视频分离流（1080p 以上）、音频转码 |
| [ffprobe](https://ffmpeg.org/download.html) | 强烈建议 | 媒体信息读取——**和 ffmpeg 同一个压缩包，但是两个独立程序** |
| [Node.js](https://nodejs.org/) | 强烈建议 | YouTube 签名/PO token 解析，缺了会掉清晰度 |
| [curl_cffi](https://pypi.org/project/curl_cffi/) | 可选 | 浏览器指纹模拟，降低被风控的概率 |

## 安装

**方式 A —— pipx（CLI 工具推荐）**

```bash
pipx install git+https://github.com/biolmz/yt-download.git
```

**方式 B —— pip**

```bash
pip install git+https://github.com/biolmz/yt-download.git
# 需要浏览器指纹模拟时：
pip install "yt-download[impersonate] @ git+https://github.com/biolmz/yt-download.git"
```

**方式 C —— 克隆下来直接跑脚本**（除了 `yt-dlp` 什么都不用装）

```bash
git clone https://github.com/biolmz/yt-download.git
cd yt-download
pip install -r requirements.txt
python yt_download.py --help
```

**方式 D —— 只要一个文件**：下载 `yt_download.py`，再 `pip install -U yt-dlp`，完事。

> 国内网络装依赖慢的话：
> `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -U yt-dlp curl_cffi`

## 快速上手

```bash
# 最高画质
yt-download "https://www.youtube.com/watch?v=VIDEO_ID"

# 1080p 存到指定目录
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080 -o ~/Videos

# 只要音频
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only --audio-format mp3

# 视频 + 字幕 + 封面 + 元数据
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" --subs --thumb --meta

# 只看信息，不下载
yt-download "https://www.youtube.com/watch?v=VIDEO_ID" --info-only
```

## 参数一览

| 分类 | 常用参数 |
|---|---|
| 输出与画质 | `-o DIR` 输出目录 · `-q 1080` 画质 · `-t TEMPLATE` 文件名模板 · `--playlist` 整个列表 · `--force` 覆盖 |
| 音频 | `--audio-only` · `--audio-format mp3` · `--audio-quality 0` |
| 附加内容 | `--subs` · `--subs-langs zh-Hans,en` · `--embed-subs` · `--thumb` · `--meta` · `--save-json` |
| 网络 | `--proxy URL` · `--no-auto-proxy` · `--cookies-from-browser edge` · `--cookies-file F` · `--rate-limit BYTES` · `--player-client web_safari,android` · `--download-archive seen.txt` |
| JS 运行时 | `--js-runtime node` · `--js-runtime-path PATH` · `--no-js-runtime` |
| 其他 | `--info-only` · `--list-formats` · `--live-from-start` · `--ignore-errors` · `--quiet` · `-V` 版本 |

完整说明见 [English README](README.md#cli-reference)，或直接 `yt-download --help`。

## 环境变量

| 变量 | 作用 |
|---|---|
| `YT_DL_FFMPEG` | 指定 `ffmpeg` 绝对路径 |
| `YT_DL_FFPROBE` | 指定 `ffprobe` 绝对路径 |
| `YT_DL_NODE` | 指定 JS 运行时（`node`/`deno`/`bun`）绝对路径 |
| `YT_DL_PROXY` | 强制指定代理，跳过端口探测 |

## 自动探测的三件事

1. **代理** —— 先用极小请求试直连 `https://www.youtube.com/robots.txt`；
   不通就依次试本地常见代理端口，返回 `200` 的第一个即采用。
2. **JS 运行时** —— 先 `PATH` 找 `node`/`deno`/`bun`，再找各系统默认安装位置，
   最后作为 `js_runtimes` 传给 yt-dlp。
3. **ffmpeg / ffprobe** —— 查找顺序：`YT_DL_*` 环境变量 → `PATH` → `./bin/` →
   脚本目录 → `imageio_ffmpeg`（仅 ffmpeg）。找到后会把所在目录前置进 `PATH`，
   并通过 `ffmpeg_location` 告知 yt-dlp。

## 稳定性说明（踩过的坑）

- **嵌入元数据时 `ffprobe` 不可省。** `FFmpegMetadataPP` 会无条件调用 `_fixup_chapters()`，
  当**最后一个章节没有 `end_time`**（直播回放的常态）时，必须靠 `ffprobe` 去算时长。
  没有 `ffprobe` 时合并其实已经成功，却会被判定为失败。本工具会识别这种情况并跳过嵌入，
  而不是让你丢掉文件。
- **字幕接口有限流。** 某个语言返回 `429` 是正常的，不会中断正片；
  可以 `--subs-langs en` 或稍后重试，配合 `--cookies-from-browser` 效果更好。
- **播放列表默认关闭。** 带 `&list=` 的链接不会突然给你下几百个文件，要整列表请显式加 `--playlist`。

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `Tunnel connection failed: 502` | 直连被挡 | 让自动探测跑，或 `--proxy` 指定 |
| `No supported JavaScript runtime could be found` | 机器上没有 JS 运行时 | 装 Node.js，或设 `YT_DL_NODE` |
| `Postprocessing: ffprobe not found`，文件卡在 `.part/` | 只装了 `ffmpeg` | 把 `ffprobe` 也装上（同压缩包） |
| 字幕 `429 Too Many Requests` | 字幕接口限流 | 无碍，稍后重试或缩小语言范围 |
| `Sign in to confirm you're not a bot` | 触发机器人校验 | `--cookies-from-browser chrome` |
| 720p 以上清晰度缺失 | 缺 JS 运行时或缺 `ffmpeg` | 两个都装上 |
| 速度很慢 | 上游 CDN 波动 | 试 `--player-client web_safari,android`，或检查代理 |

更多细节见 [`docs/troubleshooting.md`](docs/troubleshooting.md)。

## 开发

```bash
git clone https://github.com/biolmz/yt-download.git
cd yt-download
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
```

测试套件**完全离线**，不会访问 YouTube；CI 在 Linux / macOS / Windows 上跑 Python 3.9 – 3.13。

## 法律与免责声明

本项目是 [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) 的便捷封装，自身不含任何解析逻辑。

- 请仅用于你有权下载的内容：自己的作品、公有领域作品、CC 授权素材，或授权允许下载的内容。
- 未经许可下载受版权保护的内容，可能违反 YouTube 服务条款及你所在司法辖区的著作权法。
  **使用本工具产生的一切后果由你自行承担。**
- 请勿用于再分发或商业利用你不拥有权利的内容。
- 本项目按「原样」提供，不附带任何担保，作者不对滥用行为负责。

## 参与贡献

欢迎提 Issue 和 PR，请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE) © yt-download contributors
