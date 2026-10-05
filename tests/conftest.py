"""让 pytest 无论从哪个目录调用都能 import 到仓库根目录下的 yt_download 模块。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
