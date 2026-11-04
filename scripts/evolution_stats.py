"""从 git 历史提取「自我进化」的定量事实，供 EVOLUTION.md 引用。

## 为什么先量再写

「这个系统如何自我进化」很容易写成一段抒情：反复迭代、不断修正、
越来越可靠。这类句子读起来对，但无法验证，也无法据此改进。

故先把历史里能数出来的东西数出来：多少个提交是修错、多少个是撤回
自己上一轮的结论、多少轮是在同一个问题上反复。数字不好看不要紧——
不好看的部分正是经验所在。

## 口径（写进文档，读者可复核）

retract   提交主题含「撤回 / 推翻 / 错了 / 其实 / 更正 / 更正为」
fix       提交类型为 fix(...)
feat      提交类型为 feat(...)
chore/docs/test  其余

主题提取：`<type>(<scope>): <subject>`，无 type 时整行算 subject。

## 注意

这是**提交主题**的统计，不是「实际出错次数」的统计：一次错误可能
只提交一次修复，也可能改了三次才提交。故只能用于看趋势与比例，
不能当绝对值引用。
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evolution-stats.json"

TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?:\s*(?P<subj>.+)$")

# 「自我纠正」的语义词：作者在主题里明确推翻了自己前面的结论
RETRACT_WORDS = [
    "撤回", "推翻", "错了", "其实", "更正", "修正", "改口", "不是",
    "数错了", "看错", "误", "假象", "假设", "反而",
]


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout


def main() -> int:
    raw = git("log", "--pretty=%h%x1f%ad%x1f%s", "--date=format:%Y-%m-%d")
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) < 3:
            continue
        h, date, subj = parts[0], parts[1], "\x1f".join(parts[2:])
        m = TYPE_RE.match(subj)
        typ = m.group("type") if m else "other"
        scope = (m.group("scope") or "") if m else ""
        text = m.group("subj") if m else subj
        rows.append({"hash": h, "date": date, "type": typ,
                     "scope": scope, "subject": text, "raw": subj})

    by_type = Counter(r["type"] for r in rows)
    by_scope = Counter(r["scope"] for r in rows if r["scope"])
    by_date = Counter(r["date"] for r in rows)

    # 自我纠正：主题里出现撤回类词
    retract = [r for r in rows
               if any(w in r["subject"] for w in RETRACT_WORDS)]

    # 按 scope 看「fix 占比」，反映哪些模块被反复修
    scope_fix = defaultdict(lambda: [0, 0])
    for r in rows:
        if not r["scope"]:
            continue
        scope_fix[r["scope"]][1] += 1
        if r["type"] == "fix":
            scope_fix[r["scope"]][0] += 1

    # research 域内研究类提交（feat/fix research）单独统计
    research = [r for r in rows if r["scope"] == "research"
                or r["subject"].startswith("research")]
    paper = [r for r in rows if r["scope"] == "paper"]

    out = {
        "generated_by": "scripts/evolution_stats.py",
        "total_commits": len(rows),
        "date_range": [min(by_date), max(by_date)] if by_date else [],
        "active_days": len(by_date),
        "by_type": dict(by_type.most_common()),
        "by_scope": dict(by_scope.most_common(12)),
        "commits_per_day": dict(sorted(by_date.items())),
        "retract_commits": len(retract),
        "retract_ratio": round(len(retract) / len(rows), 3) if rows else 0,
        "retract_samples": [r["raw"] for r in retract[:12]],
        "scope_fix_ratio": {
            k: round(v[0] / v[1], 3)
            for k, v in sorted(scope_fix.items(), key=lambda kv: -kv[1][1])[:10]
        },
        "research_commits": len(research),
        "paper_commits": len(paper),
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")

    print(f"提交 {out['total_commits']} 个，跨越 {out['date_range']}，"
          f"活跃 {out['active_days']} 天")
    print(f"\n按类型：{out['by_type']}")
    print(f"按 scope（前 8）：{dict(list(out['by_scope'].items())[:8])}")
    print(f"\n自我纠正类提交：{out['retract_commits']} 个 "
          f"（占 {out['retract_ratio']:.1%}）")
    print(f"研究类 {out['research_commits']}，论文类 {out['paper_commits']}")
    print(f"\nfix 占比最高的 scope：")
    for k, v in list(out["scope_fix_ratio"].items())[:6]:
        print(f"  {k:<12} {v:.0%}")
    print(f"\n写入 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
