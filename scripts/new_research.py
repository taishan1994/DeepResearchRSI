#!/usr/bin/env python
"""从模板生成一份新的研究任务骨架。

用法:
    python scripts/new_research.py --slug rtx-pro-6000 --question "……"

生成 research/<slug>/ 下的 brief.yaml、sources.csv、evidence.csv、claims.csv、REPORT.md
以及 notes/ 目录，字段与 docs/data-model.md 一致。
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "research" / "_template"

BRIEF_TMPL = """\
# 研究简报 —— {slug}
question: "{question}"
scope:
  topic: "{topic}"
  region: global
  language: zh-en
  time_range: ""
as_of: {today}
freshness: 30d
deliverable: deep_analysis
constraints:
  source_priority: [official, academic, review, community, press]
  citation_style: inline_markdown
  depth: deep
  budget:
    max_tool_calls: 120
    max_minutes: 40
exclusions: []
subquestions:
  - id: q1
    question: ""
    expected_evidence: "一手规格页、官方博客或数据手册"
    done_when: "至少一条 primary 来源直接支持"
    status: unanswered
"""

SOURCES_HEADER = "source_id,url,source_type,publisher,title,published_at,updated_at,fetched_at,language,trust_tier,access,license,notes\n"
EVIDENCE_HEADER = "evidence_id,document_id,source_id,quote,locator,stance,extracted_by\n"
CLAIMS_HEADER = "claim_id,statement,claim_type,as_of,confidence,evidence_ids,counter_evidence_ids,derivation,notes\n"

REPORT_TMPL = """\
# {title}

> 状态：草稿
> 信息截止：{today}
> 来源数：0 ｜ 证据数：0 ｜ 主张数：0

## 1. 执行摘要

（待补）

## 2. 范围与方法

（待补）

## 3. 主体分析

（待补）

## 4. 争议与证据缺口

（待补）

## 5. 参考文献
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--topic", default="")
    args = ap.parse_args()

    target = ROOT / "research" / args.slug
    if target.exists():
        print(f"目录已存在，未覆盖: {target}")
        return 1

    (target / "notes").mkdir(parents=True)
    today = date.today().isoformat()

    (target / "brief.yaml").write_text(
        BRIEF_TMPL.format(
            slug=args.slug,
            question=args.question,
            topic=args.topic or args.slug,
            today=today,
        ),
        encoding="utf-8",
    )
    (target / "sources.csv").write_text(SOURCES_HEADER, encoding="utf-8")
    (target / "evidence.csv").write_text(EVIDENCE_HEADER, encoding="utf-8")
    (target / "claims.csv").write_text(CLAIMS_HEADER, encoding="utf-8")
    (target / "REPORT.md").write_text(
        REPORT_TMPL.format(title=args.title or args.slug, today=today), encoding="utf-8"
    )

    print(f"已生成 {target.relative_to(ROOT)}")
    print("下一步：填充 brief.yaml 的子问题 → 采集来源 → 抽取证据 → 写报告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
