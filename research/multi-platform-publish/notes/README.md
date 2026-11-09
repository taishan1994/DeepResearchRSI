# notes/ —— 过程笔记

本目录放**不进正式归档**的东西：探测脚本、失败的抓取记录、以及为什么放弃某个来源。

## 抓不到的东西（按 LESSONS 1.6，抓不到就不登记成来源）

| URL | 现象 | 处理 |
|---|---|---|
| `developer.zhihu.com/docs`（及 `/docs/index.md`、`/llms.txt`、`/docs.md`、`/robots.txt`） | 五个路径全部返回同一份 1,238 字节 SPA 外壳，正文 58 字 | 改用第三方转写本 `src-zhihu-api-ref`，相关主张一律 `medium` |
| `https://api.github.com/repos/wechatsync/Wechatsync` | 三轮均 `403 rate limit` | 改用 `raw.githubusercontent.com` 的 README；star 数未采信、未写入正文 |
| `https://open.xiaohongshu.com/home`、`/document` | SPA，正文抽取后仅 3 字符 | 改用其文档导航 JSON `/api/doc/list`（可直取） |
| `https://blog.csdn.net/` | `521` | 与本主题无关的平台页，放弃 |
| `https://www.jianmei.cn/` | `ReadTimeout` | 放弃；正文不依赖简媒 |
| 腾讯云那篇小红书 API 文章 | 正文需 JS 渲染，只取到「概述」（1,219 字符） | 登记为 `secondary`，**仅**用于「存在相反说法」，不用于任何事实断言 |

## 两个平台的取证路径差异（本主题最值得记的一条）

同一个研究里，知乎与小红书的结论强度不一样，原因不是谁更可信，而是**门户有没有留下可机读接口**：

- 小红书 `/api/doc/list` 是纯 JSON → 类目可穷举 → 「没有内容发布类目」是**可验证的否定判断**；
- 知乎门户是 SPA，没有 JSON 入口 → 只能依赖转写本 → 「没有发布接口」只能降为 `medium`。

否定性断言的成本远高于肯定性断言（LESSONS 1.7b）。本次的区别是：
**同样说「没有」，一个能穷举、一个只能转述。**

## 脚本

| 文件 | 作用 |
|---|---|
| `_probe_urls.py` | 早期批量 URL 探测（已用完，结论见上表）。留档是因为「哪些 URL 不可用」本身是可复用信息 |
| `check_anchors.py` | 在跑 `build_evidence.py` 之前，先确认每条锚点真的在快照里，避免一次失败的批量生成 |

正式的抓取与生成脚本在上一级目录：`fetch.py`（→ `documents/`）、
`build_evidence.py`（→ `evidence.csv`）、`build_claims.py`（→ `claims.csv`）。
三者都可重跑且幂等。
