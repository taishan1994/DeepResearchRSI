"""临时调试脚本：把上一版 PAPER.pdf 从 git 历史里取出来对照。

不是归档生成链的一部分，保留只为记录当时怎么比对旧版。
路径全部从脚本自身位置推导，不依赖本机目录结构。
"""

import subprocess
import tempfile
from pathlib import Path

# notes/ -> rsi-model-training/ -> research/ -> 仓库根
ROOT = Path(__file__).resolve().parents[3]

out = Path(tempfile.gettempdir()) / "rtx_old.pdf"
p = subprocess.run(["git", "show", "HEAD:research/rtx-pro-6000/paper/PAPER.pdf"],
                   cwd=str(ROOT), capture_output=True)
out.write_bytes(p.stdout)
print("bytes", out.stat().st_size)
