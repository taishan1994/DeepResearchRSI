"""建 SpecPilot 留档：sources / documents / evidence / claims 四张表。

## 硬规则（与 kernel-agent / pd-disagg 一致）

1. `quote` 必须是快照的原文子串，由 `grab()` 从快照实取，**不手写**。
2. 取不到就记 FAILS 并跳过，不允许「差不多」。
3. 每条证据带 `dim` 标注，说明它在五维里支持哪一维。

## 为什么用「首尾字面锚点」而不是正则

论文快照是 LaTeXML 转的：`4.46×` 渲染成 `4.46 × \\times`，`τ(N)` 渲染成
`τ ( N )`，`Figure 3` 中间是 `\\xa0`，`'` 是 `’`。第一版用正则 + `\\s*` 兜，
55 条锚点里挂了 25 条——**每一条失败都要回原文猜措辞**，代价极高。

改用字面锚点后：给一句原文的开头与结尾（可以带空格、可以带弯引号），
在「去空白」的正文上定位，再映射回原始偏移取区间。好处是

  * 不用记正则元字符（`(`、`{`、`[` 在原文里到处都是）；
  * 不用猜空白形态（`\\xa0`/`\\u2009`/换行都被去掉）；
  * 未命中时能直接报出「锚点附近实际是什么」，一轮就能改完。

取出的 quote 仍是原文的一段**连续区间**，不是拼接、不是改写。
"""

from __future__ import annotations

import csv
import hashlib
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

PAPER = "doc-arxiv-2611-02501"
PAPER_FULL = f"{PAPER}-full.txt"
PAGE = "specpilot-project-page.txt"
RREADME = "specpilot-repo-readme.txt"
RCONFIG = "specpilot-setting-h100-c1-dflash2-config.txt"

S_PAPER = "src-arxiv-2611-02501"
S_CODE = "src-specpilot-github"
S_PAGE = "src-specpilot-project-page"

SOURCES: list[dict] = []
DOCROWS: list[dict] = []
EVIDENCE: list[dict] = []
CLAIMS: list[dict] = []
FAILS: list[str] = []

_cache: dict[str, str] = {}
_match: dict[str, tuple[str, list[int]]] = {}

# 匹配空间里的同形异码归一：只影响**检索**，不影响取出来的 quote。
# 注意校验器的 norm() **不做**这层映射（只折叠空白），
# 故 quote 必须保留原文的 ’ “ ” —— 一旦把它们改成 ASCII，
# E1 就会判为「不是原文子串」。这正是本文件第一版踩的坑。
_LOOKALIKE = {
    "\u2019": "'", "\u2018": "'",
    "\u201c": '"', "\u201d": '"',
    "\u200b": None, "\u2061": None, "\ufeff": None,
}


def raw(name: str) -> str:
    """快照原文（逐字节读入、不做任何改写）。"""
    if name not in _cache:
        p = DOCS / name
        _cache[name] = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    return _cache[name]


def body(name: str) -> str:
    """校验器会看到的同一份文本，仅把空白折叠成单空格（与 norm() 一致）。"""
    return re.sub(r"\s+", " ", raw(name))


def _matchspace(name: str) -> tuple[str, list[int]]:
    """构造「去空白 + 同形归一」的检索串，并记录每个字符在原文中的下标。

    为什么要索引映射：校验器要求 quote 是**原文子串**，
    所以检索可以随便归一，但取出来的必须是原文那一段。
    """
    if name not in _match:
        text, pos = [], []
        for i, ch in enumerate(raw(name)):
            if ch.isspace():
                continue
            mapped = _LOOKALIKE.get(ch, ch)
            if mapped is None:          # 零宽字符：既不可见也不该参与匹配
                continue
            text.append(mapped)
            pos.append(i)
        _match[name] = ("".join(text), pos)
    return _match[name]


def _lit(s: str) -> str:
    out = []
    for ch in s:
        if ch.isspace():
            continue
        mapped = _LOOKALIKE.get(ch, ch)
        if mapped is not None:
            out.append(mapped)
    return "".join(out)


def grab(doc: str, start: str, end: str | None = None, *, note: str = "") -> str | None:
    """按首尾字面锚点从快照实取一段原文。

    `end` 省略时只取 `start` 本身（用于取一行 JSON、一个函数签名）。
    未命中记 FAILS 并返回 None——不抛异常，因为一次构建要跑几十条，
    逐条中断会把「改一轮」变成「改几十轮」。
    """
    text, pos = _matchspace(doc)
    s = _lit(start)
    i = text.find(s)
    if i < 0:
        FAILS.append(f"{doc}\n     起点未命中：{start!r}")
        return None
    j = i + len(s)
    if end:
        e = _lit(end)
        k = text.find(e, j)
        if k < 0:
            FAILS.append(f"{doc}\n     起点 OK（{start[:40]!r}），终点未命中：{end!r}\n"
                         f"     起点后 200 字：{text[i:i + 200]}")
            return None
        j = k + len(e)
    a = pos[i]
    b = pos[j - 1] + 1
    return re.sub(r"\s+", " ", raw(doc)[a:b]).strip()


def add_source(sid: str, url: str, *, stype: str, publisher: str, title: str,
               published: str, tier: str, license_: str, notes: str) -> None:
    if any(s["source_id"] == sid for s in SOURCES):
        return
    SOURCES.append({
        "source_id": sid, "url": url, "source_type": stype, "publisher": publisher,
        "title": title, "published_at": published, "updated_at": published,
        "fetched_at": FETCHED, "language": "en", "trust_tier": tier,
        "access": "open", "license": license_, "notes": notes,
    })


def add_doc(did: str, sid: str, snapshot: str, parser: str) -> None:
    if any(d["document_id"] == did for d in DOCROWS):
        return
    text = body(snapshot)
    DOCROWS.append({
        "document_id": did, "source_id": sid,
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),        "parser_version": parser,
        "byte_size": str(len(text.encode("utf-8"))),
        "snapshot": f"documents/{snapshot}",
    })


def ev(eid: str, did: str, sid: str, quote: str | None, locator: str, dim: str,
       stance: str = "supports", note: str = "") -> None:
    if quote is None:
        return
    EVIDENCE.append({
        "evidence_id": eid, "document_id": did, "source_id": sid, "quote": quote,
        "locator": locator, "quote_type": "verbatim", "stance": stance,
        "fetched_at": FETCHED,
        "note": f"dim={dim}｜{note}" if note else f"dim={dim}",
    })


def claim(cid: str, statement: str, *, ctype: str, confidence: str, eids: list[str],
          counters: list[str] | None = None, derivation: str = "",
          facets: dict | None = None, notes: str = "") -> None:
    CLAIMS.append({
        "claim_id": cid, "statement": statement, "claim_type": ctype, "as_of": AS_OF,
        "confidence": confidence, "evidence_ids": ";".join(eids),
        "counter_evidence_ids": ";".join(counters or []),
        "derivation": derivation,
        "facets": json.dumps(facets, ensure_ascii=False) if facets else "",
        "notes": notes,
    })


# ------------------------------------------------------------------ sources
def build_sources() -> None:
    add_source(
        S_PAPER, "https://arxiv.org/abs/2611.02501",
        stype="academic", publisher="arXiv",
        title="SpecPilot: Autonomous Algorithm Discovery and Systems Optimization "
              "for Speculative Decoding",
        published="2026-11-02", tier="primary", license_="arXiv non-exclusive",
        notes="layer=paper｜v1，10 位作者（UC Berkeley / Princeton / Stanford / NVIDIA）；"
              "机制与数字的原始出处",
    )
    add_source(
        S_CODE, "https://github.com/StargazerX0/SpecPilot",
        stype="official", publisher="GitHub (StargazerX0)",
        title="SpecPilot: engines, configs, model links and scripts for six settings",
        published="2026-11-02", tier="primary", license_="Apache-2.0",
        notes="layer=code｜commit 78c42af；交付 6 个 setting 的引擎（含 183 个 specpilot_* 机制实现）"
              "与评测脚本；不含论文描述的控制器、记忆库与 token forcing 判定（见 c-027/c-028）",
    )
    add_source(
        S_PAGE, "https://stargazerx0.github.io/specpilot-project-page/",
        stype="official", publisher="SpecPilot authors", title="SpecPilot project page",
        published="2026-11-02", tier="secondary", license_="project page",
        notes="layer=page｜作者自述的浓缩版；转述论文而无新观测，故按定义是 secondary",
    )
    add_doc(PAPER, S_PAPER, PAPER_FULL, "arxiv-html-v1")
    for did, snap in [
        ("doc-specpilot-repo-readme", RREADME),
        ("doc-specpilot-setting-h100-c1-dflash2-readme",
         "specpilot-setting-h100-c1-dflash2-readme.txt"),
        ("doc-specpilot-setting-h100-c1-dflash2-config", RCONFIG),
        ("doc-specpilot-dflash-lab-readme", "specpilot-dflash-lab-readme.txt"),
        ("doc-specpilot-compare-py", "specpilot-compare-py.txt"),
        ("doc-specpilot-bench-sh", "specpilot-bench-sh.txt"),
        ("doc-specpilot-cudaslot-py", "specpilot-cudaslot-py.txt"),
        ("doc-specpilot-build-engine-py", "specpilot-build-engine-py.txt"),
        ("doc-specpilot-techniques-budget-py", "specpilot-techniques-budget-py.txt"),
        ("doc-specpilot-experiments-trace-py", "specpilot-experiments-trace-py.txt"),
        ("doc-specpilot-dangling-refs", "specpilot-dangling-refs.txt"),
        # 机制实现的源码快照：这些是「论文的机制是否随代码交付」的直接证据。
        # 取自 settings/<setting>/files/python/sglang/... —— overlay 本体。
        ("doc-specpilot-d5-w12-py", "specpilot-d5-w12-py.txt"),
        ("doc-specpilot-d8-tlv-py", "specpilot-d8-tlv-py.txt"),
        ("doc-specpilot-tree-gdn-py", "specpilot-tree-gdn-py.txt"),
        ("doc-specpilot-d7-chain-py", "specpilot-d7-chain-py.txt"),
    ]:
        add_doc(did, S_CODE, snap, "raw-copy-v1")
    add_doc("doc-specpilot-project-page", S_PAGE, PAGE, "html-main-v1")


# ------------------------------------------------------------------ evidence
def build_evidence() -> None:
    P = PAPER_FULL

    # ---- 循环与判定 ----
    ev("e-001", PAPER, S_PAPER,
       grab(P, "Without training or quality loss", "10.87"),
       "§Abstract", "loop",
       note="摘要同时给出 stock 4.46× 与 SpecPilot 10.87×（单请求、RTX PRO 6000）")
    ev("e-002", PAPER, S_PAPER,
       grab(P, "we present SpecPilot, an autonomous agentic loop", "for each deployment."),
       "§Abstract", "loop",
       note="循环做的三件事：成本模型定位缺口、并行 agent 探索、结构化记忆迁移")
    ev("e-003", PAPER, S_PAPER,
       grab(P, "SpecPilot operates in rounds", "so the loop is recursive."),
       "§3", "loop",
       note="五阶段：Phase 0 量缺口，1–3 让 agent 建并计时，Phase 4 在未见请求上封 sealed final")
    ev("e-009", PAPER, S_PAPER,
       grab(P, "separates the agents that modify the system", "current best's."),
       "§3.2", "judge",
       note="权限边界（agent 只能调控制器、不能改）+ 晋级门槛（95% 下界 > 1% + 2×噪声，输出不同则 ~3%）")
    ev("e-010", PAPER, S_PAPER,
       grab(P, "It builds a new algorithm only if the headroom", "10 GPU-minutes."),
       "§3.2 Phase 1", "judge",
       note="方向关闭规则：先量已实现的机制再关；除非要花超 10 GPU-分钟")
    ev("e-011", PAPER, S_PAPER,
       grab(P, "A final that fails either check is rejected."),
       "§3.2 Phase 4", "judge",
       note="sealed final 的否决权：token forcing 不过即整轮作废")
    ev("e-046", PAPER, S_PAPER,
       grab(P, "Byte arithmetic put its headroom at 25%", "revised kernel gave 1.063"),
       "§3.2 worked example", "judge",
       note="单条改动的量级：headroom 25%，首次晋级 1.076×，改内核后 1.063×")
    ev("e-048", "doc-specpilot-project-page", S_PAGE,
       grab(PAGE, "A master agent plans directions", "for one request on H100."),
       "project page / Agents propose", "judge",
       note="项目页对晋级规则的复述，与论文 §3.2 逐项一致（交叉核对用）")

    # ---- 成本模型 ----
    ev("e-004", PAPER, S_PAPER,
       grab(P, "S(N)=", "one AR step on the same engine."),
       "§3.1 Eq.(3)", "costmodel",
       note="速度比 S(N)=τ(N)/c(N)；c 为一步相对一次 AR 步的耗时")
    ev("e-005", PAPER, S_PAPER,
       grab(P, "Unused candidates", "8.20 at 16"),
       "§3.1", "costmodel",
       note="未用候选：stock 链 4.25 tokens/step，oracle 在 16 位置达 8.20")
    ev("e-006", PAPER, S_PAPER,
       grab(P, "With one request, reading the target", "23.61"),
       "§3.1", "costmodel",
       note="单请求：GEMM 从 1 行 17.88ms 到 64 行 18.58ms；权重读占 23.61ms 步时的 80%")
    ev("e-007", PAPER, S_PAPER,
       grab(P, "Ceilings. To rank these effects", "90% of peak bandwidth."),
       "§3.1", "costmodel",
       note="ceiling 定义：一次 draft、一次 exact pass、每类 kernel 跑到 byte floor")
    ev("e-008", PAPER, S_PAPER,
       grab(P, "The ceiling factors as", "at the best node budget."),
       "§3.1 Eq.(4)", "costmodel",
       note="三分之积：τ_best/τ（树）· T_prof/T_floor（kernel）· T_step/T_prof（profile 外）")

    # ---- 无损与 token forcing ----
    ev("e-012", PAPER, S_PAPER,
       grab(P, "teacher-forced scorer feeds", "multiple of 1/8."),
       "§3.3", "lossless",
       note="token forcing 构造：stock 引擎 + FP32 LM head 重打分；δ 由 stock 首次偏离 AR 的最大 margin 向上取整")
    ev("e-013", PAPER, S_PAPER,
       grab(P, "The rate rule rejects it", "changes with the prefill length."),
       "§3.3", "lossless",
       note="两条拒绝规则（rate rule 0.5 点 / event rule 2δ）+ 三种可解释事件")
    ev("e-014", PAPER, S_PAPER,
       grab(P, "A system is lossless if every accepted token", "against stock."),
       "§2.1", "lossless",
       note="无损定义（落到精确 pass 的 argmax）+ 为什么「逐位相同」会误杀、「准确率」会漏放")
    ev("e-015", PAPER, S_PAPER,
       grab(P, "Token forcing accepts both lossless systems", "left unexplained."),
       "§6.2", "lossless",
       note="注入故障实验：0.73%/0.52%（无损）vs 2.0%/2.4%（故障），192/191 条大 margin 事件未解释")

    # ---- 记忆 ----
    ev("e-016", PAPER, S_PAPER,
       grab(P, "each promoted mechanism becomes one memory entry", "specific to sm_120"),
       "§3.4", "memory",
       note="条目 = 代码增量 + 变体注册 + 正确性契约 + 证据/边界；140 条，最多 12 个前置")
    ev("e-035", PAPER, S_PAPER,
       grab(P, "Porting the H100 tree and W12 entries", "(§ 3.1)."),
       "§5.3", "memory",
       note="新平台：移植两条条目即得 sealed 1.92×；TLV+split-KV 推到 2.44×，超过它自己的 2.12× ceiling")
    ev("e-036", PAPER, S_PAPER,
       grab(P, "EAGLE-3 on Gemma-4-12B reimplemented two designs from memory", "to 3.11"),
       "§5.3", "memory",
       note="顺序 drafter 也吃到记忆迁移：首轮 2.67× → 最终 3.11×")

    # ---- 机制 ----
    ev("e-017", PAPER, S_PAPER,
       grab(P, "For each channel", "bit for bit."),
       "§4.1", "mech",
       note="W12 编码：16-binade 窗口 + sign/4-bit 指数偏移/7-bit 尾数；12.01–12.02 bits/weight；44.67→33.58 GB")
    ev("e-018", PAPER, S_PAPER,
       grab(P, "Each 12 KB record", "deterministic."),
       "§4.1", "mech",
       note="12KB 记录 / 128×64 tile；stream-K 固定归约顺序 → 确定性")
    ev("e-019", PAPER, S_PAPER,
       grab(P, "An INT8 copy with a per-row", "LM head there."),
       "§4.1", "mech",
       note="certified LM head：878→482μs（H100）；PRO 6000 上 2598 vs 1750μs 反而慢，故那里改用 W12")
    ev("e-020", PAPER, S_PAPER,
       grab(P, "Round one built best-first trees", "a wide tree"),
       "§4.2", "mech",
       note="best-first 树：按父节点给的 log-softmax 打分（非 DDTree 边缘分），32 节点、深 15、16 位置 draft")
    ev("e-021", PAPER, S_PAPER,
       grab(P, "recomputes the recurrent state along each root path", "exact pass stays exact."),
       "§4.2", "mech",
       note="混合目标：不存每节点快照，沿根路径重算；WY kernel 用三个 BF16 部分表示全部 24 位有效位")
    ev("e-022", PAPER, S_PAPER,
       grab(P, "Each TLV cycle has two passes", "longest matching path."),
       "§4.3", "mech",
       note="TLV：Q pass 只提议不提交（不动 KV 与递归状态）；一次 exact pass 验 C 与挂在其下的子树")
    ev("e-023", PAPER, S_PAPER,
       grab(P, "TLV is lossless because only the exact pass accepts tokens",
            "including both drafting steps."),
       "§4.3", "mech",
       note="无损性来自「只有 exact pass 提交」；TLV 下 τ 与 T_step 的定义同时改变")
    ev("e-024", PAPER, S_PAPER,
       grab(P, "Each view agrees with the exact pass", "raised speed when it was promoted."),
       "§4.3 / App. E", "mech",
       note="Q pass 与 exact pass 的 top-1 一致率约 98%（表 A5 给嵌套 8-bit 视图 0.983）")
    ev("e-025", PAPER, S_PAPER,
       grab(P, "Shared node budget.", "flat until the next tile."),
       "§4.4", "mech",
       note="批处理：请求共享固定节点预算，靠 best-first 的前缀闭包保证每份仍是合法树")
    ev("e-026", PAPER, S_PAPER,
       grab(P, "Per-request drafter block.", "17 to 24 requests."),
       "§4.4", "mech",
       note="按近期接受率与 draft 置信度在 GPU 上选 16/12/8 位置，把 drafter 压在 256 行内")
    ev("e-027", PAPER, S_PAPER,
       grab(P, "Prompt admission.", "projection and MLP GEMMs."),
       "§4.4", "mech",
       note="prompt 准入：只在调度器本来要压住它时才并流（≤384 token 链 / 128 行段）")

    # ---- 增益与评估 ----
    ev("e-028", PAPER, S_PAPER,
       grab(P, "The system went from stock's 184 to 416", "refining the previous gain."),
       "§6.1", "loop",
       note="三轮 184→270→416 tok/s；每轮瓶颈不同，ceiling 每轮重算故方向随最大因子改")
    ev("e-029", PAPER, S_PAPER,
       grab(P, "Round three: the unit of a step.", "416 tokens/s."),
       "§6.1", "loop",
       note="第三轮：ceiling 自带「一次 draft 配一次 exact pass」的假设，TLV 把这个假设也当成可改对象")
    ev("e-030", PAPER, S_PAPER,
       grab(P, "Single-agent baseline.", "the unit of a step (TLV)."),
       "§6.1", "judge",
       note="单 agent 对照：1.34× vs 2.13×；差别是「有没有 ceiling 排序缺口」")
    ev("e-031", PAPER, S_PAPER,
       grab(P, "On H100, stock DFlash2 drafts its trained block size", "stronger baseline"),
       "§5.1 Baselines", "eval",
       note="基线是逐 GPU 调过的 stock；H100 单请求上 DDTree 树是更强基线（4.82×）")
    ev("e-032", PAPER, S_PAPER,
       grab(P, "gain is the geometric mean of per-request", "on unseen requests."),
       "§5.1 Metrics", "eval",
       note="口径：逐请求速率比的几何均值、等权合并；对 AR 的增益与 sealed 增益差 −2%~+6%")
    ev("e-033", PAPER, S_PAPER,
       grab(P, "With one request, SpecPilot is more than twice as fast as stock",
            "faster than the DDTree baseline."),
       "§5.2", "eval",
       note="单请求：8.86–9.41×（H100）与 10.63–10.87×（PRO 6000）；对 DDTree 基线 1.84×")
    ev("e-034", PAPER, S_PAPER,
       grab(P, "With batching on FP8 Qwen3.8-27B, SpecPilot beats stock at every batch size",
            "stock trails AR."),
       "§5.2", "eval",
       note="批处理：对 stock 1.85×/1.94×；对 AR 3.90×/3.93×；stock 弱的目标获益更大（2.39×/3.11×）")
    ev("e-037", PAPER, S_PAPER,
       grab(P, "Mechanisms that spend more verify work per exact pass", "to break even."),
       "§6.5", "boundary",
       note="反号：批处理下 24 节点树 −14.9%、24 位置 block −9.9%、TLV −13%")
    ev("e-038", PAPER, S_PAPER,
       grab(P, "Mechanisms that choose rows selectively", "admitting every short prompt lost."),
       "§6.5", "boundary",
       note="正向：共享节点预算多收 6–14%、per-request block 1.040×、仅等待中的 prompt 3.5%（未配对）")
    ev("e-049", "doc-specpilot-project-page", S_PAGE,
       grab(PAGE, "With batching, 24-node trees lost 14.9%", "hides behind the weight stream."),
       "project page / Batched serving", "boundary",
       note="项目页同样写出反号，用于交叉核对论文 §6.5")

    # ---- 成本与边界 ----
    ev("e-039", PAPER, S_PAPER,
       grab(P, "A round takes 7", "promoted 54 of them."),
       "Appendix D", "cost",
       note="循环成本：一轮 7–20 小时 / 20–86 GPU-小时；13 轮 164 小时 / 530 GPU-小时；486 改动、晋级 54")
    ev("e-040", PAPER, S_PAPER,
       grab(P, "A TLV cycle of the final H100 system takes about 30",
            "instead of 6.16 in a one-level step"),
       "Appendix C", "mech",
       note="TLV 一轮 30ms 拆解（两次 draft 1.05ms、Q 11.5ms、exact 14.9ms、glue 1.6ms），换 11.67 vs 6.16 token")
    ev("e-041", PAPER, S_PAPER,
       grab(P, "In AR decoding on SGLang", "with 32 requests."),
       "§6.3", "mech",
       note="W12 脱离投机解码仍加速 1.19–1.28×（1 请求）/1.13–1.20×（32 请求），权重缩 14–22%")
    ev("e-042", PAPER, S_PAPER,
       grab(P, "The shipped W12 GEMM beats cuBLAS on every", "allows 48-row tiles"),
       "§6.3", "mech",
       note="W12 GEMM 对 cuBLAS：1 行 1.19–1.47×，32 行 1.17–1.35×；初版 kernel 只有 cuBLAS 的 0.80–0.89 时间")
    ev("e-043", PAPER, S_PAPER,
       grab(P, "On the 8-position lattice, best-first trees raise", "the lattice and node budget."),
       "§6.4", "mech",
       note="exact replay：4.25 → 5.38（8 位置/32 节点）→ 5.85（16 位置）；16 节点时与 EAGLE-2 top-4 打平")
    ev("e-044", PAPER, S_PAPER,
       grab(P, "The agents closed most directions on a measured bound",
            "twice what the saved time bought back."),
       "Appendix F", "boundary",
       note="被关闭的方向：>32 节点每节点 0.17ms vs 值 0.063ms；Q 视图每减 1/8 字节掉约 0.01 的 top-1 一致率")
    ev("e-047", PAPER, S_PAPER,
       grab(P, "On the RTX PRO 6000, W12 is 1.18", "flat across verify rows."),
       "§6.3", "mech",
       note="PRO 6000 无 wgmma，W12 走 mma.sync 仍全面超过 cuBLAS（1.18–1.68×，13 个形状）")

    # ---- 仓库侧 ----
    ev("e-101", "doc-specpilot-repo-readme", S_CODE,
       grab(RREADME, "This repository ships the engine", "serve, benchmark and verify them."),
       "README.md:3-5", "code",
       note="交付边界：6 个 setting 的引擎 + serve/bench/verify 脚本")
    ev("e-102", "doc-specpilot-repo-readme", S_CODE,
       grab(RREADME, "In each round of the loop, a cost model", "to new rounds and deployments."),
       "README.md:11-16", "code",
       note="README 复述循环；紧接着就转到「本仓库交付什么」——循环本身不在交付物里")
    ev("e-103", "doc-specpilot-repo-readme", S_CODE,
       grab(RREADME, "We reproduced the four H100 settings from a fresh clone",
            "Brackets give 95% bootstrap CIs."),
       "README.md:Reproduced", "code",
       note="作者自报复现（非第三方），4 个 H100 setting，95% bootstrap CI")
    ev("e-104", "doc-specpilot-repo-readme", S_CODE,
       grab(RREADME, "Outputs are not bitwise identical to AR",
            "the target's own choice at that position."),
       "README.md:Evaluation", "code",
       note="仓库自承输出不逐位相同，并改用「每个提交的 token 都是目标的自身选择」这一人工判据")
    ev("e-105", "doc-specpilot-repo-readme", S_CODE,
       grab(RREADME, "The four single-request finals stream the target's BF16 weights in W12",
            "beats cuBLAS BF16 up to 64 rows per GEMM"),
       "README.md:W12", "code",
       note="W12 的仓库侧数字（含 batch 1–32 与 64 行的分界）")
    ev("e-121", "doc-specpilot-repo-readme", S_CODE,
       grab(RREADME, "A final is the stock tree with its setting's `files/` copied on top",
            "(no final deletes a file)"),
       "README.md:How the engines are built", "code",
       note="final 的定义：stock 树 + setting 的 files/ 覆盖，且没有任何 final 删文件")
    ev("e-106", "doc-specpilot-setting-h100-c1-dflash2-config", S_CODE,
       grab(RCONFIG, '"name": "int-015-tlvcbn32"'),
       "settings/h100_c1_qwen38-27b_dflash2/config.json", "code",
       note="final 的名字是候选编号，可回溯到晋级过程")
    ev("e-107", "doc-specpilot-setting-h100-c1-dflash2-config", S_CODE,
       grab(RCONFIG, '"SPECPILOT_D8R_TLV": "1"'),
       "settings/h100_c1_qwen38-27b_dflash2/config.json", "code",
       note="机制以环境开关交付；默认关闭即 stock 行为")
    ev("e-108", "doc-specpilot-setting-h100-c1-dflash2-config", S_CODE,
       grab(RCONFIG, '"SPECPILOT_TREE_MODE": "ddtree"'),
       "settings/h100_c1_qwen38-27b_dflash2/config.json", "code",
       note="树模式取 ddtree——best-first 的打分改变了，但树骨架沿用 DDTree")
    ev("e-109", "doc-specpilot-setting-h100-c1-dflash2-config", S_CODE,
       grab(RCONFIG, '"SPECPILOT_D7_W4": "all"'),
       "settings/h100_c1_qwen38-27b_dflash2/config.json", "code", stance="context",
       note="drafter 权重降到 4-bit（论文只一句 low-precision drafter weights）")
    ev("e-110", "doc-specpilot-compare-py", S_CODE,
       grab("specpilot-compare-py.txt", "Speedup = exp(mean over cells",
            "2000 resamples of requests within cells)"),
       "scripts/compare.py:5-9", "code",
       note="仓库增益口径与论文一致；并注明 tau 在 TLV 下改按每次 exact pass 计")
    ev("e-111", "doc-specpilot-compare-py", S_CODE,
       grab("specpilot-compare-py.txt", "def identical(a, b):", "len(ids)"),
       "scripts/compare.py:60-63", "code",
       note="仓库只报「输出逐位相同」的条数，**没有** mismatch rate / margin 判定")
    ev("e-112", "doc-specpilot-bench-sh", S_CODE,
       grab("specpilot-bench-sh.txt", "Workload: first turns of the dev split",
            "output ids and text)."),
       "scripts/bench.sh:4-9", "code",
       note="评测负载：dev split 首轮、贪心、2048 新 token；单请求取每集前 6 条（30 条）")
    ev("e-114", "doc-specpilot-cudaslot-py", S_CODE,
       grab("specpilot-cudaslot-py.txt", "Machine-wide CUDA-init semaphore",
            "campaign or user starts them."),
       "research/autoresearch/cudaslot.py:1-6", "code",
       note="仓库里最接近「控制器」的东西其实是 CUDA 初始化信号量，解决驱动 D 状态与 nvidia-smi 假死")
    ev("e-115", "doc-specpilot-cudaslot-py", S_CODE,
       grab("specpilot-cudaslot-py.txt", "Scheduling only: nothing here", "INFRA_FILES"),
       "research/autoresearch/cudaslot.py:27", "code",
       note="作者自己限定：这个文件只做调度，不参与测量")
    ev("e-116", "doc-specpilot-dflash-lab-readme", S_CODE,
       grab("specpilot-dflash-lab-readme.txt", "Hooks suit proposal-side changes",
            "decides what is emitted."),
       "research/dflash_lab/README.md", "code",
       note="诊断插件只做提案侧；权重不动，目标模型的贪心验证决定输出")
    ev("e-117", "doc-specpilot-build-engine-py", S_CODE,
       grab("specpilot-build-engine-py.txt", "The tree is <OUT_DIR>/{python,lab}",
            "keys the build caches by it."),
       "scripts/build_engine.py:1-6", "code",
       note="引擎 = stock 树 + overlays + setting/files，逐文件覆盖，输出内容哈希")
    ev("e-118", "doc-specpilot-build-engine-py", S_CODE,
       grab("specpilot-build-engine-py.txt", 'if which == "final":', "tree_sha(out)"),
       "scripts/build_engine.py:70-72", "code",
       note="final 分支只有 overlay(...)，没有删除动作——patch 只加不改语义默认")
    ev("e-119", "doc-specpilot-setting-h100-c1-dflash2-readme", S_CODE,
       grab("specpilot-setting-h100-c1-dflash2-readme.txt",
            "Engine = stock engine + `files/` (49 files)", "(`final.env`)."),
       "settings/h100_c1_qwen38-27b_dflash2/README.md", "code",
       note="final = stock + 49 文件 + 46 个 SPECPILOT_* 开关 + block 32")
    ev("e-120", "doc-specpilot-setting-h100-c1-dflash2-readme", S_CODE,
       grab("specpilot-setting-h100-c1-dflash2-readme.txt", "Main mechanisms:",
            "fused glue kernels and PDL"),
       "settings/h100_c1_qwen38-27b_dflash2/README.md", "code",
       note="主机制清单比论文 §4 多出 tail skip / fused glue / PDL 等纯工程项")

    # ---- 悬空引用：仓库自己的代码指向树里不存在的路径 ----
    ev("e-122", "doc-specpilot-techniques-budget-py", S_CODE,
       grab("specpilot-techniques-budget-py.txt",
            "Reference implementation for the ``budget`` family",
            "test_techniques_budget.py"),
       "research/dflash_lab/dflash_lab/techniques/budget.py:3-6", "code",
       note="插件指向 research/knowledge/ 与 research/validation/ 的文档与测试；这两个目录在公开树里不存在")
    ev("e-123", "doc-specpilot-techniques-budget-py", S_CODE,
       grab("specpilot-techniques-budget-py.txt", "the engine never imports it"),
       "research/dflash_lab/dflash_lab/techniques/budget.py:5", "code",
       note="作者明确：techniques 是参考实现，引擎从不 import——机制在引擎侧，判定侧在此只是原型")
    ev("e-124", "doc-specpilot-experiments-trace-py", S_CODE,
       grab("specpilot-experiments-trace-py.txt", "Load with ``research/autoresearch/replay.py``",
            "`spec_verify_ct`"),
       "research/dflash_lab/dflash_lab/experiments/trace.py:12-14", "code",
       note="trace 实验的输出要靠 replay.py 校验完整性，而该文件不在树里")
    ev("e-125", "doc-specpilot-dangling-refs", S_CODE,
       grab("specpilot-dangling-refs.txt", "被引用的路径 22 个", "缺失 10 个"),
       "analysis: audit_dangling.py 输出", "code",
       note="22 条路径引用里 10 条不存在：knowledge 缺 7、validation 缺 2、autoresearch 缺 1")
    ev("e-126", "doc-specpilot-dangling-refs", S_CODE,
       grab("specpilot-dangling-refs.txt", "knowledge: 存在 0 / 缺失 7",
            "validation: 存在 0 / 缺失 2"),
       "analysis: audit_dangling.py 输出（按区域）", "code",
       note="缺失集中在知识库与验证两区，恰好是「循环怎么知道改对了」所在的位置")

    # ---- 机制实现：论文的机制确实随代码交付 ----
    # 这一组是为了回答「机制在不在代码里」。第一版审计把
    # settings/*/files/python/sglang/（overlay 本体）当成 vendored 排除了，
    # 于是 183 个 specpilot_* 实现文件一个都没看到——是审计的范围错误。
    ev("e-127", "doc-specpilot-d5-w12-py", S_CODE,
       grab("specpilot-d5-w12-py.txt", "NESTED PLANES:", "wgmma-A-fragment lane order."),
       "settings/h100_c1_.../files/python/sglang/kernels/ops/gemm/specpilot_d5_w12.py:8-12",
       "code",
       note="W12 的嵌套平面布局写在代码里：12KB 记录 = Q 区 1B/weight + B 区半字节，与论文 §4.1 一一对应")
    ev("e-128", "doc-specpilot-d5-w12-py", S_CODE,
       grab("specpilot-d5-w12-py.txt", "the Q pass (`q_pass()`, two-level verify)",
            "zero extra memory."),
       "同一文件:12-18", "code",
       note="Q pass 只读 Q 区（1B/weight），**零额外显存**——论文 §4.3「不额外占显存」在代码里的实现")
    ev("e-129", "doc-specpilot-d8-tlv-py", S_CODE,
       grab("specpilot-d8-tlv-py.txt", "SPECPILOT_D8R_TLV_QNOISE", "0 default"),
       "srt/speculative/specpilot_d8_tlv.py:17-19", "code",
       note="**故障注入钩子随代码交付**：以概率把 Q 预测替换成别的 token，用来制造链失配")
    ev("e-130", "doc-specpilot-d8-tlv-py", S_CODE,
       grab("specpilot-d8-tlv-py.txt", "def perturb_pred", "return torch.where(flip, pred + 1, pred)"),
       "同一文件:74-79", "code",
       note="perturb_pred 的实现：逐元素以 q_noise 概率 pred+1，无 host sync（可在 graph 里跑）")
    ev("e-131", "doc-specpilot-tree-gdn-py", S_CODE,
       grab("specpilot-tree-gdn-py.txt", "# fp32 state as hi + mid + lo bf16 terms",
            "tl.dot(kb, h_lo)"),
       "kernels/ops/attention/fla/specpilot_tree_gdn.py（WY kernel）", "code",
       note="论文 §4.2 的三段 BF16 表示 24 位有效位：hi/mid/lo 拆解 + 三个 tl.dot，代码逐行对应")
    ev("e-132", "doc-specpilot-tree-gdn-py", S_CODE,
       grab("specpilot-tree-gdn-py.txt", "SPECPILOT_TREE_GDN=paths",
            "writes no per-node fp32 state"),
       "同一文件:1-3", "code",
       note="「不存每节点 fp32 状态」在代码注释里的原话，与论文 §4.2 的 snapshot-free 说法一致")
    ev("e-133", "doc-specpilot-d7-chain-py", S_CODE,
       grab("specpilot-d7-chain-py.txt", "prefill as a teacher-forced verify chain",
            "skips the extend forward."),
       "settings/h100_batch_.../files/.../speculative/specpilot_d7_chain.py:1-4", "code",
       note="论文 §4.4 的 prompt admission：短 prompt 跳过 extend，作为强制链并进 decode 批")
    ev("e-134", "doc-specpilot-d7-chain-py", S_CODE,
       grab("specpilot-d7-chain-py.txt", "A newly admitted request with a short prompt",
            "``p[0]``."),
       "同一文件:3-6", "code",
       note="准入的具体形态：KV 提交 0、pending root = p[0]，与论文「≤384 token 的链」对应")


# ------------------------------------------------------------------ claims
def build_claims() -> None:
    claim("c-001",
          "SpecPilot 的循环是「五阶段 + 一次否决」：Phase 0 用成本模型量缺口，Phase 1 由 master agent "
          "按最大因子开方向（每条方向一块 GPU），Phase 2 把单独不够门槛的补丁叠起来再计时，"
          "Phase 3 的 kernel 子 agent 专修离 byte floor 最远的 kernel，Phase 4 在未见过的请求上封 sealed final；"
          "任何一环 token forcing 不过即整轮作废。",
          ctype="attribution", confidence="high",
          eids=["e-003", "e-009", "e-011", "e-048", "e-002", "e-010"],
          facets={"plane": "judge", "topic": "loop"},
          notes="「未见过的请求」是关键：开发请求 agent 看得到，sealed 请求看不到")

    claim("c-002",
          "循环的权限边界是可执行的：agent 只能调用控制器脚本、不能修改；晋级条件是增益的 95% 下界同时"
          "超过 1% 与 2×（stock 对 stock 的噪声），输出与当前最优不一致时门槛抬到约 3%。"
          "H100 单请求上噪声 <0.1%，故实际门槛接近 1%；单条改动的典型量级是 1.06–1.08×，正是为这种幅度设计的。",
          ctype="spec", confidence="high",
          eids=["e-009", "e-048", "e-046"],
          facets={"plane": "judge", "topic": "promotion"},
          notes="把「谁说了算」从组织问题变成数值问题，是本专题认为最可迁移的部分")

    claim("c-003",
          "成本模型把该优化什么写成三分之积：τ_best/τ（更好的树能多收多少 token）、T_prof/T_floor"
          "（已计入 profile 的 kernel 离 byte floor 多远）、T_step/T_prof（profile 之外的开销）。"
          "每轮重算取最大因子作为下一轮方向；byte floor 取「60% 峰值稠密算力的 FLOP 时间」与"
          "「90% 峰值带宽的字节时间」中的较大者。",
          ctype="spec", confidence="high",
          eids=["e-004", "e-007", "e-008", "e-005"],
          facets={"plane": "costmodel", "topic": "ceiling"},
          notes="τ_best 不是理论最优，而是「exact replay 里最好一棵树在最佳节点预算下的 τ」")

    claim("c-004",
          "三轮的实际走向说明排序确实会变：第一轮 τ 因子领先（stock 只验一条链），第二轮变成步成本"
          "（权重读占 23.61ms 的 80%），第三轮两个因子都接近上限，增益改从「ceiling 自身假设一次 draft "
          "配一次 exact pass」里取，即 TLV。系统速度 184 → 270 → 416 tokens/s。",
          ctype="measurement", confidence="high",
          eids=["e-028", "e-029", "e-006"],
          facets={"plane": "loop", "topic": "three-rounds"},
          notes="第三轮是全文最有信息量的一步：连「上界的定义」都被当成可改对象")

    claim("c-005",
          "没有 ceiling 排序的对照（单 agent 循环）三轮只到 1.34×，SpecPilot 是 2.13×；差别不在模型或预算，"
          "而在对照把注意力放在最显眼的因子（每步 token 数）上，始终没碰占步时 80% 的目标权重读取。",
          ctype="measurement", confidence="high",
          eids=["e-030", "e-006"],
          facets={"plane": "judge", "topic": "ablation"},
          notes="全文唯一的「有无成本模型」对照，但只有一个 setting、一次运行")

    claim("c-006",
          "本文的「无损」不是逐位相同，而是：每个被接受的 token 都落在一次精确权重 pass 验证过的路径上、"
          "且等于该 pass 的 argmax。因此允许浮点归约顺序造成的近 tie 翻转——stock 本身就这样偏离 AR，"
          "首次偏离处两 token 的 log-prob 差不超过 0.232 nats。",
          ctype="spec", confidence="high",
          eids=["e-014"],
          facets={"plane": "lossless", "topic": "definition"},
          notes="定义先于度量：先把「无损」降格为「相对精确 pass 的无损」，判据才可能成立")

    claim("c-007",
          "token forcing 的构造是：把系统输出喂回 stock 引擎、用 FP32 LM head 重打分，逐 token 比对 argmax；"
          "stock 自身在 0.72% 的 token 上失配，几乎都是近 tie。近 tie 阈值 δ 不是拍的，而是由 stock 首次"
          "偏离 AR 时的最大 margin 向上取整到 1/8 的倍数。",
          ctype="spec", confidence="high",
          eids=["e-012", "e-013"],
          facets={"plane": "lossless", "topic": "token-forcing"},
          notes="δ 的定法把「基线自己也不干净」变成阈值的一部分，而不是要求基线为 0")

    claim("c-008",
          "拒绝用两条规则：rate rule（失配率高出 stock 超过 0.5 个百分点、95% 置信）与 event rule"
          "（margin > 2δ 的大 margin 失配经二项检验显著多于 stock）。事件可被解释掉，但只有三种解释："
          "stock 在自身路径上能复现、margin 与 stock 相当、或打分器 argmax 随 prefill 长度改变。",
          ctype="spec", confidence="high",
          eids=["e-013", "e-015"],
          facets={"plane": "lossless", "topic": "rejection-rules"},
          notes="两条规则分别管「整体分布」与「尾部事件」——只查均值会漏掉少量系统性错误")

    claim("c-009",
          "注入故障实验说明准确率不能替代该判据：给每第 7 个 vocab id 在 2048 token 后加 2 的 logit bias，"
          "准确率变化在无损与故障系统之间区间重叠；而失配率把它们分开——0.73%/0.52%（无损，贴近 stock 的 "
          "0.72%/0.53%）对 2.0%/2.4%（故障），并由 192/200 与 191/200 条未解释的大 margin 事件坐实。",
          ctype="measurement", confidence="high",
          eids=["e-015", "e-014"],
          facets={"plane": "lossless", "topic": "fault-injection"},
          notes="全文说服力最强的一处：同时给出判据的假阴性与假阳性两侧")

    claim("c-010",
          "W12 是无损的 12-bit 权重格式：每个输出通道取覆盖最多权重的 16-binade 窗口，权重存 sign + 4-bit "
          "指数偏移 + 7-bit 尾数；窗外、零与 denormal 走稀疏 escape 表精确还原。实测 12.01–12.02 bits/weight，"
          "Qwen3.8-27B 的转换层从 44.67 降到 33.58 GB，加载时逐张量与 checkpoint 按位比对。",
          ctype="measurement", confidence="high",
          eids=["e-017", "e-018", "e-019"],
          facets={"plane": "mech", "topic": "w12"},
          notes="escape 率 7.33e-5（Qwen3.8-27B），故稀疏表很小")

    claim("c-011",
          "W12 的收益一半来自格式、一半来自 kernel：GEMM 在寄存器里解码，记录以 128×64 tile 为单位的 12KB "
          "块流式读取，stream-K 的固定归约顺序保证确定性。它在 Qwen3.8-27B 的每个投影上都超过 cuBLAS——"
          "1 行 1.19–1.47×、32 行 1.17–1.35×，PRO 6000（无 wgmma，改走 mma.sync）上 1.18–1.68×。",
          ctype="measurement", confidence="high",
          eids=["e-018", "e-042", "e-047"],
          facets={"plane": "mech", "topic": "w12-gemm"},
          notes="首版 kernel 只有 cuBLAS 的 0.80–0.89 时间，是被 kernel 子 agent 调上去的")

    claim("c-012",
          "W12 可脱离投机解码使用：SGLang 纯 AR 解码上单独开启即得 1.19–1.28×（1 请求）与 1.13–1.20×"
          "（32 请求），权重缩小 14–22%，省下的显存把 KV pool 放大 2.0×（Qwen3.8-27B）与 2.5×"
          "（Muse-Glimmer-30B）。",
          ctype="measurement", confidence="high",
          eids=["e-041"],
          facets={"plane": "mech", "topic": "w12-ar"},
          notes="这条让 W12 从「SpecPilot 的零件」变成可独立采纳的工程结论")

    claim("c-013",
          "best-first 树把每步接受的 token 从 stock 链的 4.25 提到同 lattice 32 节点的 5.38；把 drafter 从 8 "
          "位置放宽到 16 位置后到 5.85、63 节点到 6.25。16 节点预算下它与 EAGLE-2 式 top-4 树打平"
          "（5.03 vs 5.02）、优于 Sequoia 树（4.71），说明继续加宽收益有限、得换 lattice 或预算。",
          ctype="measurement", confidence="high",
          eids=["e-043", "e-020"],
          facets={"plane": "mech", "topic": "tree"},
          notes="这是 exact replay（离线重放）的数字，不是实测时延——两者口径必须分开")

    claim("c-014",
          "混合目标（Qwen3.8-27B 的 64 层里 48 层是 GDN）上，树验证不存每节点状态快照，而是沿根路径从已提交"
          "状态重算；WY verify kernel 把 FP32 状态拆成三个 BF16 部分以表示全部 24 位有效位，在 tensor core "
          "上一次解出所有路径，与 path kernel 的差在一个 BF16 ulp 内。两者只改归约顺序，故 exact pass 仍精确。",
          ctype="spec", confidence="high",
          eids=["e-021"],
          facets={"plane": "mech", "topic": "hybrid-tree"},
          notes="这是让「树」在混合架构上成立的前提；没有它，每节点一份状态快照会把收益吃掉")

    claim("c-015",
          "TLV 无损，是因为只有 exact pass 提交 token：Q pass 在 W12 已嵌套的 8-bit 视图上跑，只提出链 C 与"
          "下一轮 draft 的锚点，不更新 KV 与递归状态；随后一次 exact pass 同时验证 C 与挂在它下面的子树。"
          "Q 与 exact 的 top-1 一致率约 98%（嵌套 8-bit 视图 0.983），且不额外占显存。",
          ctype="spec", confidence="high",
          eids=["e-022", "e-023", "e-024"],
          facets={"plane": "mech", "topic": "tlv"},
          notes="「零拷贝」来自 W12 记录本身就是 8-bit 视图 + 低尾数平面，Q pass 只读前 2/3")

    claim("c-016",
          "TLV 的代价结构明确：H100 final 的一轮约 30ms，其中两次 draft 各 1.05ms、Q pass 11.5ms、exact pass "
          "14.9ms、胶水 1.6ms；换来每次 exact pass 接受 11.67 而非 6.16 个 token。Q pass 占到一步的 0.80–0.88 "
          "时，一轮必须接受接近两倍的 token 才不亏——这正是它在批处理下反号的原因。",
          ctype="measurement", confidence="high",
          eids=["e-040", "e-023", "e-037"],
          facets={"plane": "mech", "topic": "tlv-cost"},
          notes="同一机制在单请求与批处理下符号相反，是全文最干净的「机制依赖 regime」证据")

    claim("c-017",
          "批处理下的机制是另一类：共享节点预算（按路径 log-prob 在请求间分配固定总预算，因 best-first "
          "前缀闭包故每份仍是合法树）、每请求 16/12/8 位置的 drafter block、以及只在调度器本来要压住时才并流的 "
          "prompt 准入。它们的共同点是只挑选要 draft/verify 的行，不改变验证语义。",
          ctype="spec", confidence="high",
          eids=["e-025", "e-026", "e-027"],
          facets={"plane": "mech", "topic": "batching"},
          notes="与单请求侧的「多花验证工作」相反：批处理侧全部是「少花」")

    claim("c-018",
          "批处理下的收益量级：共享节点预算在 DSpark 上比等尺寸的每请求树多接受 6–14% 的 token，"
          "per-request drafter block 为 1.040×；只准入等待中的 prompt 在 24 请求时 +3.5%（未配对），"
          "而「准入所有短 prompt」是负收益。",
          ctype="measurement", confidence="medium",
          eids=["e-038"],
          facets={"plane": "mech", "topic": "batching-gain"},
          notes="3.5% 那条作者自己标了 unpaired，故整条主张降为 medium")

    claim("c-019",
          "主结果：单请求下 SpecPilot 对 AR 达 8.86–9.41×（H100）与 10.63–10.87×（RTX PRO 6000），对 stock "
          "均超过 2×（sealed 2.13/2.38/2.44/2.21×）；批处理下对 AR 3.90×/3.93×，对 stock 1.85×（DFlash2）与 "
          "1.94×（DSpark）。批处理侧 stock 较弱的目标获益更大（Qwen3.5-4B 2.39×、Gemma-4-12B 3.11×）。",
          ctype="measurement", confidence="high",
          eids=["e-001", "e-033", "e-034", "e-031"],
          facets={"plane": "eval", "topic": "main-results"},
          notes="两套数字不可混用：10.87× 是「对 AR」，2.44× 是「对 stock」，同一个 setting 的两个口径")

    claim("c-020",
          "口径必须跟着数字走：增益定义为逐请求输出速率比的对数、按 benchmark×batch 等权求几何均值；"
          "主表是对 AR 的速度比（交错的 AR/stock/SpecPilot 运行），sealed 增益是对 stock、在未见请求上、"
          "两次配对运行；两者相差 −2%~+6%。TLV 下 τ 改定义为「每次 exact pass 的 token 数」而非每步，"
          "故 τ 可以超过 16 的 draft block。",
          ctype="spec", confidence="high",
          eids=["e-032", "e-023", "e-110", "e-112"],
          facets={"plane": "eval", "topic": "metrics"},
          notes="τ 的定义在 TLV 下变了——这是最容易把 13.08 误读成「一步接受 13 个 token」的地方")

    claim("c-021",
          "机制会反号，且论文自己给了量化：批处理下 24 节点树在 FP8 目标上 −14.9%，BF16 Qwen3.8-27B 上 "
          "24 位置 block −9.9%、TLV −13%。原因是单请求时权重流把额外验证工作藏住了，批处理时它按行累加。",
          ctype="measurement", confidence="high",
          eids=["e-037", "e-049"],
          facets={"plane": "boundary", "topic": "sign-flip"},
          notes="项目页与论文两处一致，可交叉核对")

    claim("c-022",
          "被关闭的方向也用测量封口：11-bit 权重解码慢 3×；48 节点树 −4.3%；超过 32 节点后每个节点约值 "
          "0.063ms 却要花 0.17ms；嵌套 Q 视图每减 1/8 字节掉约 0.01 的 top-1 一致率，代价约为省下时间的两倍。",
          ctype="measurement", confidence="high",
          eids=["e-044"],
          facets={"plane": "boundary", "topic": "closed-directions"},
          notes="这张表是本文最稀缺的东西：负结果带测量依据")

    claim("c-023",
          "循环自身的成本不低：一轮 7–20 小时、20–86 GPU-小时；十三轮合计 164 小时 / 530 GPU-小时，"
          "产生 486 个代码改动、晋级 54 个（约 11%）。一个 setting 若在两轮内到位，则由两轮分担工作量。",
          ctype="measurement", confidence="high",
          eids=["e-039"],
          facets={"plane": "cost", "topic": "loop-cost"},
          notes="54/486 的「晋级率」是改动级，不是轮次级")

    claim("c-024",
          "记忆让新部署不必从零开始：DSpark 复用树/W12/TLV 三条条目（一次晋级 2.110×）；RTX PRO 6000 仅移植 "
          "H100 的树与 W12（W12 改 mma.sync、树改 Triton attention）就得 sealed 1.92×，TLV 与 split-KV 再推到 "
          "2.44×；EAGLE-3（顺序 drafter）首轮 2.67×，最终 3.11×。条目只在「套回 stock 能逐字重建源系统代码」时才保留。",
          ctype="measurement", confidence="high",
          eids=["e-016", "e-035", "e-036"],
          facets={"plane": "memory", "topic": "transfer"},
          notes="「复用条目不算新发现」这条规则，是记忆不会被重复计入收益的原因")

    claim("c-025",
          "ceiling 本身会低估：PRO 6000 上最终达到 2.44×，而它对该系统的 ceiling 估计是 2.12×。"
          "原因是 ceiling 假定一次 draft 配一次 exact pass——TLV 打破了这个假定。换言之，"
          "「模型的上界」与「模型所依赖的假设」哪一个才是瓶颈，本身也要每轮重判。",
          ctype="prediction", confidence="high",
          eids=["e-035", "e-029"],
          derivation="由 e-035（2.44× 超过 2.12× ceiling，且 ceiling 假定 one draft per pass）与 e-029"
                     "（第三轮增益正来自打破该假定）推出：ceiling 不是硬上界，而是「在给定结构假设下」的上界；"
                     "实测超过它时，正确解读是假设被打破，而不是测量出错。",
          facets={"plane": "costmodel", "topic": "ceiling-limit"},
          notes="系统推断，不是来源事实：论文只并列陈述了两个数字，没有把二者合起来说")

    claim("c-026",
          "仓库交付的是六个 setting 的结果引擎，不是循环本身：每个 final 等于 stock 树叠该 setting 的 files/ "
          "（且不删任何文件），再用 config.json 里 46–66 个 SPECPILOT_* 开关与 block size 打开机制；"
          "README 的复现表是作者自跑（4 个 H100 setting、95% bootstrap CI），不是第三方复现。",
          ctype="attribution", confidence="high",
          eids=["e-101", "e-117", "e-118", "e-119", "e-103", "e-121",
                "e-105", "e-106", "e-107", "e-108", "e-109", "e-120"],
          facets={"plane": "code", "topic": "delivery"},
          notes="「final = stock + 覆盖且不删文件」由 build_engine.py 与 README 两处独立坐实")

    claim("c-027",
          "论文里承担判定的三个组件在公开仓库中找不到对应实现：控制器（配对运行与晋级判定）、结构化记忆库"
          "（140 条条目）、token forcing（失配率与 margin 审计）。仓库里叫 controller 的是 CUDA 初始化信号量，"
          "memory 只出现在 README 文字里，比对工具 compare.py 只报告输出逐位相同的条数。",
          ctype="measurement", confidence="high",
          eids=["e-111", "e-114", "e-115", "e-101", "e-116", "e-123"],
          facets={"plane": "code", "topic": "missing-parts"},
          notes="证据是检索结果（repo_audit.json 的 component_hits），不是印象；"
                "「找不到」只能是「在这份快照里找不到」，见 c-028")

    claim("c-031",
          "公开树是更大工作区的裁剪子集，且裁剪口可定位：仓库自己的代码引用了 22 条路径，其中 10 条不存在——"
          "`research/knowledge/` 的 7 篇方法与搜索空间文档、`research/validation/` 的 2 个测试/预言机、"
          "以及 `research/autoresearch/replay.py`。缺失集中在「知识」与「验证」两个区域，"
          "恰好是「循环怎么知道改对了」所在的位置，而机制侧（引擎、techniques、bench）都在。",
          ctype="measurement", confidence="high",
          eids=["e-125", "e-126", "e-122", "e-124"],
          facets={"plane": "code", "topic": "pruned-tree"},
          notes="比「grep 不到 token forcing」强得多：这是仓库**自证**的引用，不是我的检索空白")

    claim("c-032",
          "论文的机制不是伪代码：六个 setting 的 overlay 共 333 个文件，其中 183 个是 `specpilot_*` / "
          "`dflash_d*` 实现，逐 setting 25–37 个。W12 的 12KB 嵌套平面布局、Q pass 的零额外显存读取、"
          "树验证的三段 BF16（hi/mid/lo，24 位有效位）WY kernel、prompt admission 的强制链，"
          "都能在源码里逐行对上论文的描述。",
          ctype="measurement", confidence="high",
          eids=["e-127", "e-128", "e-131", "e-132", "e-133", "e-134", "e-120"],
          facets={"plane": "code", "topic": "mechanisms-shipped"},
          notes="这一条是对 c-027 的必要平衡：**机制侧完整交付，判定侧缺失**。"
                "不写这条会让人误读成「仓库是空壳」")

    claim("c-033",
          "故障注入实验的装置也随代码交付：`SPECPILOT_D8R_TLV_QNOISE` 以给定概率把 Q 的预测替换成别的 token，"
          "专门用来制造链失配（`perturb_pred` 逐元素 pred+1，无 host sync 故能在 graph 里跑）。"
          "这与论文 §6.2 的注入故障实验对应——**判据的测试装置在**，而判据本身（失配率与 margin 审计）不在。",
          ctype="measurement", confidence="high",
          eids=["e-129", "e-130"],
          facets={"plane": "code", "topic": "fault-injection-shipped"},
          notes="这处对比最能说明裁剪的形状：造故障的钩子留了，判定故障的脚本没留")

    claim("c-028",
          "对「缺失」的表述必须限定范围：本审计只覆盖 commit 78c42af 的公开快照，检索范围是"
          "「仓库根与 research/、settings/*/files/、overlays/，排除 vendored 的 python/sglang 上游副本」；"
          "作者可能未公开控制器与记忆库，也可能它们存在于私有分支。"
          "因此正确结论是「公开仓库未交付」，而不是「不存在」。",
          ctype="spec", confidence="medium",
          eids=["e-102", "e-115", "e-125"],
          facets={"plane": "code", "topic": "scope-of-audit"},
          notes="第一条限定把 c-027/c-031 从断言降为可复查结论。"
                "§6 记了一次范围错误：第一版审计把 overlay 也当 vendored 排除，"
                "漏掉 183 个机制实现文件——**范围写错会把「有」看成「无」**")

    claim("c-029",
          "论文与仓库在「怎么判定无损」上口径不同：论文说输出不逐位相同是正常的、并用 token forcing 统计判定；"
          "仓库的 compare.py 仍以「identical outputs same/tot」为主要输出，README 则改用「每个提交的 token "
          "都是目标模型自身的选择」这一人工判据。事实不冲突，但判据的自动化程度不同——论文的统计判据没有随代码交付。",
          ctype="attribution", confidence="disputed",
          eids=["e-104", "e-014"],
          counters=["e-111"],
          facets={"plane": "code", "topic": "judge-not-shipped"},
          notes="并列呈现不强裁决：e-104 说明作者确实做了逐 token 检查（人工），e-111 说明交付脚本里没有该检查；"
                "两种解读都成立——检查发生在离线流程里，或检查没进仓库。")

    claim("c-030",
          "可迁移的不是某个机制，而是三条判据工程：(1) 上界要分解成可重算的因子，否则搜索会被最显眼的瓶颈吸住；"
          "(2) 晋级只看增益的下界与噪声之比，不看点估计；(3) 正确性判据要能同时挡住假阳性与假阴性——"
          "本文用注入故障验证了第三条、用单 agent 对照验证了第一条，第二条靠把噪声写进门槛本身。",
          ctype="prediction", confidence="medium",
          eids=["e-008", "e-009", "e-015", "e-030"],
          derivation="把 c-003/c-005（因子分解与无成本模型的对照）、c-002（下界+噪声门槛）、c-009"
                     "（注入故障下准确率失效而 token forcing 有效）合并，得到「判据工程」这一层的三条做法；"
                     "这是本归档的综合，不是论文的原话。",
          facets={"plane": "judge", "topic": "transferable"},
          notes="系统推断：论文没有把这三条并列成方法论")


# ------------------------------------------------------------------ 输出
def write_csv(name: str, rows: list[dict], cols: list[str]) -> None:
    p = HERE / name
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"  {name}: {len(rows)} 行")


def main() -> int:
    build_sources()
    build_evidence()
    build_claims()

    write_csv("sources.csv", SOURCES,
              ["source_id", "url", "source_type", "publisher", "title", "published_at",
               "updated_at", "fetched_at", "language", "trust_tier", "access", "license",
               "notes"])
    write_csv("documents.csv", DOCROWS,
              ["document_id", "source_id", "content_hash", "parser_version", "byte_size",
               "snapshot"])
    write_csv("evidence.csv", EVIDENCE,
              ["evidence_id", "document_id", "source_id", "quote", "locator", "quote_type",
               "stance", "fetched_at", "note"])
    write_csv("claims.csv", CLAIMS,
              ["claim_id", "statement", "claim_type", "as_of", "confidence", "evidence_ids",
               "counter_evidence_ids", "derivation", "facets", "notes"])

    print(f"\nsources {len(SOURCES)}｜evidence {len(EVIDENCE)}｜claims {len(CLAIMS)}"
          f"｜documents {len(DOCROWS)}")
    if FAILS:
        print(f"\n[!] {len(FAILS)} 处未取到：")
        for f in FAILS:
            print("   ", f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
