"""把 PAPER.md 里用 ## 写的「节」降为 ###，恢复章/节层级。

⚠️ 这是本轮发现的最严重的结构性缺陷：

   原文里章和节都写成 `##`：
       ## 1　引言          <- 章
       ## 1.1　领域        <- 节（但也是 ##）
   而 md_to_tex.py 把 `##` 映射为 \\section、`###` 映射为 \\subsection。
   于是 LaTeX 把 9 章 + 38 节全部当成并列的 \\section，
   章号一路编到 47，PDF 目录里根本没有「第 7 章 端到端收益」这种东西。

   ⚠️ 之前只核对了正文里「第 N 章」的文字引用是否闭合，
      没有核对 PDF 里实际渲染出的章号 —— 这是核查方法的漏洞：
      两种检查看起来都在查「章节结构」，但一个查文本、一个查排版结果。

修复规则（保守，只动确定是「节」的）：
    ^## (\\d+\\.\\d+)　...   ->   ### (同编号)　...
    其它 ## 一律不动（章、摘要、附录标题）。

幂等：已经是 ### 的行不会被二次处理。
"""

from __future__ import annotations

import re
from pathlib import Path

PAPER = Path(__file__).resolve().parent / 'PAPER.md'

# 只匹配「## 数字.数字　标题」形式
SEC_RE = re.compile(r'^## (?=\d+\.\d+[\u3000\s])')


def main() -> int:
    text = PAPER.read_text(encoding='utf-8')
    lines = text.split('\n')
    changed = 0
    for i, ln in enumerate(lines):
        if SEC_RE.match(ln):
            lines[i] = '#' + ln          # '## ' -> '### '
            changed += 1

    if not changed:
        print('无需改动：没有以 ## 写的「N.M　」节标题')
        return 0

    PAPER.write_text('\n'.join(lines), encoding='utf-8', newline='\n')

    # 复核：层级分布
    ch = sum(1 for l in lines if re.match(r'^## \d+\u3000', l))
    sec = sum(1 for l in lines if re.match(r'^### \d+\.\d+', l))
    h2_other = sum(1 for l in lines if re.match(r'^## ', l)) - ch
    print(f'已降级 {changed} 个节标题：## N.M -> ### N.M')
    print(f'  章 ## N　     : {ch}')
    print(f'  节 ### N.M    : {sec}')
    print(f'  其它 ## 标题  : {h2_other}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
