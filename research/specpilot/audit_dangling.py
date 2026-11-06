"""审计：仓库代码引用了哪些**本仓库里不存在**的路径。

## 为什么这条值得单独查

论文说循环由三样东西判定：控制器（配对运行）、结构化记忆库、token forcing。
在公开树里搜这些词，命中很少——但这只能说明「没找到」。

更强的一类证据是：**仓库自己的代码在引用这些组件**，而那些路径不在树里。
例如 `techniques/budget.py` 的 docstring 指向
`research/knowledge/search_space/06_dynamic_budget.md`，`trace.py` 指向
`research/autoresearch/replay.py`，而 `research/` 下只有
`autoresearch/cudaslot.py`、`bench/`、`dflash_lab/`、`scripts/`。

这说明公开树是一个更大工作区的**裁剪子集**：机制（引擎侧）在，
判定与知识侧（knowledge / validation / replay / ar CLI）被裁掉了。
结论因此从「我没找到」升级为「作者交付的是裁剪后的树，裁剪口就在这些引用上」。

## 做法

1. 只扫非 vendored 文本（排除 `python/sglang`，那是 SGLang 的裁剪副本）；
2. 用正则找出形如 `research/xxx/yyy.md|py`、`scripts/xxx.py` 的路径引用；
3. 对每个引用检查是否存在（含相对仓库根的常见前缀）；
4. 输出「引用数 / 存在数 / 缺失清单」，并写成一份快照供 E1 引用。

用法：python audit_dangling.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(r"D:\github\specpilot")
HERE = Path(__file__).resolve().parent
SNAP = HERE / "documents" / "specpilot-dangling-refs.txt"

# 只认这些前缀：它们是本课题关心的四类组件所在的位置。
PRESENT = r"(?:knowledge|validation|autoresearch|bench|scripts|dflash_lab)"
PAT = re.compile(rf"\bresearch/({PRESENT})/[A-Za-z0-9_./-]+\.(?:md|py)\b")
# 根级 scripts/ 只在**不**被 research/ 或别的路径前缀时才算——
# 否则 `research/scripts/launch.sh` 会被截成 `scripts/launch.sh`，
# 报出一个不存在的假缺失（本脚本第一版就是这样误报了 2 条）。
PAT2 = re.compile(r"(?<![\w/.-])scripts/[A-Za-z0-9_./-]+\.(?:py|sh)\b")


def main() -> int:
    if not REPO.is_dir():
        print(f"[!] 仓库不存在：{REPO}")
        return 1

    files = [p for p in REPO.rglob("*")
             if p.is_file() and p.suffix.lower() in (".py", ".md", ".sh", ".json")
             and "python/sglang" not in p.as_posix()
             and "python\\sglang" not in p.as_posix()]

    refs: dict[str, dict] = {}
    for p in files:
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(body.splitlines(), 1):
            for m in list(PAT.finditer(line)) + list(PAT2.finditer(line)):
                rel = m.group(0)
                ent = refs.setdefault(rel, {"refs": [], "exists": (REPO / rel).exists()})
                ent["refs"].append(f"{p.relative_to(REPO).as_posix()}:{lineno}")

    missing = {k: v for k, v in refs.items() if not v["exists"]}
    present = {k: v for k, v in refs.items() if v["exists"]}

    by_area = defaultdict(lambda: {"present": 0, "missing": 0})
    for k, v in refs.items():
        parts = k.split("/")
        area = parts[1] if parts[0] == "research" else "scripts"
        by_area[area]["present" if v["exists"] else "missing"] += 1

    lines = [
        "# SpecPilot 仓库：指向不存在路径的引用（审计产物）",
        "#",
        "# 由 research/specpilot/audit_dangling.py 生成，勿手改。",
        "# 扫描范围：非 vendored 的 .py/.md/.sh/.json（排除 python/sglang）。",
        f"# 被引用的路径 {len(refs)} 个，其中缺失 {len(missing)} 个、存在 {len(present)} 个。",
        "",
        "## 按区域统计",
    ]
    for area, n in sorted(by_area.items()):
        lines.append(f"{area}: 存在 {n['present']} / 缺失 {n['missing']}")

    lines += ["", "## 缺失清单（路径 -> 引用位置）"]
    for k in sorted(missing):
        lines.append(f"{k}")
        for r in missing[k]["refs"]:
            lines.append(f"    引用：{r}")

    lines += ["", "## 存在的路径（对照用）"]
    for k in sorted(present):
        lines.append(f"{k}")

    text = "\n".join(lines) + "\n"
    SNAP.write_text(text, encoding="utf-8", newline="\n")

    out = {
        "refs_total": len(refs),
        "missing": sorted(missing),
        "present": sorted(present),
        "by_area": {k: dict(v) for k, v in sorted(by_area.items())},
        "scan_files": len(files),
    }
    (HERE / "dangling_audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"引用路径 {len(refs)}｜缺失 {len(missing)}｜存在 {len(present)}")
    print("缺失：")
    for k in sorted(missing):
        print(f"  {k}   <- {missing[k]['refs'][0]}"
              + (f" (+{len(missing[k]['refs']) - 1})" if len(missing[k]["refs"]) > 1 else ""))
    print(f"\n快照：documents/{SNAP.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
