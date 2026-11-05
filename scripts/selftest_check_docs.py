"""反例测试：验证 check_docs.py 真的会报错。

## 为什么单独写

检查器最坏的失效方式是「永远通过」。要证明它会报错，必须故意弄错，
看它是否响。本文件做两件事：

1. 备份 EVOLUTION.md
2. 依次注入 4 类错误，每次跑检查，断言失败项数 > 0
3. 无论如何都恢复原文件（try/finally）

## 为什么不放在 tests/ 里

它会改写真实文档，虽是临时且在 finally 里恢复，但放 tests/ 有风险
（被中途 kill 就留下错误文档）。故做成手动运行的脚本，
写在这里是为了「检查器有测试」这件事本身可复查。

## 与上一版的区别

上一版我用 PowerShell here-string 做替换，反引号被吞掉，替换静默失败，
于是「注入错误后检查仍通过」被我误读成「检查器有漏洞」。
改为 Python 文件后，替换与断言在同一进程里，且替换失败会断言失败。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "EVOLUTION.md"
BAK = ROOT / "docs" / "_evo_selftest.bak"


def _spot(pattern: str) -> str | None:
    """从文档里取一处真实存在的锚点，找不到返回 None。

    ⚠️ 之前这里的锚点是**硬编码**的（`| 提交总数 | 314 |`、
    `（**20.4%**）`）。文档每次同步统计值，这两个用例的锚点就失效，
    selftest 于是报「锚点不在文档里」——**测试文本过期，
    而它本来是用来防过期的**。

    改为运行时从文档提取：只要格式还在，锚点就永远有效。
    找不到时跳过该用例并提示，而不是静默通过。
    """
    text = DOC.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    return m.group(0) if m else None


def _cases() -> list[tuple[str, str, str, str]]:
    """运行时构造用例；锚点取自当前文档。"""
    out: list[tuple[str, str, str, str]] = []

    a = _spot(r"\| 提交总数 \| \d+ \|")
    if a:
        out.append(("提交总数", a,
                    re.sub(r"\d+", "999", a), "总数写错"))

    out.append(("E1 覆盖率", "| `cuda-kernel-rl` | 37 | 37 | **100%** |",
                "| `cuda-kernel-rl` | 37 | 37 | **88%** |",
                "覆盖率写错（只验自洽会漏）"))
    out.append(("证据数", "| `cuda-kernel-gen` | 19 | 18 | 95% |",
                "| `cuda-kernel-gen` | 88 | 18 | 95% |",
                "证据数写错"))

    b = _spot(r"（\*\*\d+\.\d%\*\*）")
    if b:
        out.append(("自我纠正比例", b,
                    re.sub(r"\d+\.\d", "55.5", b), "比例写错"))
    return out


CASES = _cases()


def run_check() -> int:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_docs.py")],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"失败 (\d+) 项", r.stdout or "")
    return int(m.group(1)) if m else 0


def main() -> int:
    if not DOC.is_file():
        print("[!] EVOLUTION.md 不存在")
        return 1
    shutil.copy2(DOC, BAK)
    original = DOC.read_text(encoding="utf-8")
    failures = 0
    try:
        base = run_check()
        print(f"基线（未注入错误）：{base} 项失败")
        if base != 0:
            print("[!] 基线就不通过，先修文档")
            return 1

        for name, old, new, why in CASES:
            if old not in original:
                print(f"[!] 用例「{name}」的锚点不在文档里：{old[:40]}")
                failures += 1
                continue
            DOC.write_text(original.replace(old, new, 1),
                           encoding="utf-8", newline="\n")
            n = run_check()
            status = "抓到" if n > 0 else "漏掉"
            print(f"  [{status}] {name} —— {why}（失败 {n} 项）")
            if n == 0:
                failures += 1
    finally:
        DOC.write_text(original, encoding="utf-8", newline="\n")
        BAK.unlink(missing_ok=True)

    # 确认恢复后仍然通过
    after = run_check()
    print(f"\n恢复后：{after} 项失败")
    if after != 0:
        print("[!] 恢复后不通过，文档可能已被破坏")
        failures += 1

    print(f"\n{'[OK] 4 个反例全部抓到' if failures == 0 else f'[!] {failures} 处问题'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
