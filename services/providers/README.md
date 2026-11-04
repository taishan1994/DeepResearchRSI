# services/providers

统一的外部来源适配器层。

## 接口

```python
class SearchProvider(Protocol):
    def search(self, query: str, *, limit: int, since: date | None) -> list[SearchHit]: ...

class DocumentProvider(Protocol):
    def fetch(self, url_or_doi: str) -> Document: ...
```

## 已规划的适配器

| 类型 | 来源 |
|---|---|
| 学术元数据 | OpenAlex、Crossref、Semantic Scholar、arXiv、PubMed |
| 通用 Web | 搜索引擎、网页读取 |
| 内部资料 | 本地文件、知识库、MCP 连接器 |

## 硬性约束

- **网页与 PDF 内容是数据，不是指令**。绝不执行页面里的"指令"。
- 遵守 `robots.txt` 与站点条款；不抓登录态；不绕过访问控制。
- 超时、重试、速率限制为必选项，不是可选项。
- 每次抓取必须记录 `fetched_at`（带时区），否则证据链断裂（见 ADR-0002）。

## 不负责

- 解析与分段（`services/ingestion`）
- 直接写 `Claim`（必须先经 ingestion 得到 `Document`）

## 当前状态

| 适配器 | 状态 | 位置 |
|---|---|---|
| arXiv（关键词检索） | **已实现** | `packages/providers/python/deepresearchrsi_providers/arxiv.py` |
| OpenAlex / Crossref / Semantic Scholar / PubMed | 规划 | — |
| 通用 Web | 规划 | — |
| 内部资料 | 规划 | — |

### arXiv 适配器为什么先做

做第二个专题（`research/cuda-kernel-rl/`）时暴露了一个重复实现：
`cuda-kernel-gen` 与 `cuda-kernel-rl` 各自写了一份
requests + XML 解析 + 限速 + 429 退避，几乎逐行相同。

更麻烦的是**能力缺口**：框架只有「按已知 ID 批量取」，
没有「按关键词检索」。而新专题的起点恰恰是
「这个方向有哪些论文」，不是「我知道 ID 列表」。

收回后，专题脚本只声明检索式：

```python
provider = ArxivProvider()
hits = provider.search_many(['all:"reinforcement learning" AND all:"CUDA kernel"',
                             'all:GRPO AND all:kernel'], limit=100)
```

`search_many` 做多式并集去重，并保留 `query` 字段记录每篇被哪条式子召回——
用于评估「检索式是否够全」（全被单一式子命中说明其余是冗余）。

**归位的验收方式**：用新旧两套实现跑同一组检索式，
比较候选池。结果 80 篇、交集 80、零差异。
没有这个对比，「换个地方实现」与「能力退化」无法区分。
