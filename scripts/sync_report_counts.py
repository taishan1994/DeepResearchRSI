#!/usr/bin/env python
"""把 research/<slug>/REPORT.md 里的校验计数行与实际数据同步。

⚠️ 为什么需要这个工具：
   tests/test_schemas.py 有两条断言专门防止「文档计数漂移」——
   test_report_header_counts_match_data 和 test_docs_quote_real_counts。
   它们能**发现**漂移，但不能**修复**漂移。
   于是每次往归档里补数据，就得手工改 REPORT.md 和 README.md 里的数字，
   而手工改必然出错：本次就发现 rtx-pro-6000 的归档已从
   2997/2233/1877 长到 3002/2238/1882，文档还停在旧值上。

   这个工具把「抄写」换成「重算」：
     - 用 validate_research_dir() 拿到权威计数
     - 只替换形如 `sources=N, evidence=N, ...` 的那一行
     - 同时更新 research/README.md 表格里对应 slug 的那格
   默认 dry-run，加 --apply 才写入。

用法：
    python scripts/sync_report_counts.py                # 全部归档，dry-run
    python scripts/sync_report_counts.py --apply        # 真正写入
    python scripts/sync_report_counts.py --slug X --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi.validate import validate_research_dir  # noqa: E402

# 匹配 REPORT.md 里那行校验结果。允许用反引号包裹，也允许没有。
RESULT_RE = re.compile(
    r"sources=\d+, evidence=\d+, claims=\d+, claims_high=\d+"
    r"(?:, claims_disputed=\d+)?(?:, trace_events=\d+)?"
    r"(?:, c3_violations=\d+)?(?:, subquestions=\d+)?"
    r"(?:, r2_violations=\d+)?(?:, c1_violations=\d+)?"
)

# research/README.md 表格行：| [slug](./slug/REPORT.md) | 主题 | 规模 |
README_ROW_RE = re.compile(
    r"^\| \[(?P<slug>[a-z0-9-]+)\]\(\./(?P=slug)/REPORT\.md\) \| (?P<topic>[^|]+)\|"
    r" (?P<scale>[^|]+)\|$"
)


def build_result_line(stats: dict) -> str:
    """按 validate_research_dir 的返回顺序拼出与既有格式一致的一行。"""
    order = [
        "sources", "evidence", "claims", "claims_high", "claims_disputed",
        "trace_events", "c3_violations", "subquestions",
        "r2_violations", "c1_violations",
    ]
    return ", ".join(f"{k}={stats[k]}" for k in order if k in stats)


def sync_report(slug_dir: Path, apply: bool) -> tuple[bool, str]:
    report = slug_dir / "REPORT.md"
    if not report.exists():
        return False, "无 REPORT.md"
    stats = validate_research_dir(slug_dir)
    new_line = build_result_line(stats)
    text = report.read_text(encoding="utf-8")
    m = RESULT_RE.search(text)
    if not m:
        return False, "REPORT.md 中找不到校验计数行"
    old_line = m.group(0)
    if old_line == new_line:
        return False, "已是最新"
    if apply:
        report.write_text(text[:m.start()] + new_line + text[m.end():],
                          encoding="utf-8", newline="\n")
    return True, f"{old_line}\n      -> {new_line}"


def sync_readme(results: dict[str, dict], apply: bool) -> list[str]:
    """把 research/README.md 表格里的规模列按实际计数重写。"""
    readme = ROOT / "research" / "README.md"
    if not readme.exists():
        return ["无 research/README.md"]
    lines = readme.read_text(encoding="utf-8").split("\n")
    changed: list[str] = []
    for i, ln in enumerate(lines):
        m = README_ROW_RE.match(ln)
        if not m:
            continue
        slug = m.group("slug")
        st = results.get(slug)
        if not st:
            continue
        scale = (
            f" **{st['sources']} 来源 / {st['evidence']} 证据 / {st['claims']} 主张"
            f"（{st['claims_high']} 高置信）/ {st.get('claims_disputed', 0)} 争议** "
        )
        new_ln = (f"| [{slug}](./{slug}/REPORT.md) | {m.group('topic')}|{scale}|")
        if new_ln != ln:
            changed.append(f"{slug}: {ln.strip()}\n      -> {new_ln.strip()}")
            lines[i] = new_ln
    if changed and apply:
        readme.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return changed


def sync_eval_cases(results: dict[str, dict], apply: bool) -> list[str]:
    """把 evals/cases/README.md 里散落在正文中的「N 来源、N 证据、N 主张」重写。

    ⚠️ 这里没有 slug 表格行可配对，所以按「同段落内同时出现三个数」定位：
       形如 `447 来源、2997 证据、2233 主张`。
       若该文件里出现多组，按出现顺序依次对应 results 中的归档 —— 但为避免
       猜错，本函数只在**恰好一组**时才改写，多于一组就跳过并提示手动处理。
    """
    f = ROOT / "evals" / "cases" / "README.md"
    if not f.exists():
        return []
    text = f.read_text(encoding="utf-8")
    # 三连数字：来源 / 证据 / 主张（分隔符可能是 、, /）
    triple_re = re.compile(
        r"(\d+)\s*(?:来源|sources)[、,，/\s]+(\d+)\s*(?:证据|evidence)"
        r"[、,，/\s]+(\d+)\s*(?:主张|claims)"
    )
    hits = list(triple_re.finditer(text))
    if len(hits) != 1:
        if len(hits) > 1:
            return [f"evals/cases/README.md 有 {len(hits)} 组计数，需手动确认对应归档"]
        return []
    m = hits[0]
    # ⚠️ 必须先确认这个文件讲的是**哪个**归档，再决定要不要改。
    # 曾经的错误：加了 --slug cuda-kernel-rl 后 results 只剩一个归档，
    # 代码就无条件把它的计数写进 evals/cases/README.md——
    # 而那个文件讲的是 rtx-pro-6000（447 来源），被改成了 20 来源。
    # 「只有一个候选」不等于「就是这个候选」。
    mentioned = [s for s in results if s in text]
    if not mentioned:
        return ["evals/cases/README.md 未提及任何本次处理的归档，跳过"]
    if len(mentioned) > 1:
        return [f"evals/cases/README.md 同时提到多个归档 {mentioned}，需手动确认"]
    st = results[mentioned[0]]
    new = f"{st['sources']} 来源、{st['evidence']} 证据、{st['claims']} 主张"
    old = m.group(0)
    if old == new:
        return []
    if apply:
        f.write_text(text[:m.start()] + new + text[m.end():],
                     encoding="utf-8", newline="\n")
    return [f"evals/cases/README.md: {old} -> {new}"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="同步 REPORT.md / README.md 的校验计数")
    ap.add_argument("--slug", default=None, help="只处理某个归档；省略则全部")
    ap.add_argument("--apply", action="store_true", help="真正写入（默认 dry-run）")
    args = ap.parse_args(argv)

    research = ROOT / "research"
    targets = ([research / args.slug] if args.slug
               else sorted(p for p in research.iterdir()
                           if p.is_dir() and (p / "claims.csv").exists()))
    if not targets:
        print("没有找到任何归档")
        return 1

    all_stats: dict[str, dict] = {}
    dirty = 0
    for d in targets:
        try:
            st = validate_research_dir(d)
        except Exception as exc:  # noqa: BLE001
            print(f"[SKIP] {d.name}: 校验未通过 — {exc}")
            continue
        all_stats[d.name] = st
        changed, msg = sync_report(d, args.apply)
        if changed:
            dirty += 1
            print(f"[{'WROTE' if args.apply else 'DIFF'}] {d.name}/REPORT.md:\n      {msg}")
        else:
            print(f"[ OK ] {d.name}/REPORT.md: {msg}")

    readme_changes = sync_readme(all_stats, args.apply)
    for c in readme_changes:
        print(f"[{'WROTE' if args.apply else 'DIFF'}] research/README.md:\n      {c}")

    eval_changes = sync_eval_cases(all_stats, args.apply)
    for c in eval_changes:
        print(f"[{'WROTE' if args.apply else 'DIFF'}] {c}")

    total = dirty + len(readme_changes) + len(eval_changes)
    if not args.apply and total:
        print(f"\n共 {total} 处待同步；加 --apply 写入。")
    elif not total:
        print("\n全部一致，无需改动。")
    else:
        print(f"\n已写入 {total} 处。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
