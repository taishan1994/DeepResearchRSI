"""抓取「8x RTX PRO 6000 上真跑 V4.1-Flash」的现场报告。

这两个 issue 是全网唯一两组「在目标硬件上端到端跑通并给出实测」的一手记录：
  - vLLM #56700：8x RTX PRO 6000，1M 上下文验证
  - SGLang #40877：8x RTX PRO 6000（PCIe，无 NVLink），实测吞吐与被否掉的拓扑
另加 diffbot 的 EXL3 3bpw 量化卡（2x RTX PRO 6000）作为「装不下时怎么办」的对照。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "packages" / "schemas" / "python"))
from deepresearchrsi.invariants import write_snapshot  # noqa: E402


def gh_issue_text(repo: str, num: int) -> str:
    """拼出 issue 正文 + 全部评论的纯文本。

    ⚠️ 走 api.github.com 会撞 403 限流（实测），故改走 html 页面并用
       fetch 的正文抽取。GitHub issue 页是服务端渲染的，正文可读。
    """
    return fetch(f"https://github.com/{repo}/issues/{num}")


TARGETS = [
    ("src-vllm-56700", "doc-vllm-56700", "vllm-56700",
     lambda: gh_issue_text("vllm-project/vllm", 56700)),
    ("src-sglang-40877", "doc-sglang-40877", "sglang-40877",
     lambda: gh_issue_text("sgl-project/sglang", 40877)),
    ("src-diffbot-exl3", "doc-diffbot-exl3", "diffbot-exl3",
     lambda: fetch("https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-"
                   "RTX-PRO-6000/raw/main/recipe/README.md")),
    ("src-r6k-r38", "doc-r6k-r38", "r6k-r38",
     lambda: fetch("https://raw.githubusercontent.com/local-inference-lab/"
                   "rtx6kpro/master/models/deepseek-v4.1-flash-community-r38.md")),
]


def main(argv: list[str]) -> int:
    only = set(argv)
    for sid, did, stem, getter in TARGETS:
        if only and sid not in only:
            continue
        dest = ROOT / "documents" / f"{stem}.txt"
        if dest.is_file() and dest.stat().st_size > 1500 and not only:
            print(f"[skip] {stem} 已存在 {dest.stat().st_size} B")
            continue
        try:
            text = getter()
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {sid}: {type(exc).__name__}: {exc}")
            continue
        print(f"[OK]   {sid}: {len(text):,} 字符")
        write_snapshot(ROOT, did, text, source_id=sid,
                       parser_version="fetch6.py/1", variant="")
        _ = json  # 保留 import，供后续需要时改用 API
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
