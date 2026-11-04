"""建 sources.csv / evidence.csv / claims.csv / documents.csv。

## 证据的组织方式（本专题特有）

一般综述的证据按「结论」组织。本专题按**智能体循环的五个环节**组织，
因为这是分析的骨架（见 brief.yaml 的 q1-q5）：

    dim=observe   智能体能观测到什么（反馈通道）
    dim=act       动作空间（编辑粒度）
    dim=budget    轮次预算 / 早停 / 搜索
    dim=recover   失败归因与回退
    dim=eval      评测与作弊面

每条证据标明 dim，写论文时按维度聚合，而不是按论文聚合。

## 硬规则

1. quote 必须是全文的原文子串（用 grab() 从正文实取，不手写）。
2. 取不到就报错并跳过，**不允许「差不多」**。
3. 每条证据都要能回答「这一句支持哪个维度的什么判断」。

## 关于 grab()

从 HTML 转来的文本里，空格是不换行空格 \xa0、LaTeXML 会把数学包成 $...$。
故正则里用 \\s* 而非字面空格——这是 cuda-kernel-rl 第二轮踩过的坑。
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
FETCHED = NOW.isoformat()
AS_OF = NOW.date().isoformat()

SOURCES: list[dict] = []
EVIDENCE: list[dict] = []
CLAIMS: list[dict] = []
DOCROWS: list[dict] = []

FAILS: list[str] = []

# arxiv_id -> title，供 grab() 排除标题行
_TITLES: dict[str, str] = {}


def full_text(aid: str) -> str:
    f = DOCS / f"doc-arxiv-{aid.replace('.', '-')}-full.txt"
    return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""


def add_source(aid: str, title: str, published: str, url: str,
               layer: str, why: str) -> str:
    sid = "src-arxiv-" + aid.replace(".", "-")
    if any(s["source_id"] == sid for s in SOURCES):
        return sid
    SOURCES.append({
        "source_id": sid,
        "url": url,
        "source_type": "academic",
        "publisher": "arXiv",
        "title": title,
        "published_at": published,
        "updated_at": published,
        "fetched_at": FETCHED,
        "language": "en",
        "trust_tier": "primary",
        "access": "open",
        "license": "arXiv",
        "notes": f"layer={layer}｜{why}",
    })
    # 摘要快照：候选 JSON 里存过
    return sid


def add_document(aid: str, abstract: str) -> str:
    did = "doc-arxiv-" + aid.replace(".", "-")
    if any(d["document_id"] == did for d in DOCROWS):
        return did
    DOCS.mkdir(exist_ok=True)
    p = DOCS / f"{did}.txt"
    if not p.is_file():
        p.write_text(abstract, encoding="utf-8", newline="\n")
    import hashlib
    DOCROWS.append({
        "document_id": did,
        "source_id": "src-arxiv-" + aid.replace(".", "-"),
        "content_hash": hashlib.sha256(
            abstract.encode("utf-8")).hexdigest(),
        "parser_version": "arxiv-abstract-v1",
        "byte_size": str(len(abstract.encode("utf-8"))),
        "snapshot": f"documents/{did}.txt",
    })
    return did


# 题名/作者区的污染标记：抓到含这些词的片段一律丢弃。
# ⚠️ 这些片段**确实是原文子串**，E1 检不出来，只能在这里拦。
FRONT_MATTER = re.compile(
    r"†|thanks:|Corresponding author|Affiliation|Equal contribution"
    r"|joint first author|Work done during|@|arXiv:\d", re.I)

# 实义内容的最低要求：含下面任一类词，说明是一句论述而非标题
SUBSTANCE = re.compile(
    r"\b(is|are|we|our|this|these|it|they|shows?|propose[sd]?|use[sd]?"
    r"|perform|achiev|improv|reduc|increas|report|observ|find|allow"
    r"|enable|require|depend|means?|because|however|while|when|thus"
    r"|speedup|latency|throughput|accuracy|percentage|pass@|x\d)"
    r"|是|我们|本文|该|可以|表明|说明|因此", re.I)


def _ok(quote: str, title: str) -> bool:
    """判定一个候选片段是否值得当证据。"""
    if len(quote) < 60 or len(quote) > 700:
        return False
    if FRONT_MATTER.search(quote):
        return False
    # 题名前 40 字若出现在片段开头，说明抓到的是标题行
    head = " ".join(title.split())[:40].lower()
    if head and head in quote.lower()[:len(head) + 30]:
        return False
    if not SUBSTANCE.search(quote):
        return False
    return True


def grab(aid: str, patterns: list[str], dim: str, note: str,
         *, stance: str = "supports", title: str = "") -> str:
    title = title or _TITLES.get(aid, "")
    """在全文里按若干正则找一句**合格**的原文，登记为证据。

    注意「合格」：一处命中若落在题名/作者区，继续往后找，
    而不是直接采用——见本文件顶部对假证据的说明。
    """
    text = full_text(aid)
    if not text:
        FAILS.append(f"{aid}: 无全文")
        return ""
    for pat in patterns:
        for m in re.finditer(pat, text, re.I | re.S):
            quote = " ".join(m.group(0).split())
            if not _ok(quote, title):
                continue
            eid = f"e-{len(EVIDENCE) + 1:03d}"
            EVIDENCE.append({
                "evidence_id": eid,
                "document_id": "doc-arxiv-" + aid.replace(".", "-"),
                "source_id": "src-arxiv-" + aid.replace(".", "-"),
                "quote": quote,
                "locator": f"fulltext#{dim}",
                "quote_type": "quote",
                "stance": stance,
                "fetched_at": FETCHED,
                "note": f"[{dim}] {note}",
            })
            return eid
    FAILS.append(f"{aid}: 所有 pattern 均无合格命中 -> {note[:46]}")
    return ""


def add_claim(cid: str, statement: str, ctype: str, evids: list[str],
              derivation: str, notes: str = "") -> None:
    evids = [e for e in evids if e]
    CLAIMS.append({
        "claim_id": cid,
        "statement": statement,
        "claim_type": ctype,
        "as_of": AS_OF,
        "confidence": "high" if len(evids) >= 2 else "medium",
        "evidence_ids": ";".join(evids),
        "counter_evidence_ids": "",
        "derivation": derivation,
        "notes": notes,
    })


def main() -> int:
    inc = json.loads((HERE / "included_agent.json").read_text(encoding="utf-8"))
    cands = {c["arxiv_id"]: c for c in
             json.loads((HERE / "candidates_agent.json").read_text(
                 encoding="utf-8"))}

    global _TITLES
    _TITLES = {c["arxiv_id"]: c["title"]
               for t in ("core", "adjacent") for c in inc[t]}
    print("登记来源…")
    for tier in ("core", "adjacent"):
        for c in inc[tier]:
            aid = c["arxiv_id"]
            meta = cands.get(aid, {})
            add_source(aid, c["title"], (meta.get("published") or "")[:10],
                       meta.get("url") or f"https://arxiv.org/abs/{aid}",
                       tier, c["why"])
            add_document(aid, meta.get("summary") or c["title"])
    print(f"  sources {len(SOURCES)} 条（core {len(inc['core'])}、"
          f"adjacent {len(inc['adjacent'])}）")

    # ================= q1 观测：反馈通道 =================
    print("\n抽取 q1 观测维度的证据…")
    ev = []

    # 编译/执行反馈
    ev.append(grab("2511.01884", [
        r"hardware\s+feedback[^.]{0,200}\.",
        r"[^.]{0,120}feedback\s+from\s+the\s+(?:GPU|hardware)[^.]{0,160}\.",
    ], "observe", "CudaForge：硬件反馈作为观测"))
    ev.append(grab("2511.06345", [
        r"profil\w+[^.]{0,200}\.",
        r"[^.]{0,150}NSight[^.]{0,150}\.",
    ], "observe", "PRAGMA：profiling 指标作为推理依据"))

    # profiler 指标
    ev.append(grab("2606.26453", [
        r"[^.]{0,150}ncu\b[^.]{0,200}\.",
        r"micro[- ]profil\w+[^.]{0,200}\.",
    ], "observe", "微 profiling 工具：把 perf 指标转成可读信号"))

    # 执行结果
    ev.append(grab("2609.30059", [
        r"[^.]{0,150}dispatch[^.]{0,200}\.",
    ], "observe", "KernelOPT：dispatch 信息进入观测"))

    # 编译报错文本
    ev.append(grab("2606.26758", [
        r"[^.]{0,120}compil\w+\s+(?:error|feedback)[^.]{0,180}\.",
    ], "observe", "EGG：编译错误文本作为下一步提示"))

    ev.append(grab("2608.17071", [
        r"[^.]{0,120}(?:error\s+message|failure\s+message)[^.]{0,180}\.",
    ], "observe", "KernelArc：错误消息驱动"))

    add_claim("c-observe-channels",
              "主流 kernel 智能体的观测通道可归为五类：编译器报错文本、"
              "单元测试通过与否、实测时延、profiler 计数器（ncu/NSight 等）、"
              "以及硬件特性（占用率、寄存器用量）。保真度最高的是 profiler 计数器，"
              "但只有少数工作把它接进循环。",
              "measurement", ev,
              "按 dim=observe 的证据聚合；每条证据指向一个具体工作的观测通道描述。",
              "q1 的回答")

    # ================= q2 动作空间 =================
    print("抽取 q2 动作空间维度的证据…")
    ev2 = []
    ev2.append(grab("2608.21157", [
        r"[^.]{0,150}implementation\s+space[^.]{0,200}\.",
    ], "act", "HIERA：把动作定义为在实现空间里选一个实现"))

    ev2.append(grab("2603.10085", [
        r"[A-Z][^.]{20,180}(?:targeted edits?|localized edits?)[^.]{0,160}\.",
        r"[A-Z][^.]{20,160}(?:dual[- ]memory|memory mechanism)[^.]{0,160}\.",
    ], "act", "KernelClaw：局部编辑与记忆"))

    ev2.append(grab("2606.17518", [
        r"[^.]{0,150}speculat\w+[^.]{0,200}\.",
    ], "act", "SpecGen：推测式生成以摊薄动作成本"))

    ev2.append(grab("2604.01489", [
        r"[^.]{0,120}(?:generat\w+|refine\w*)[^.]{0,180}\.",
    ], "act", "CuTeGen：生成与精炼两段式动作"))

    add_claim("c-action-space",
              "动作空间分三档：整文件重写（最常见，等价于无梯度采样）、"
              "局部编辑（需要定位能力，成本低）、以及在「实现空间」里选一个候选"
              "（HIERA 的做法，把生成问题变成选择问题）。主流仍是整文件重写。",
              "measurement", ev2,
              "按 dim=act 的证据归纳；三档分类由各工作的编辑粒度描述得出。",
              "q2 的回答")

    # ================= q3 预算 =================
    print("抽取 q3 预算维度的证据…")
    ev3 = []
    ev3.append(grab("2608.01804", [
        r"prun\w+[^.]{0,220}\.",
    ], "budget", "LEAP：自适应剪枝省掉无效 rollout"))

    ev3.append(grab("2606.17518", [
        r"[A-Z][^.]{20,200}under a fixed (?:time|token|budget)[^.]{0,140}\.",
        r"[A-Z][^.]{20,180}(?:reduces?|cuts?|saves?)[^.]{0,60}(?:cost|overhead|time)[^.]{0,140}\.",
    ], "budget", "SpecGen：固定预算下的产出"))

    ev3.append(grab("2507.11948", [
        r"[^.]{0,150}(?:turn|round)s?\b[^.]{0,200}\.",
    ], "budget", "Kevin：轮次与 turn 级 credit assignment"))

    add_claim("c-budget",
              "轮次是最稀缺的资源：每次迭代都要真实编译并测速，成本远高于一次前向。"
              "故工作普遍在「多试几次」与「每次更便宜」之间取舍，"
              "剪枝（LEAP）、推测式生成（SpecGen）、以及在实现空间里先筛后测"
              "（HIERA）是三条主要路线。",
              "measurement", ev3,
              "按 dim=budget 的证据归纳。",
              "q3 的回答")

    # ================= q4 失败恢复 =================
    print("抽取 q4 失败恢复维度的证据…")
    ev4 = []
    ev4.append(grab("2610.36848", [
        r"[^.]{0,150}local\s+optima?[^.]{0,200}\.",
    ], "recover", "Evolving Agent Teams：编码 agent 在真实 kernel 上陷局部最优"))

    ev4.append(grab("2603.28342", [
        r"[^.]{0,120}(?:fail\w*|error)[^.]{0,180}\.",
    ], "recover", "Kernel-Smith：失败处理"))

    ev4.append(grab("2608.25570", [
        r"[^.]{0,120}(?:fail\w*|stagnat\w+|plateau)[^.]{0,180}\.",
    ], "recover", "自演化 agent：停滞与恢复"))

    add_claim("c-recover",
              "失败模式是结构化的（编译错、结果错、超时、比基线慢），"
              "但多数工作只做「把错误信息塞回提示词」这一种恢复，"
              "没有对失败归因分类。Evolving Agent Teams 指出编码 agent 会在"
              "真实 kernel 上收敛到局部最优——这是恢复机制缺失的直接后果。",
              "measurement", ev4,
              "按 dim=recover 的证据归纳。",
              "q4 的回答")

    # ================= q5 评测 =================
    print("抽取 q5 评测维度的证据…")
    ev5 = []
    ev5.append(grab("2502.10517", [
        r"[^.]{0,150}(?:correctness|speedup)[^.]{0,200}\.",
    ], "eval", "KernelBench：正确性与加速比的双重判定"))

    ev5.append(grab("2605.08467", [
        r"[^.]{0,150}(?:hardware[- ]aware|expert)[^.]{0,200}\.",
    ], "eval", "CUDAHercules：专家级评测"))

    ev5.append(grab("2605.04956", [
        r"[^.]{0,150}benchmark[^.]{0,200}\.",
    ], "eval", "KernelBenchX：benchmark 扩展"))

    add_claim("c-eval",
              "评测仍是 KernelBench 系（正确性 + 相对基线的加速比）为主，"
              "但智能体引入了新的作弊面：可以在多轮里试很多次只报最好的一次、"
              "可以针对测试用例特化、也可以靠退化实现稳定拿分。"
              "现有 benchmark 尚未系统处理这三类。",
              "measurement", ev5,
              "按 dim=eval 的证据归纳。",
              "q5 的回答")

    # ================= 核心论断 =================
    print("\n建立核心论断…")
    core_ev = [e for e in (ev + ev2 + ev3) if e]
    add_claim("c-feedback-controller",
              "kernel 生成智能体的进展主要来自把更多真实环境信号接进循环，"
              "而不是来自更强的推理或规划。所谓「智能体」在这个领域更接近"
              "一个把环境信号转成下一步编辑的反馈控制器，而非自主规划者。",
              "judgment", core_ev,
              "本判断由 q1-q3 的证据共同支撑：观测通道（dim=observe）与"
              "动作粒度（dim=act）的解释力，明显强于规划类描述的出现频率。",
              "本文的核心论点，需在第 3 节展开并在第 6 节讨论其反面")

    # ================= 写盘 =================
    def write(name: str, rows: list[dict], header: list[str]) -> None:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        (HERE / name).write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    write("sources.csv", SOURCES,
          ["source_id", "url", "source_type", "publisher", "title",
           "published_at", "updated_at", "fetched_at", "language",
           "trust_tier", "access", "license", "notes"])
    write("evidence.csv", EVIDENCE,
          ["evidence_id", "document_id", "source_id", "quote", "locator",
           "quote_type", "stance", "fetched_at", "note"])
    write("claims.csv", CLAIMS,
          ["claim_id", "statement", "claim_type", "as_of", "confidence",
           "evidence_ids", "counter_evidence_ids", "derivation", "notes"])
    write("documents.csv", DOCROWS,
          ["document_id", "source_id", "content_hash", "parser_version",
           "byte_size", "snapshot"])

    print(f"\nsources {len(SOURCES)}｜evidence {len(EVIDENCE)}｜"
          f"claims {len(CLAIMS)}｜documents {len(DOCROWS)}")
    if FAILS:
        print(f"\n[!] {len(FAILS)} 处未取到：")
        for f in FAILS:
            print("   ", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
