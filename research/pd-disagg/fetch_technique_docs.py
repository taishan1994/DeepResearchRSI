"""抓取「优化技巧」一层的权威文档快照。

## 为什么要补这一批

第 1 轮论文把「技术」理解成架构层（传输 / 切分），漏掉了
**具体的优化技巧**这一整层。用户指出后重新检索，语料里实际浮现出
22 个技巧词（TBO 47 篇命中、chunked prefill 28、prefix cache 21、
speculative 20、piggyback 17、layerwise 7、KV reshard 1 ...）。

这些技巧大多不在 arXiv 论文里，而在框架官方文档与工程博客里，
故单独抓。

## 抓哪些

只抓「能给出机制细节与实测数字」的一手材料：
  · SGLang EP 文档      -> TBO / SBO 的官方定义
  · NVIDIA+SGLang 博客  -> Waterfill / LPLB，含逐数据集实测表
  · vLLM DBO 设计文档    -> DBO 的调度图与启用条件
  · vLLM DSpark 博客     -> 自适应验证的动机、成本模型与限制

不抓二手综述：技巧的机制细节在转述中最容易失真。

## 为什么要去标签

文档站是 SPA，正文混在大量 <script>/<style> 与导航里。
不去标签则快照里 90% 是导航文字，取引文时会取到菜单项。
"""

from __future__ import annotations

import re

import requests

from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

TARGETS = {
    "sglang-waterfill-lplb": (
        "https://raw.githubusercontent.com/bojieli/ai-infra-book/"
        "b069b6971faf6c4701b57a8b025462b9f2694b8f/references/"
        "framework-history/2026-09-08/ep-reconfiguration/"
        "sglang-waterfill-lplb-2026.md"
    ),
    "vllm-dbo": (
        "https://raw.githubusercontent.com/vllm-project/vllm/main/"
        "docs/design/dbo.md"
    ),
    "vllm-dspark": "https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification",
}


def strip_html(h: str) -> str:
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h)
    t = re.sub(r"&[a-z]+;|&#\d+;", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    for name, url in TARGETS.items():
        r = requests.get(url, timeout=40)
        print(f"{name}: HTTP {r.status_code} {len(r.text):,} 字符")
        if r.status_code != 200:
            print("  [!] 抓取失败")
            continue
        text = strip_html(r.text) if "<html" in r.text[:600].lower() else (
            r.text)
        p = DOCS / f"{name}.txt"
        p.write_text(text, encoding="utf-8", newline="\n")
        print(f"  -> {p.name}  {len(text):,} 字符")

        # 校验：关键术语确实在快照里（否则后续取引文必然失败）
        for probe in ("Waterfill", "LPLB", "TBO", "SBO", "DBO",
                      "speculative", "concurrency", "overlap"):
            n = text.count(probe)
            if n:
                print(f"     {probe:<14} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
