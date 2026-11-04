"""抓取器 v2：修掉 8 个失败暴露出的四类问题。

## 逐条对账（diag_grab.py 的实测结果）

1. **最好的引文因「无数字」被拒。**
   2403.02310 窗口原文：
     "The prefill phase is compute-bound because it processes all tokens of
      an input prompt in parallel whereas the decode phase is memory-bound
      because it processes only one token per-request at a time."
   这是全文对 q1 最有力的一句，却因不含百分比被 NUMBER 判据拒掉。
   -> 修：NUMBER 收紧为「真数字」，同时允许调用方显式关掉；并把
      「两阶段受限类型对比」列入 REGIME 允许模式（它本身就是量化判断：
      计算受限 vs 带宽受限）。

2. **抓到标题。**
   2610.06917 / 2404.09526 / 2605.28302 的第一个命中都落在论文标题上
   （全文首部即标题）。标题是原文子串，E1 会通过，但对论证零贡献。
   -> 修：若窗口与标题高度重合则跳过（上一轮用「前 40 字符」判，
      这次标题被窗口截断后仍重合，故改为**重合度**判断）。

3. **配置项被「无实义词」拒。**
   sglang-pd 的窗口是 `--disaggregation-mode prefill --port 30000 ...`，
   没有 is/we/the 这类词，但它是**最硬的证据**：官方文档里确有此参数。
   -> 修：窗口含 CLI 旗标（--xxx）或表格行时，视为实义。

4. **GitHub 页面抓取不完整。**
   nvidia-nixl 快照里 RDMA / NVLink / GPUDirect 各 0 次——GitHub 的
   README 是异步渲染，抓到的是壳。
   -> 修：不在此处修抓取，改为换源：抓 raw.githubusercontent.com 的
      README.md（见 fetch_readme.py）。这只是渠道问题，不是判据问题。

## 判据放宽的边界

放宽三处，但**没有**放宽「引文必须是原文子串」——那是 E1 的职责，
由 invariants 独立验证。这里只管「选哪一段」，两件事必须分开。
"""

from __future__ import annotations

import re

FRONT = re.compile(
    r"†|thanks:|Corresponding author|Affiliation|Equal contribution"
    r"|joint first author|Work done during|@[a-z]|arXiv:\d"
    r"|Preprint\.|Under review", re.I)

SUBSTANCE = re.compile(
    r"\b(is|are|was|were|we|our|this|these|it|they|shows?|propose[sd]?"
    r"|use[sd]?|perform|achiev|improv|reduc|increas|report|observ|find"
    r"|allow|enable|require|depend|means?|because|however|while|when"
    r"|thus|can|could|may|would|should|has|have|had|not|than|more|less"
    r"|also|only|both|each|such|other|same|different|due|given|per)\b"
    r"|是|我们|本文|该|可以|表明|因此", re.I)

# 配置项/命令/表格行：没有自然语言实义词，但作为证据是硬的
CONFIG = re.compile(r"(?:^|\s)--[a-z][\w-]{2,}|^\s*\|.*\|\s*$"
                    r"|[a-z_]+=[\w.-]+", re.M)

# 量化：真数字（百分比/倍数/速率/延时/容量/卡数）
NUMBER = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|×|x\b|times|GB/s|GiB/s|TB/s|MB/s|ms\b|us\b"
    r"|μs|GB\b|GiB\b|MB\b|KB\b|TB\b|tokens?/s|tok/s|qps|TFLOPS|FLOPs"
    r"|W\b|秒|毫秒|倍|张卡|GPUs?\b)", re.I)

# 「受限类型对比」本身是量化判断，即使没写百分比也可用
REGIME = re.compile(
    r"(?:compute|memory)[- ](?:bound|intensive)[^.]{0,200}"
    r"(?:memory|compute)[- ](?:bound|intensive)"
    r"|(?:compute|memory)[- ]bound[^.]{0,120}(?:whereas|while|but)"
    r"|arithmetic intensity", re.I)


def _window(text: str, pos: int, before: int = 220,
            after: int = 340) -> str:
    """从 pos 向两侧扩窗，尽量在句末收尾。"""
    lo = max(0, pos - before)
    hi = min(len(text), pos + after)

    seg = text[lo:pos]
    m = None
    for m in re.finditer(r"(?:[.!?]\s+|\n\n)", seg):
        pass
    if m:
        lo += m.end()

    seg2 = text[pos:hi]
    m2 = re.search(r"[.!?](?:\s|$)|\n\n", seg2)
    if m2:
        hi = pos + m2.end()

    return " ".join(text[lo:hi].split())


def _title_like(q: str, title: str) -> bool:
    """引文是否只是标题（或其截断）。

    用重合度而非前缀匹配：窗口常把标题截断成 30~60 字符，
    前缀判据会漏。做法：若引文中超过 70% 的词都出现在标题里，判为标题。
    """
    if not title:
        return False
    qw = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) > 2]
    if not qw:
        return False
    tw = set(re.findall(r"[a-z0-9]+", title.lower()))
    hit = sum(1 for w in qw if w in tw)
    return hit / len(qw) > 0.7 and len(qw) < 30


def find_quotes(text: str, keywords: list[str], *, need_number: bool,
                title: str = "", max_try: int = 40,
                skip_first: int = 1) -> list[str]:
    """按关键词命中顺序返回候选引文。

    skip_first：每个关键词跳过前 N 个命中（默认 1）。
    全文首部的第一个命中通常是标题或作者行——这是上一轮和本轮
    重复踩到的同一个坑，故做成默认行为而不是逐个调用方去躲。
    """
    out: list[str] = []
    for kw in keywords:
        seen = 0
        for m in re.finditer(kw, text, re.I):
            seen += 1
            # 只在**正文首部**跳过首命中，且仅当该关键词出现多次。
            #
            # 第一版写 skip_first and m.start() < 4000，看似合理，
            # 实际把「只出现一次」的关键词整条废掉：nvidia-nixl 的
            # "abstraction over various types of memory" 全文 1 次，
            # 2608.03741 的 "pays for itself" 全文 1 次，都被跳过，
            # 于是报「无合格命中」——而文本里明明有。
            #
            # 标题污染的真实特征是：命中位置在文件最开头（标题/作者区）。
            # 故改为按**总次数**判断：只出现一次的关键词一律不跳。
            if (skip_first and seen <= skip_first and m.start() < 3000
                    and len(re.findall(kw, text, re.I)) > 3):
                continue
            w = _window(text, m.start())
            if len(w) < 60:
                continue
            if _title_like(w, title):
                continue
            if not (SUBSTANCE.search(w) or CONFIG.search(w)):
                continue
            if need_number and not (NUMBER.search(w)
                                    or REGIME.search(w)):
                continue
            out.append(w)
            if len(out) >= max_try:
                return out
    return out


def ok_quote(q: str, title: str = "") -> bool:
    if len(q) < 60 or len(q) > 900:
        return False
    if FRONT.search(q):
        return False
    if _title_like(q, title):
        return False
    return True
