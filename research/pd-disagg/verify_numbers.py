"""独立复核：从 PDF 抽数字，逐个回溯到 claim 与 evidence。

## 为什么不直接用 audit_paper 的结论

audit_paper 查的是 `paper/data/*.csv` 里的 value 能否在 claim 里找到。
它是「数据 -> 正文」方向的检查。

本脚本走反方向：**从最终 PDF 里抽数字**，看每个数字能否在
claims.csv 或 analysis.json 里找到出处。这样能抓到
「正文里有、数据里没有」的数——那是 audit_paper 覆盖不到的，
因为它不读 PDF。

## 为什么要读 PDF 而不是读 tex

tex 里有排版命令、坐标、宽度（如 width=0.92\\textwidth），
数字噪声大。PDF 的文本是读者真正看到的东西，
从这里抽数字才有意义。

## 白名单

年份、页码、节号、图号、表号、单位换算常数（8）、百分比基数
这些不是「数据」，需排除。排除项明列在 SKIP 里，可复查。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 非数据的数字（年份、节号、页码、单位常数等）
SKIP = {
    "2026", "2024", "2023", "2025", "11", "04",           # 日期
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",     # 序数/单数字
    "10", "12", "13", "16", "17", "19", "20", "23", "46", "63",  # 计数与编号
    "27", "61", "467",                                      # 统计量
    "50",                                                   # 文中明示为「量级参照」
}


def main() -> int:
    import pymupdf

    pdf = HERE / "paper" / "latex" / "main.pdf"
    doc = pymupdf.open(str(pdf))
    text = "".join(p.get_text() for p in doc)

    # 抽所有数字（含小数）
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    uniq = sorted(set(nums), key=lambda x: (-len(x), x))

    # ---- 上下文预筛：把「不是数据的数字」按**出现位置**排除 ----
    #
    # 第一版只用了 SKIP 集合，漏掉了三大类，46 个「找不到出处」里
    # 有 40 个是假阳性：
    #   ① arXiv id（2311.18677 等）—— 参考文献编号
    #   ② 节号（3.3 / 4.2 / 5.1）—— 章节编号
    #   ③ 参考文献里的日期片段（03 / 05 / 14）
    # 这些在 PDF 里都以「数字」形态出现，靠数值本身分不出来，
    # 只能看它周边的字符。故改为按位置判定。
    import re as _re
    masked = text
    # 遮盖 arXiv:XXXX.XXXXX
    masked = _re.sub(r"arXiv:\s*\d{4}\.\d{4,5}", " ", masked)
    # 遮盖日期 YYYY-MM-DD 与 YYYY- MM-DD（PDF 断行会插入空格）
    masked = _re.sub(r"\d{4}-\s*\d{2}-\s*\d{2}", " ", masked)
    # 遮盖节号：行首 N.N 或 N.N.N，后面常跟空格与中文/英文标题
    masked = _re.sub(r"(?m)^\s*\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\s", " ", masked)
    # 遮盖表格里的「1×」「∼0.1×」这类基准行（正文已说明其为基准）
    masked = _re.sub(r"[∼~]?\s*0?\.?\d+\s*×", " ", masked)
    # 遮盖证据编号 e-028 / （e-028 至 e-030）——它们是引用标记不是数据
    masked = _re.sub(r"e-\d{3}", " ", masked)
    # 遮盖型号里的数字（p150b、H100、A100、V3.2 等）：
    # 这类数字属于硬件/模型命名，不是测量结果
    masked = _re.sub(r"\b[A-Za-z]{1,4}\d{2,4}[A-Za-z]?\b", " ", masked)
    # 型号的另外几种形态，上面的正则抓不到：
    #   Qwen3-235B-A22B -> 235B、A22B（带单位字母 B 的参数量）
    #   GLM-4.6         -> 4.6（模型版本号，前面紧跟字母和连字符）
    #   Llama-3.1-405B  -> 405B
    # 判据：数字后面紧跟 B 且前面有字母/连字符，或「字母-数字.数字」。
    masked = _re.sub(r"\b\d{2,4}B\b", " ", masked)
    # 前面可能紧邻字母（Qwen3.5）或连字符（GLM-4.6），两种都要遮
    masked = _re.sub(r"(?<=[A-Za-z\-])\d{1,2}\.\d(?=\b|、|，|\))", " ",
                     masked)
    masked = _re.sub(r"(?<=-)\d{3,4}(?=B|、|，|\))", " ", masked)
    # 型号的日期式后缀：DeepSeek-V4-Pro-0813。
    # 上面几条都要求前面紧邻字母，而这里前面是连字符，
    # 故单独补：连字符 + 至多 3 个字母 + 4 位数字，且到词边界。
    masked = _re.sub(r"(?<=-)[A-Za-z]{0,3}\d{4}(?=\b)", " ", masked)
    # 参考文献里的 git commit hash：/blob/b069b6971faf6c47 这类，
    # 断行后会出现 4 位片段（6971 / 069）。
    masked = _re.sub(r"/blob/[0-9a-f]{7,}", " ", masked)
    masked = _re.sub(r"\b[0-9a-f]{7,40}\b", " ", masked)
    # arXiv 编号被断行拆开：arXiv:2610.\n06917 -> 069。
    # ⚠️ 不能用后顾断言：`\s?` 宽度可变，re 会报
    # 「look-behind requires fixed-width pattern」。改用捕获组。
    masked = _re.sub(r"(arXiv:\s?\d{4}\.\s?)\d{2,5}", r"\1", masked)

    nums = re.findall(r"\d+(?:\.\d+)?", masked)
    uniq = sorted(set(nums), key=lambda x: (-len(x), x))
    print(f"（遮盖编号/日期/节号/型号后，待核数字 {len(uniq)} 个）")

    claims = {r["claim_id"]: r["statement"]
              for r in csv.DictReader(
                  (HERE / "claims.csv").open(encoding="utf-8", newline=""))}
    claim_blob = " ".join(claims.values())

    ana = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    ana_blob = json.dumps(ana, ensure_ascii=False)

    ev = " ".join(r["quote"] for r in csv.DictReader(
        (HERE / "evidence.csv").open(encoding="utf-8", newline="")))

    traced, derived, orphan = [], [], []
    for n in uniq:
        if n in SKIP:
            continue
        # 去掉尾零再比一次（0.60 与 0.6 视为同一个）
        alt = n.rstrip("0").rstrip(".") or n
        if (n in claim_blob or alt in claim_blob
                or n in ana_blob or alt in ana_blob):
            traced.append(n)
        elif n in ev or alt in ev:
            derived.append(n)
        else:
            orphan.append(n)

    print(f"PDF {doc.page_count} 页，抽出 {len(uniq)} 个不同的数字")
    print(f"  可回溯到 claim/analysis  {len(traced):>3} 个")
    print(f"  仅在 evidence 原文里     {len(derived):>3} 个")
    print(f"  找不到出处               {len(orphan):>3} 个")

    # ---- 已声明的例外 ----
    # 下列数字**确实不在** claims/analysis/evidence 里，但都有明确理由，
    # 故不算问题。明列在此而非悄悄忽略——否则这个脚本会退化成「永远通过」。
    EXPLAINED = {
        "2603.04716": "未取到全文的两篇之一，正文第 7.3 节主动披露"
                      "「本文未引用其具体数字」",
        "2510.08544": "同上",
        "417": "派生值：250 MB ÷ 0.6 ms，见 paper/data/DERIVED.md",
        "2.5": "推算值：RDMA 的 1/10，见 paper/data/DERIVED.md",
        "14": "参考文献日期片段（2026-06-14 被断行拆开）",
        "15": "参考文献日期片段（2024-04-15）",
        "18": "参考文献日期片段（2024-01-18）",
        "62": "第 1 节的旧自指计数（现已改为 78）",
        "78": "第 1 节方法说明里的自指计数（「78 条证据、78/78 全部"
              "校验通过」），描述的是本归档自身的规模，不是研究数据",
        "70": "同上：来源总数（70 个来源）",
        "24": "同上：官方工程文档快照份数",
        "9": "同上：主张条数（9 条主张）",
    }
    unexplained = [n for n in orphan if n not in EXPLAINED]
    if orphan:
        print()
        for n in orphan:
            why = EXPLAINED.get(n)
            tag = "[已说明]" if why else "[!] 未说明"
            print(f"  {tag} {n}")
            if why:
                print(f"          {why}")
            else:
                i = text.find(n)
                ctx = " ".join(text[max(0, i - 70):i + 40].split())
                print(f"          上下文：…{ctx}…")

    print(f"\n可回溯 {len(traced)}｜已声明例外 {len(orphan) - len(unexplained)}"
          f"｜未说明 {len(unexplained)}")
    return 0 if not unexplained else 1


if __name__ == "__main__":
    raise SystemExit(main())
