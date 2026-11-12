"""用 arXiv API 做真正的检索式搜索（而不是只扫站内已有快照）。

## 为什么要有这个脚本

第 1 轮的失误：新归档的候选集是「在站内 5 个归档的 documents/ 里 grep 出来的」。
那不是检索，那是**让旧归档定义领域边界**——旧归档没收录的工作，
新归档永远发现不了。KOPE（2608.25570）明明已经躺在 kernel-agent/documents/ 里，
我打印过它的摘要却没纳入，就是这个方法的直接后果。

## 第 2 轮修的第二个 bug（更隐蔽）

初版用 `sortBy=submittedDate + max_results=60`：每个式子只取**最新** 60 篇。
后果是老的基础工作被系统性截断——DGM（2025-05）、AlphaEvolve（2025-05）、
AutoKernel（2026-03）全部落在窗口外，而它们恰好是这一族的地基。
DGM 与 AutoKernel 当时就在本站其它归档里，却因为按日期排序而搜不到，
这比「没检索」更危险：它让检索看起来跑过了、还跑了 8 个式子。

故现行做法：
  1. **按相关度**排序（arXiv 默认），不按日期——覆盖面优先于新鲜度
  2. **同时发日期序**作为第二遍，捕捉相关度排序漏掉的新工作
  3. 每个式子取 max_results=200，两遍并集
  4. 末尾附「已知工作覆盖自检」：把必须命中的 10 篇写死，任何一篇没命中就报警

用法：
    python research/rsi-infra-feedback/fetch_candidates.py
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "candidates.json"

API = "http://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}

# 十二组检索式。每组的意图写在值里，便于日后判断「漏了哪一类」。
#
# 第 3 轮补的三组（program-evolve / evolution-search / kernel-bench）：
#   前三版式子全部围绕 "agent + serving/kernel + feedback" 的字面组合，
#   于是**演化搜索**这一支被整体漏掉——DGM、AlphaEvolve、AutoKernel 都不说
#   自己是 "self-evolving agent"，它们说 "evolutionary program search"、
#   "archive"、"open-ended"。词面不重叠，检索式再精确也捞不到。
#   教训：漏的不是「某个工作」，漏的是**一整类措辞**。
QUERIES = {
    "system-evolve": 'all:"inference system" AND all:"self-evolv"',
    "engine-agent": 'abs:"inference engine" AND abs:"agent"',
    "training-infra": 'abs:"training infrastructure" AND abs:"agent"',
    "agent-evolve": 'all:"self-evolving" AND all:"agent"',
    "rsi": 'all:"recursive self-improvement"',
    "experience-memory": 'all:"experience" AND all:"kernel"',
    "feedback-kernel": 'abs:"feedback" AND abs:"kernel" AND abs:"performance"',
    "serving-bench": 'all:"benchmark" AND all:"inference" AND all:"agent"',
    "serving-opt": 'abs:"serving" AND abs:"optimization" AND abs:"LLM"',
    "meta-evolve": 'all:"meta-skill" OR all:"harness" AND all:"evolv"',
    # --- 第 3 轮新增：覆盖「演化搜索」措辞 ---
    "program-evolve": 'all:"evolutionary" AND all:"program" AND all:"LLM"',
    "open-ended": 'all:"open-ended" AND all:"agent" AND all:"code"',
    "kernel-agent-gen": 'all:"kernel" AND all:"optimization" AND all:"agent"',
    # --- 第 4 轮新增：AlphaEvolve 的自我描述是 "algorithmic discovery" ---
    # 探针实测：'evolutionary search'+LLM、'code evolution'、'evaluator'+program
    # 都 miss，唯一稳定命中的是 all:"algorithmic discovery"（86 条）。
    # 它连 "agent" 都不说，说 "discovery"——这是又一处措辞鸿沟。
    "algorithmic-discovery": 'all:"algorithmic discovery"',
}

# 必检命中集。这些先按 id 精确取（见 IDS），再与检索式结果取并集——
# 靠 id 兜底，才不会因为措辞差异让地基工作掉出候选集。
MUST_HIT = {
    "2610.04646": "SEIS",
    "2611.11558": "InfraRSI",
    "2608.25570": "KOPE",
    "2610.36848": "Evolving Agent Teams",
    "2609.26777": "SWE-Serve",
    "2607.05297": "MetaSkill-Evolve",
    "2603.21331": "AutoKernel",
    "2505.22954": "Darwin Gödel Machine",
    "2506.13131": "AlphaEvolve",
    "2607.20468": "InferenceBench",
}

MAX_PER = 200


def fetch(q: str, sort: str, maxr: int = MAX_PER) -> list[dict]:
    params = {
        "search_query": q,
        "start": 0,
        "max_results": maxr,
        "sortBy": sort,
        "sortOrder": "descending",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "drs-inventory/1.2"})
    with urllib.request.urlopen(req, timeout=90) as r:
        root = ET.fromstring(r.read())
    out = []
    for e in root.findall("a:entry", NS):
        eid = e.findtext("a:id", "", NS)
        out.append({
            "aid": eid.rsplit("/abs/", 1)[-1].split("v")[0],
            "title": " ".join((e.findtext("a:title", "", NS) or "").split()),
            "published": (e.findtext("a:published", "", NS) or "")[:10],
            "summary": " ".join((e.findtext("a:summary", "", NS) or "").split()),
            "cats": [c.get("term") for c in e.findall("a:category", NS)],
        })
    return out


def fetch_by_ids(ids: list[str]) -> list[dict]:
    """按 id 精确取。用于必检集兜底：绕开一切措辞差异。"""
    params = {"id_list": ",".join(ids), "max_results": len(ids)}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "drs-inventory/1.2"})
    with urllib.request.urlopen(req, timeout=90) as r:
        root = ET.fromstring(r.read())
    out = []
    for e in root.findall("a:entry", NS):
        eid = e.findtext("a:id", "", NS)
        out.append({
            "aid": eid.rsplit("/abs/", 1)[-1].split("v")[0],
            "title": " ".join((e.findtext("a:title", "", NS) or "").split()),
            "published": (e.findtext("a:published", "", NS) or "")[:10],
            "summary": " ".join((e.findtext("a:summary", "", NS) or "").split()),
            "cats": [c.get("term") for c in e.findall("a:category", NS)],
        })
    return out


def main() -> int:
    seen: dict[str, dict] = {}
    # 两遍：相关度 + 日期。相关度保覆盖，日期保新鲜，并集。
    for sort in ("relevance", "submittedDate"):
        for name, q in QUERIES.items():
            try:
                got = fetch(q, sort)
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] {name}/{sort}: {exc}")
                time.sleep(5)
                continue
            new = 0
            for it in got:
                base = it["aid"]
                if base not in seen:
                    it["queries"] = [f"{name}:{sort}"]
                    seen[base] = it
                    new += 1
                else:
                    seen[base]["queries"].append(f"{name}:{sort}")
            print(f"{sort[:9]:9} {name:16} {len(got):3} 条，新增 {new}")
            time.sleep(3)  # arXiv 要求间隔

    # 必检集按 id 兜底并入（billable 一次请求）
    try:
        pinned = fetch_by_ids(list(MUST_HIT))
        add = 0
        for it in pinned:
            if it["aid"] not in seen:
                it["queries"] = ["pinned:id"]
                seen[it["aid"]] = it
                add += 1
        print(f"\n必检集按 id 取回 {len(pinned)} 篇，补入候选 {add} 篇")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] id_list 兜底失败：{exc}")

    ordered = sorted(seen.values(), key=lambda x: x["published"], reverse=True)
    OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"去重合计 {len(ordered)} 篇 -> {OUT.name}")

    # ---- 覆盖自检 ----
    print("\n必检命中自检：")
    miss = 0
    for aid, label in MUST_HIT.items():
        ok = aid in seen
        print(f"  {'[OK ]' if ok else '[MISS]'} {aid}  {label}")
        if not ok:
            miss += 1
    if miss:
        print(f"\n⚠️  {miss} 篇必检工作未命中——检索式仍需扩，不要就此定稿")
        return 1
    print("\n全部必检工作已命中")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
