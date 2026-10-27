# scripts/ — 本地开发工具

不承担研究逻辑，只做**校验、生成与导出**。所有脚本都是单文件、零第三方依赖、可直接 `python scripts/xxx.py` 运行。

## 公开脚本

### `new_research.py` — 脚手架

```bash
python scripts/new_research.py --slug <slug> --question "<研究问题>" [--title "<标题>"] [--topic "<主题>"]
```

例：

```bash
python scripts/new_research.py --slug rtx-pro-6000 --question "RTX PRO 6000 的性能到底如何？" --title "RTX PRO 6000 性能分析"
```

生成 `research/<slug>/`：`brief.yaml`（含 `q1` 子问题骨架）、`sources.csv`、`evidence.csv`、`claims.csv`（均含表头）、`REPORT.md`、`notes/` 空目录。

用途：让新研究从第一秒就满足 S1/D1/E1/C1/C2/R1 等不变量，而不是事后补齐。

### `validate_research.py` — 归档自洽性校验

```bash
python scripts/validate_research.py research/rtx-pro-6000   # 单个
python scripts/validate_research.py research/*              # 全部
python scripts/validate_research.py                         # 默认 research/ 下所有子目录
```

委托给 `packages/schemas/python/deepresearchrsi/validate.py`，检查：

| 类别 | 检查项 |
|---|---|
| ID | `src-` / `e-` / `c-` 前缀，各表内唯一 |
| 来源 | `url` 非空、`fetched_at` 非空（**S1**）、`published_at` 可解析、`source_type` 与 `trust_tier` 枚举合法 |
| 证据 | `quote` 非空（**E1**）、`source_id` 存在 |
| 主张 | 至少一条 `evidence_ids`、引用可解析、`prediction` 必须带 `derivation`（**C2**） |
| 报告 | `REPORT.md` 中 `[c-*]` / `[e-*]` 引用不得悬空 |

退出码：全通过为 `0`，任一失败为 `1`。

## 内部工具（下划线前缀）

以下脚本是**操作性工具**，不保证接口稳定，主要服务于人工/代理批量写归档。

### `_append_csv.py` — 安全追加

```bash
python scripts/_append_csv.py <目标.csv> <新增行.csv>
```

**为什么存在**：直接用 `csv.DictWriter` 或字符串拼接写这些 CSV 时，一旦某行列数不对（常见原因：中文引号里的 ASCII 逗号、英寸符号 `"`），会在写入中途抛错并把目标文件**截断**——本项目历史上真实发生过一次数据丢失。

本脚本的做法：先读 `utf-8-sig`，**逐行校验列数必须等于目标表头列数**，全部通过后才写 `.tmp` 再用 `Path.replace()` 原子替换。任何一行不合规就整体中止，目标文件不变。

### `_repair_csv.py` — 列错位修复

```bash
python scripts/_repair_csv.py <目标.csv>
```

处理英寸符号（如 `5.4 H x 12.0" L`）导致的列错位，把会造成歧义的 ASCII `"` 替换为 `″`（U+2033）后重新对齐。

## 约定

- **不要**用 `csv.DictWriter` 写 `sources.csv` / `evidence.csv` / `claims.csv`——必须用 `_append_csv.py`。
- 写 CSV 时统一 `quoting=csv.QUOTE_ALL, lineterminator="\n"`，编码 `utf-8-sig`。
- 脚本报错时**不要**用 `git checkout -- <csv>` 回滚：会把未提交的相邻工作一起丢掉。先 `git status` 确认范围。
- 本目录是工具，**不属于研究产物**。提交时 `git add research/`（或明确路径），**不要** `git add scripts/`，否则会把临时草稿一起提交。
