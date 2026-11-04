"""arXiv 检索适配器：`services/providers` 的第一个真实实现。

## 为什么现在做

做「CUDA kernel 强化学习」专题时，起点不是「我知道有哪些论文」，
而是「这个方向有哪些论文」。可框架只有 `fetch_papers.py`（按已知 ID 批量取），
没有按关键词检索的能力。于是每个新专题都得自己写一份抓取脚本——
`cuda-kernel-gcn/paper/fetch_rl.py` 就是第二份重复。

这是典型的「容量增长落在框架外」。故把检索逻辑收回 `services/providers`。

## 与 README 契约的对应

README 定义：

    class SearchProvider(Protocol):
        def search(self, query: str, *, limit: int, since: date | None) -> list[SearchHit]

本模块实现 `ArxivProvider.search`，返回 `SearchHit`。
`since` 映射为 arXiv 的 `submittedDate` 下限过滤（在本地做，API 的
日期过滤语法不稳，且不同镜像行为不一致）。

## 关于「多 query 合并」

单一 search_query 只能表达一个布尔式。做专题检索时需要多组式子的并集
（例如同时搜 "reinforcement learning" AND "CUDA kernel"、
GRPO AND kernel），否则会漏。故提供 `search_many`。
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

import requests

API = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}
TZ = timezone(timedelta(hours=8))

# arXiv 官方对脚本的请求频率要求约 3 秒一次。
# 这不是保守，是硬要求：低于此值会收到 429 并可能被临时封禁。
MIN_INTERVAL = 3.2


@dataclass(frozen=True)
class SearchHit:
    """一条检索命中。字段对应 Atom entry，已做空白归一。"""
    source_id: str
    arxiv_id: str
    title: str
    authors: list[str]
    published: str
    updated: str
    abstract: str
    url: str
    query: str = ""            # 由哪个检索式命中，便于回溯召回率
    fetched_at: str = field(default="")


class ProviderError(RuntimeError):
    pass


class ArxivProvider:
    """arXiv 检索适配器。

    用法：
        p = ArxivProvider()
        hits = p.search('all:"reinforcement learning" AND all:"CUDA kernel"',
                        limit=50)
        hits = p.search_many([q1, q2, q3], limit=100)   # 并集去重
    """

    name = "arxiv"

    def __init__(self, *, min_interval: float = MIN_INTERVAL,
                 timeout: int = 40, max_retries: int = 3) -> None:
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_call = 0.0

    # ------------------------------------------------------------ 内部
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()

    def _get(self, params: dict) -> str:
        last: Exception | None = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                r = requests.get(API, params=params, timeout=self.timeout)
                if r.status_code == 429:
                    # 退避而不是立刻重试：立刻重试只会继续被拒
                    time.sleep(10 * (attempt + 1))
                    last = ProviderError("429 rate limited")
                    continue
                r.raise_for_status()
                return r.text
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep(5 * (attempt + 1))
        raise ProviderError(f"arXiv 请求失败：{last}")

    @staticmethod
    def _parse(xml: str, query: str, now: str) -> list[SearchHit]:
        root = ET.fromstring(xml)
        out: list[SearchHit] = []
        for e in root.findall("a:entry", NS):
            raw = (e.find("a:id", NS).text or "").strip()
            m = re.search(r"(\d{4}\.\d{4,5})", raw)
            if not m:
                continue
            aid = m.group(1)
            out.append(SearchHit(
                source_id="src-arxiv-" + aid.replace(".", "-"),
                arxiv_id=aid,
                title=" ".join((e.find("a:title", NS).text or "").split()),
                authors=[a.find("a:name", NS).text
                         for a in e.findall("a:author", NS)][:8],
                published=(e.find("a:published", NS).text or "")[:10],
                updated=(e.find("a:updated", NS).text or "")[:10],
                abstract=" ".join((e.find("a:summary", NS).text or "").split()),
                url=f"https://arxiv.org/abs/{aid}",
                query=query,
                fetched_at=now,
            ))
        return out

    # ------------------------------------------------------------ 公开
    def search(self, query: str, *, limit: int = 50,
               since: date | None = None) -> list[SearchHit]:
        now = datetime.now(TZ).replace(microsecond=0).isoformat()
        params = {
            "search_query": query,
            "start": 0,
            # since 过滤在本地做，故多取一些再截断
            "max_results": min(limit * 2 if since else limit, 200),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        hits = self._parse(self._get(params), query, now)
        if since:
            cutoff = since.isoformat()
            hits = [h for h in hits if h.published >= cutoff]
        return hits[:limit]

    def search_many(self, queries: Iterable[str], *, limit: int = 50,
                    since: date | None = None) -> list[SearchHit]:
        """多组检索式的并集去重。

        保留首次命中的 query 字段——它记录了这篇是被哪条式子召回的，
        对评估「检索式是否够全」有用（全被单一式子命中说明其余是冗余）。
        """
        seen: dict[str, SearchHit] = {}
        for q in queries:
            for h in self.search(q, limit=limit, since=since):
                seen.setdefault(h.arxiv_id, h)
        return sorted(seen.values(), key=lambda h: h.published, reverse=True)


def hits_to_records(hits: Iterable[SearchHit]) -> list[dict]:
    """转成与 `papers.json` 一致的记录格式，便于合并进既有研究。"""
    return [{
        "id": h.arxiv_id,
        "title": h.title,
        "authors": h.authors,
        "published": h.published,
        "updated": h.updated,
        "abstract": h.abstract,
        "arxiv_url": h.url,
        "query": h.query,
        "fetched_at": h.fetched_at,
    } for h in hits]
