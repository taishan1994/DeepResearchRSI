"""同步 docs 里引用 evolution-stats 的统计数。

## 什么该改、什么不该改

必须改：当前统计值（提交总数、各类型数、自我纠正比例、天数）。
这些由 `scripts/evolution_stats.py` 生成，手抄进文档必然漂移——
`check_docs.py` 正是为抓这个而写的。

**不能改**：`3069 个 blob 只覆盖 198 个`。那是判据二的**历史案例**，
记录的是当时算错的分母。把 3069 改成正确值，会把「一次真实翻车」
抹成「一直都对」，反而毁掉这条教训。

这个区分很关键：同样是「文档里的一个数」，一个是**待同步的当前值**，
一个是**必须保持原样的历史事实**。自动化只该处理前者。

## 数据从哪来

不手读 JSON，直接调 evolution_stats.py 的输出，避免二次漂移。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent

# 历史案例，绝不能替换
FROZEN = {"3069", "198"}


def load_stats() -> dict:
    p = HERE / "docs" / "evolution-stats.json"
    subprocess.run([sys.executable, "scripts/evolution_stats.py"],
                   cwd=HERE, capture_output=True, text=True, timeout=120)
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    st = load_stats()
    total = st["total_commits"]
    feat = st["by_type"]["feat"]
    fix = st["by_type"]["fix"]
    retract = st["retract_commits"]
    ratio = st["retract_ratio"] * 100
    days = st["active_days"]

    # (旧值正则, 新值)，只针对明确的统计语境
    subs: list[tuple[str, str]] = [
        (r"（314 个提交）", f"（{total} 个提交）"),
        (r"在 5 天、314 个提交里，20\.4%",
         f"在 {days} 天、{total} 个提交里，{ratio:.1f}%"),
        (r"\| 提交总数 \| 314 \|", f"| 提交总数 | {total} |"),
        (r"\| 自我纠正类提交 \| 64（\*\*20\.4%\*\*） \|",
         f"| 自我纠正类提交 | {retract}（**{ratio:.1f}%**） |"),
        (r"\*\*20\.4% 这个比例", f"**{ratio:.1f}% 这个比例"),
        (r"\| 314 / 173 / 98 / 64 / 20\.4% \|",
         f"| {total} / {feat} / {fix} / {retract} / {ratio:.1f}% |"),
        (r"本仓库 314 个提交里 64 个（20\.4%）",
         f"本仓库 {total} 个提交里 {retract} 个（{ratio:.1f}%）"),
        (r"`docs/evolution-stats\.json` 的 20\.4%",
         f"`docs/evolution-stats.json` 的 {ratio:.1f}%"),
    ]

    changed = 0
    for name in ("EVOLUTION.md", "LESSONS.md"):
        p = HERE / "docs" / name
        s = p.read_text(encoding="utf-8")
        before = s
        for pat, rep in subs:
            new = re.sub(pat, rep, s)
            if new != s:
                changed += 1
                s = new
        # 完整性守卫：历史案例必须仍在
        for frozen in FROZEN:
            if frozen not in s and frozen in before:
                print(f"  [!] {name} 的历史案例 {frozen} 被误删，回滚该文件")
                s = before
                break
        if s != before:
            p.write_text(s, encoding="utf-8", newline="\n")
            print(f"  {name}: 已更新")

    print(f"\n共替换 {changed} 处")
    print(f"  提交 {total}｜feat {feat}｜fix {fix}｜"
          f"自我纠正 {retract} ({ratio:.1f}%)｜{days} 天")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
