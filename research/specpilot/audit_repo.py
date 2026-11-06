"""审计 SpecPilot 仓库，产出 repo_audit.json —— 正文里所有仓库侧数字的唯一来源。

## 为什么要有这个脚本

研究留档的硬规则是「数字由脚本算，绝不手写」（docs/LESSONS.md 2.1）。
本专题的数字分两类：

  1. **论文侧**：来自 `documents/doc-arxiv-2611-02501-full.txt` 的原文，
     由 build_specpilot.py 逐条 grab() 取子串，不手抄。
  2. **仓库侧**：文件数、去重后的源码行数、`SPECPILOT_*` 开关数、
     各 setting 的 overlay 规模——这些只能数，不能猜。

本脚本只做第 2 类，并把「检索不到」也当成结论记下来（例如控制器脚本、
记忆库文件），因为**「未交付」是一个需要证据的判断，不是一句印象**。

用法：
    python audit_repo.py [--repo D:\\github\\specpilot] [--out analysis.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "dist"}
ENV_RE = re.compile(r"SPECPILOT_[A-Z0-9_]+")

# 论文声称由「控制器 / 记忆库 / token forcing」承担的工作。
# 这些是审计对象：仓库里有没有对应实现，要有可复查的检索结果。
CLAIMED_COMPONENTS = {
    "controller": [r"\bcontroller\b", r"paired run", r"promotes? the patch"],
    "memory": [r"memory entr", r"memory\.json", r"structured memory"],
    "token_forcing": [r"token forcing", r"teacher-forced", r"mismatch rate"],
    "cost_model": [r"cost model", r"ceiling"],
}


def walk(repo: Path):
    for p in repo.rglob("*"):
        if any(part in SKIP_DIRS for part in p.relative_to(repo).parts):
            continue
        if p.is_file():
            yield p


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_lines(p: Path) -> int:
    try:
        return sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"D:\github\specpilot")
    ap.add_argument("--out", default="repo_audit.json")
    a = ap.parse_args()
    repo = Path(a.repo)
    if not repo.is_dir():
        print(f"[!] 仓库不存在：{repo}")
        return 1

    files = list(walk(repo))
    by_ext = Counter(p.suffix.lower() for p in files)

    # 同一份 overlay 文件会在多个 setting 里重复出现，故先按内容哈希去重，
    # 否则「316 个 .py / 26.6 万行」会把重复的 6 份副本算成 6 份原创代码。
    setting_py = [p for p in files if p.suffix == ".py" and "settings" in p.parts]
    seen: dict[str, int] = {}
    for p in setting_py:
        h = sha(p)
        seen.setdefault(h, count_lines(p))

    env_names: set[str] = set()
    for p in files:
        if p.suffix.lower() not in (".py", ".sh", ".md", ".json", ".cu", ".cuh"):
            continue
        try:
            env_names.update(ENV_RE.findall(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue

    settings = []
    for d in sorted((repo / "settings").iterdir()):
        cfg = d / "config.json"
        if not cfg.is_file():
            continue
        c = json.loads(cfg.read_text(encoding="utf-8"))
        overlay = [p for p in (d / "files").rglob("*") if p.is_file()] if (d / "files").is_dir() else []
        settings.append({
            "setting": d.name,
            "hardware": c.get("hardware"),
            "regime": c.get("regime"),
            "precision": c.get("precision"),
            "concurrency_levels": c.get("concurrency_levels"),
            "final_name": c["final"].get("name"),
            "final_block_size": c["final"].get("block_size"),
            "final_env_switches": len(c["final"].get("env") or {}),
            "overlay_files": len(overlay),
            "stock_block_size": c["stock"].get("block_size"),
            "paper_sealed_gain": c.get("paper", {}).get("sealed_final_vs_stock"),
            "paper_final_vs_ar": c.get("paper", {}).get("final_vs_ar"),
        })

    # 「未交付」的检索：对论文声称的组件逐项在仓库文本里找。
    # 注意这里只报告**命中位置**，判定由报告给出——脚本不替人下结论。
    #
    # ⚠️ 排除 vendored 的 `python/sglang/`，但**必须保留**
    #    `settings/<setting>/files/python/sglang/...` —— 那才是 SpecPilot 的补丁本体。
    #    本文件第一版只写 `"python/sglang" not in path`，把 333 个 overlay 文件
    #    连同 W12 / TLV / 树 的实现一起排除了，于是「机制在不在代码里」这个
    #    问题根本没被真正问过。是审计自己的范围错误，不是仓库缺东西。
    def is_vendored(p: Path) -> bool:
        parts = p.relative_to(repo).parts
        # 形如 (python, sglang, ...) 的上游副本 -> vendored
        return (len(parts) >= 2 and parts[0] == "python" and parts[1] == "sglang")

    text_files = [p for p in files
                  if p.suffix.lower() in (".py", ".sh", ".md", ".json", ".txt")
                  and not is_vendored(p)]
    hits: dict[str, list[str]] = {}
    for name, pats in CLAIMED_COMPONENTS.items():
        found = []
        for p in text_files:
            try:
                body = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat in pats:
                if re.search(pat, body, re.I):
                    found.append(f"{p.relative_to(repo).as_posix()}")
                    break
        hits[name] = sorted(set(found))

    # 机制侧的实现：按文件名认定，不靠内容猜测。
    # 这些文件的存在与否，与「论文的机制是否随代码交付」直接相关。
    MECH_PAT = re.compile(
        r"^specpilot_|^dflash_d\d", re.I)
    mech_files = sorted(
        p.relative_to(repo).as_posix()
        for p in files
        if p.suffix.lower() in (".py", ".cu", ".cuh") and MECH_PAT.search(p.name)
    )
    # 每个 setting 的 overlay 里有多少个 specpilot_* 实现文件
    mech_by_setting: dict[str, int] = {}
    for s in settings:
        mech_by_setting[s["setting"]] = sum(
            1 for m in mech_files
            if m.startswith(f"settings/{s['setting']}/files/")
        )

    try:
        head = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%H%x09%ad%x09%s",
                               "--date=iso"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        head = ""

    out = {
        "repo": str(repo),
        "head": head.split("\t"),
        "files_total": len(files),
        "by_extension": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
        "settings": settings,
        "setting_py_files": len(setting_py),
        "setting_py_distinct": len(seen),
        "setting_py_distinct_lines": sum(seen.values()),
        "env_switches_distinct": len(env_names),
        "component_hits": hits,
        "mechanism_files": mech_files,
        "mechanism_files_total": len(mech_files),
        "mechanism_files_by_setting": mech_by_setting,
        "overlay_files_total": sum(1 for p in files
                                   if "files" in p.relative_to(repo).parts),
    }
    (repo / ".." / "DeepResearchRSI" / "research" / "specpilot" / a.out).resolve().write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in out.items() if k != "component_hits"},
                     ensure_ascii=False, indent=2))
    print("\ncomponent_hits:")
    for k, v in hits.items():
        print(f"  {k}: {len(v)} file(s) -> {v[:6]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
