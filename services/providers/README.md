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

规范已定，实现待补（阶段 1）。
