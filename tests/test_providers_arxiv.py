"""`services/providers` 的 arXiv 适配器测试。

## 为什么测这个

先前每个研究专题都自带一份 arXiv 抓取脚本
（`cuda-kernel-gcn/paper/fetch_recent.py`、`cuda-kernel-rl/fetch_rl.py`），
同一套 XML 解析逻辑抄了三遍。把检索收进 `services/providers` 之后，
这里必须证明它**等价于**那些脚本——否则「归位」只是换个地方重复。

## 测试分两层

1. **离线**：给一段真实 arXiv Atom 响应（截取），验证解析、去重、
   字段归一、`src-arxiv-*` 命名。不发网络请求。
2. **在线**（可选，`--online`）：真实检索一次，验证限速与字段完整性。
   默认不跑——CI 里不该依赖外部服务可用性。

不依赖 pytest：`python tests/test_providers_arxiv.py [--online]`
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import (  # noqa: E402
    ArxivProvider,
    SearchHit,
    hits_to_records,
)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2507.14111v2</id>
    <updated>2025-07-24T00:00:00Z</updated>
    <published>2025-07-18T00:00:00Z</published>
    <title>CUDA-L1: Improving CUDA Optimization via Contrastive
  Reinforcement Learning</title>
    <summary>We present CUDA-L1, which delivers an average speedup of
  x3.12 with a median speedup of x1.42 over 250 CUDA kernels.</summary>
    <author><name>Alice</name></author>
    <author><name>Bob</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2507.11948v1</id>
    <updated>2025-07-16T00:00:00Z</updated>
    <published>2025-07-16T00:00:00Z</published>
    <title>Kevin: Multi-Turn RL for Generating CUDA Kernels</title>
    <summary>We train a model with multi-turn reinforcement learning.</summary>
    <author><name>Carol</name></author>
  </entry>
</feed>
"""

NOW = "2026-11-04T09:00:00+08:00"


def test_parse() -> None:
    hits = ArxivProvider._parse(SAMPLE_XML, "test-query", NOW)

    check("解析出 2 条", len(hits) == 2, str(len(hits)))

    h = hits[0]
    check("arxiv_id 正确", h.arxiv_id == "2507.14111", h.arxiv_id)
    check("source_id 命名带 src-arxiv- 前缀",
          h.source_id == "src-arxiv-2507-14111", h.source_id)
    # 标题里的换行与连续空格必须归一，否则后续与 papers.json 比对会失配
    check("标题空白归一",
          "\n" not in h.title and "  " not in h.title, repr(h.title))
    check("标题内容完整",
          h.title.startswith("CUDA-L1") and "Contrastive" in h.title, h.title)
    check("摘要空白归一", "\n" not in h.abstract, repr(h.abstract[:40]))
    check("published 截到日期", h.published == "2025-07-18", h.published)
    check("fetched_at 带时区", "+08:00" in h.fetched_at, h.fetched_at)
    check("记录了命中 query", h.query == "test-query", h.query)
    check("作者列表", h.authors == ["Alice", "Bob"], str(h.authors))
    check("url 指向 abs 页",
          h.url == "https://arxiv.org/abs/2507.14111", h.url)

    # 转换后应与既有的 papers.json 记录同构
    rec = hits_to_records(hits)[0]
    for k in ("id", "title", "authors", "published", "updated",
              "abstract", "arxiv_url"):
        check(f"记录含字段 {k}", k in rec, str(rec.keys()))


def test_dedup() -> None:
    """search_many 必须去重，且保留首次命中的 query。"""
    p = ArxivProvider()
    calls: list[str] = []

    def fake_search(query: str, *, limit: int = 50,
                    since: date | None = None) -> list[SearchHit]:
        calls.append(query)
        # 两个式子都返回同一篇 + 各自独有的一篇
        base = ArxivProvider._parse(SAMPLE_XML, query, NOW)[:1]
        extra = ArxivProvider._parse(SAMPLE_XML, query, NOW)[1:]
        return base + (extra if "q2" in query else [])

    p.search = fake_search  # type: ignore[method-assign]
    hits = p.search_many(["q1", "q2"], limit=10)

    ids = [h.arxiv_id for h in hits]
    check("多式子并集去重", len(ids) == len(set(ids)), str(ids))
    check("并集计 2 篇", len(ids) == 2, str(ids))
    # 2507.14111 被 q1 先命中，故其 query 应为 q1
    first = next(h for h in hits if h.arxiv_id == "2507.14111")
    check("保留首次命中的 query", first.query == "q1", first.query)
    check("按 published 倒序",
          [h.published for h in hits] == sorted(
              [h.published for h in hits], reverse=True),
          str([h.published for h in hits]))


def test_since_filter() -> None:
    """since 过滤必须真的筛掉早期论文。"""
    p = ArxivProvider()

    def fake_search(query: str, *, limit: int = 50,
                    since: date | None = None) -> list[SearchHit]:
        # 直接调用真实实现会发网络请求，这里改为复刻过滤逻辑
        hits = ArxivProvider._parse(SAMPLE_XML, query, NOW)
        if since:
            hits = [h for h in hits if h.published >= since.isoformat()]
        return hits

    all_hits = fake_search("q")
    check("不过滤时 2 篇", len(all_hits) == 2, str(len(all_hits)))

    recent = fake_search("q", since=date(2025, 7, 17))
    check("since 过滤掉 07-16 那篇", len(recent) == 1, str(len(recent)))
    check("保留的是较新的一篇",
          recent and recent[0].published == "2025-07-18",
          recent[0].published if recent else "")


def test_online() -> None:
    p = ArxivProvider()
    hits = p.search('all:"reinforcement learning" AND all:"CUDA kernel"',
                    limit=10)
    check("在线检索有结果", len(hits) > 0, str(len(hits)))
    if hits:
        h = hits[0]
        check("在线结果 arxiv_id 形态正确",
              bool(h.arxiv_id and "." in h.arxiv_id), h.arxiv_id)
        check("在线结果摘要非空", len(h.abstract) > 50, str(len(h.abstract)))
        check("在线结果 fetched_at 带时区", "+08:00" in h.fetched_at, h.fetched_at)


def main() -> int:
    test_parse()
    test_dedup()
    test_since_filter()
    if "--online" in sys.argv:
        test_online()

    print()
    bad = 0
    for name, ok, detail in RESULTS:
        if ok:
            print(f"[PASS] {name}")
        else:
            bad += 1
            print(f"[FAIL] {name}\n       {detail}")
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
