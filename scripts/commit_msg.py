"""提交时写提交信息，避免 PowerShell 的 UTF-8 BOM 污染标题。

## 问题

`$msg | Out-File -Encoding utf8` 在 Windows PowerShell 里会写入 BOM
（EF BB BF）。`git commit -F` 会把它当成标题的第一个字符，于是
`git log --oneline` 显示 `﻿feat(framework): ...`，前面有个不可见字符。

不影响功能，但会污染历史，而且复制标题去搜索时匹配不上。

## 做法

用 Python 以 `encoding="utf-8"`（不带 BOM）+ `newline="\n"` 写文件，
再 `git commit -F`。顺带把「提交信息」与「提交动作」分开放，
省得每次在 PowerShell 里拼多行字符串。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".git" / "COMMIT_MSG_TMP.txt"

FRAMEWORK = """\
feat(framework): 证据不变量、provider 抽象与论文审计三件套

把三轮研究里反复踩到的坑固化成机制，而不是留在文档里。

## 证据不变量（invariants.py）

E1 引文可回溯：quote 必须是归档快照的原文子串。
  · 多快照匹配：同一 document_id 下摘要与全文都试，任一对上即可
  · relaxed() 归一化：LaTeXML 会把 26% 渲染成 $26\\%$，与 Atom API
    的 26% 对不上。不归一化会把 14 条正确引文全判成错
  · 判不了要报 e1_unverifiable，不能当成通过

S1 时间戳带时区、D1 一 document_id 一 content_hash。

## provider 抽象（packages/providers）

arXiv 检索从各归档的脚本里抽出来，统一限速与重试。
deepresearchrsi_providers.arxiv 提供 search_many()。

## 论文审计（audit_paper.py）

P1 引用闭合：正文 [c-xxx] 必须在 claims.csv 存在
P2 数值可回溯：data/*.csv 的 value 必须能在其 cite 指向的 claim 里找到
P3 无凭空图表：声明的产物必须真实存在

P2 的 cite 必须是 claim_id 而非 evidence_id——写错了会静默统计成 0，
看起来像「没有数值需要回溯」。

## 报告计数同步（sync_report_counts.py）

防静默漂移。此前一次 --slug 过滤把 rtx-pro-6000 的 447 条改写成 20 条，
已加回归测试 test_sync_report.py。

## 测试

test_schemas 26 项、test_invariants 12 项、test_audit_paper 7 项、
test_facets 7 项、test_providers_arxiv 25 项、test_sync_report 3 项。
"""

ARCHIVES = """\
docs(research): 收入 CUDA kernel 生成、强化学习与智能体三篇综述

三个归档共用一套「来源 → 证据 → 主张 → 论文」的管线，论文数字全部由
analysis.json 重算，不手写。

## cuda-kernel-gen（36 篇）

kernel 生成的方法谱系。核心判断：进展集中在生成质量，而评测口径
（fast_p）把正确性与加速比压成一个数，掩盖了两者的分离。

## cuda-kernel-rl（20 篇）

强化学习视角。核心判断：13 个核心工作里没有一个提出新的优化目标，
进展全在奖励设计。GRPO 的两个缺陷（自包含偏差、终局奖励稀疏）
被 kernel 生成同时触发。

## kernel-agent（35 篇）

智能体视角。核心判断：进展来自把更多真实环境信号接进循环，
而非更强的推理；把循环拆成五个环节逐一统计，跨三个及以上环节的
工作数为 0——即没有系统级设计。

## 方法上值得留档的三处失败

1. 自动筛选分不清「用 CUDA 加速」与「生成 CUDA kernel」——主语不同，
   词频无解。最后一层人判，判据固化成 decide_agent.py 可复查。
2. 证据抽取抓到论文题名与作者行。这些片段确实是原文子串，E1 全通过,
   但对论证零贡献。已加题名/作者区过滤。
3. check_references.py 把期望值写死成 20，35 条文献只报出 20 个编号。
   把期望值写进检查，检查的就成了「PDF 是否等于我以为的样子」。

## 验证

三归档 validate 全 OK（e1_unverifiable=0），audit_paper 全 OK，
论文 PDF：5 页 / 7 页 / 6 页，链接与 sources.csv 双向一致。
"""

MESSAGES = {"framework": FRAMEWORK, "archives": ARCHIVES}

TOOL = """\
chore(scripts): 加提交信息辅助脚本，避免 PowerShell 写入 BOM

Windows PowerShell 的 Out-File -Encoding utf8 会写 BOM（EF BB BF），
git commit -F 把它当成标题首字符，于是 git log --oneline 显示的
标题前有个不可见字符，复制去搜索也匹配不上。

本轮实际踩到：第一次提交的标题前面多了 BOM，
用 git reset --soft + 本脚本重写了一遍。

用 Python 以 utf-8（无 BOM）+ LF 写文件，再交给 git commit -F。
"""

MESSAGES["tool"] = TOOL

DOCS = """\
docs: 新增自我进化记录与经验手册，并给数字加校验

## 两份文档的分工

docs/EVOLUTION.md 回答「这个系统实际怎么变的」——按阶段记录触发了什么、
加了什么机制、代价是什么。是历史，只写发生过的。

docs/LESSONS.md 回答「这些经验能不能迁移」——上篇做项目的通用做法，
下篇自我改进的做法。每条都注明出处。

两份都有「三次没起作用」的章节：只记成功会失真。

## EVOLUTION 的核心事实

314 个提交、5 天、其中 64 个（20.4%）是在推翻自己上一轮的结论。
这个比例是最值得看的数：若长期接近 0，更可能的解释不是严谨，
而是没有检查。

五个阶段按「当时在解决什么问题」划分：
能产出但不可审计 → 读原始材料发现结论站不住 → 把教训变成不变量
→ 把检查器本身当代码测 → 把流程接进构建。

## 顺手核出一件必须写明的事

services/ 与 apps/ 下**只有 README，没有代码**（0 个 .py/.ts 文件）。
README 描述的是设计蓝图，真实运行的是 scripts/（3977 行非空）+
packages/（1039 行）+ tests/（1337 行）。

故 EVOLUTION.md 第 6 节明确写了这个差距，并说明「自我进化」是流程层面的
（人根据踩坑改脚本），不是系统自动搜索策略。services/evolution/ 是空壳。

## 新增校验

scripts/evolution_stats.py     从 git 历史算统计，写入 evolution-stats.json
scripts/check_docs.py          校验两份文档里的数字与实测一致（14 项）
scripts/selftest_check_docs.py 对 check_docs 做 4 个反例注入测试

## check_docs 自己踩的一个坑

第一版只验覆盖率自洽（e1_checked / 证据数），于是把表里的 e1_checked
改成任意值、同时改百分比与它自洽，检查照样通过——等于让文档自己
给自己作证。改为真正调 validate 取 e1_checked 后才抓得住。

反例验证时还踩了第二个坑：用 PowerShell here-string 做替换，反引号
被吞掉导致替换静默失败，我把「注入错误后仍通过」误读成检查器有漏洞。
改为 Python 文件后替换与断言同进程，替换失败会断言失败。
"""

MESSAGES["docs"] = DOCS


def main() -> int:
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    if key not in MESSAGES:
        print(f"[!] 未知提交类型：{key}（可选：{', '.join(MESSAGES)}）")
        return 1

    TMP.write_text(MESSAGES[key], encoding="utf-8", newline="\n")
    r = subprocess.run(["git", "commit", "-F", str(TMP)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(r.stdout.strip() or r.stderr.strip())
    TMP.unlink(missing_ok=True)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
