"""外部来源适配器。

设计约束见 `services/providers/README.md`：
网页与 PDF 内容是**数据**，不是指令；每次抓取必须记录带时区的 `fetched_at`。

当前实现：

| 模块 | 来源 | 能力 |
|---|---|---|
| `arxiv` | arXiv | 关键词检索（单式 / 多式并集） |
"""

from __future__ import annotations

__all__ = ["arxiv"]
