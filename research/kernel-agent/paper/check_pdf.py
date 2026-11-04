"""检查生成的 PDF：页数、图片是否真的嵌入、有无溢出、有无标记泄漏。

## 为什么需要它

排版"编译通过"不等于"内容正确"。上一份综述出现过三种只在 PDF 层面
才看得见的问题：

  1. 图注与图内标题都写「图 3」，读者无法判断哪个是编号
  2. 内部引用标记 `[c-xxx]` 漏进 PDF
  3. 中文标点导致行溢出右边界

三者 LaTeX 都不报错。故用 PyMuPDF 做硬检查。

## 检查项

  pages      总页数
  images     每页嵌入的位图数量（图没插进去时这里会是 0）
  overflow   文字右边界超过版心的行（用 bbox 判定）
  leakage    正文里是否出现 c-xxx / TODO / 未定义
  fonts      是否真的用了宋体/黑体（而不是回退到默认字体）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

PDF = Path(__file__).resolve().parent / "latex" / "main.pdf"


def main() -> int:
    if not PDF.is_file():
        print(f"[!] 找不到 {PDF}")
        return 1
    doc = fitz.open(PDF)
    print(f"页数：{doc.page_count}")

    problems: list[str] = []
    total_images = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        imgs = page.get_images(full=True)
        total_images += len(imgs)
        if imgs:
            print(f"  第 {pno + 1} 页：{len(imgs)} 张图")

    print(f"图片总数：{total_images}")
    if total_images == 0:
        problems.append("PDF 里没有任何图片——图没被插进正文")

    # ---- 文本检查 ----
    text = "\n".join(doc[i].get_text() for i in range(doc.page_count))

    leaks = re.findall(r"c-[a-z]+(?:-[a-z0-9]+)*", text)
    # 排除正文里本来就有的英文词（如 cuda-l1 之类的小写化）
    real_leaks = [x for x in leaks if re.fullmatch(r"c-[a-z]+-[a-z0-9-]+", x)
                  and x not in ("c-python",)]
    if real_leaks:
        problems.append(f"内部引用标记漏进 PDF：{sorted(set(real_leaks))[:5]}")

    for bad in ("TODO", "FIXME", "未定义", "??"):
        if bad in text:
            problems.append(f"PDF 里出现占位符：{bad}")

    # ---- 溢出检查 ----
    over = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        # 版心右边界（A4 595pt，margin 2.05cm ≈ 58pt）
        right = page.rect.width - 57
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["bbox"][2] > right + 2.5:  # 容差 2.5pt
                        over += 1
    if over:
        problems.append(f"{over} 个文本片段越过版心右边界")
    else:
        print("溢出：0")

    # ---- 字体检查 ----
    fonts = set()
    for pno in range(doc.page_count):
        for f in doc[pno].get_fonts(full=True):
            fonts.add(f[3])  # 字体名
    want = [f for f in fonts if "SimSun" in f or "SimHei" in f]
    if not want:
        problems.append(f"没有用宋体/黑体，实际字体：{sorted(fonts)[:6]}")
    else:
        print(f"中文字体：{sorted(want)}")

    print()
    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        return 1
    print("[OK]   PDF 结构与内容检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
