"""列出每个文件中所有硬编码绝对路径的具体行，供逐条判断。

## 为什么先列而不是直接替换

绝对路径有两种性质完全不同的用法：

1. **代码里的路径**（`sys.path.insert(0, r"D:\\github\\...")`、
   `ROOT = Path(r"D:\\github\\...")`）—— 可以也应该改成相对/推导。
2. **数据里的字符串**（JSON 审计结果里的 `"path": "D:\\github\\..."`）——
   它是**记录**，改了等于篡改审计当时的输入。这类要么保留，
   要么连同生成它的脚本一起改，并重新生成。

混在一起批量替换会把第 2 类变成假记录。
故本脚本只打印，不动文件。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PAT = re.compile(r"(D:\\+github|C:\\+Users\\+|/home/[a-z]|/Users/[A-Za-z])")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out = subprocess.run(["git", "ls-files"], cwd=str(root),
                         capture_output=True, text=True, encoding="utf-8")
    files = [f for f in out.stdout.splitlines()
             if f.endswith((".py", ".md", ".json", ".yaml", ".yml", ".tex",
                            ".sh", ".ps1", ".toml", ".cfg", ".ini"))]

    total = 0
    for f in files:
        p = root / f
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        hit = [(i + 1, ln) for i, ln in enumerate(lines) if PAT.search(ln)]
        if not hit:
            continue
        print(f"\n=== {f}  ({len(hit)} 行) ===")
        for n, ln in hit:
            print(f"  {n:>4}: {ln.strip()[:170]}")
            total += 1
    print(f"\n合计 {total} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
