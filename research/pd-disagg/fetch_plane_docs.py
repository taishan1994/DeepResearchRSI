"""抓取「四类之外」的权威材料。

## 为什么原来的四类不够

ABCD 是按「作用于 KV 传输成本的哪个环节」分的：
省量 / 隐藏 / 均衡 / 少步。这个维度只覆盖**分离带来的额外成本**。

但真实生产栈的优化面远大于此。vLLM 的大规模服务博客把优化分成
**三个平面**（数据面 / 执行面 / 控制面），其中至少五个维度
不落在我原来的分类里：

  · 并行策略选择      DEP / DCP / PCP / Wide-EP / TP
                      —— 不是「均衡负载」，是「选哪种切法」
  · 调度顺序          长 prefill 的 token 上限、prefill 节拍对齐
                      —— 不是「让传输不可见」，是「让队列不阻塞」
  · KV 池分层          分布式 KV cache pool、CPU/磁盘tier、
                      session-aware retention
                      —— 不是「省传输量」，是「扩大容量 + 提高命中」
  · kernel 与算子融合  DeepGEMM、SiLU fusion、GEMM+RS fusion、
                      对称内存、model-specific kernel
                      —— 完全不涉及传输，直接提升单步效率
  · 执行模式          CUDA graph FULL_AND_PIECEWISE、async scheduling
                      —— 消除 CPU 侧开销

## 三个必须记住的反例（来自 vLLM AgentX 博客的 bitter lessons）

1. **PP 不适合热的 agentic 轮次**：预热前缀的请求新增 token 太少，
   填不满流水线，bubble 吃掉收益。
2. **DCP 不能干净迁移到 DeepSeek V4**：压缩稀疏注意力有 indexer +
   compressor + 主注意力，CP 要切分协调全部子层，投入大量重叠与
   kernel 优化后仍只是「打平 DEP」。
3. **负载均衡不保证更好性能**：按队列深度/运行 token/KV 利用率
   均衡，全部劣于简单的 session 粘性路由。原因是缓存局部性——
   迁移迫使取 KV，且预取的块会占容量，导致「队列更均衡但并发更少」。

第 3 条直接反驳了我论文第 8 节 C 类的假设：均衡本身有价值。
实际是**均衡与局部性冲突，局部性常常更值钱**。
"""

from __future__ import annotations

from pathlib import Path

import re
import requests

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

TARGETS = {
    "vllm-large-scale": (
        "https://vllm.ai/blog/2025-12-17-large-scale-serving"),
    "vllm-agentx": (
        "https://vllm.ai/blog/2026-09-08-vllm-agentx"),
    "pytorch-dsv4-gb300": (
        "https://pytorch.org/blog/serving-deepseek-v4-on-gb300-with-"
        "sglang-5x-higher-throughput-at-the-same-interactivity-since-"
        "day-0/"),
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
        try:
            r = requests.get(url, timeout=45,
                             headers={"User-Agent": "Mozilla/5.0"})
        except Exception as e:
            print(f"{name}: 请求失败 {str(e)[:50]}")
            continue
        print(f"{name}: HTTP {r.status_code} {len(r.text):,} 字符")
        if r.status_code != 200:
            continue
        text = strip_html(r.text)
        p = DOCS / f"{name}.txt"
        p.write_text(text, encoding="utf-8", newline="\n")
        print(f"  -> {p.name}  {len(text):,} 字符")

        probes = ("parallelism", "kernel", "fusion", "offload", "router",
                  "routing", "CUDA graph", "prefill", "concurren",
                  "bitter", "balance")
        hits = [(k, text.count(k)) for k in probes if text.count(k)]
        for k, n in hits:
            print(f"     {k:<14} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
