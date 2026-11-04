"""二筛：把「kernel」与「生成/优化」绑在邻近位置，剔除同文不同句的假命中。

## 为什么需要二筛

一筛要求「有 kernel 类词」+「有智能体要件」+「有生成类词」，但三者
**可以出现在完全不同的句子里**，于是混进了：

    2610.26106  A GPU-Resident Pipeline for Multi-Robot 3D Inspection
                —— 有 GPU、有 pipeline，但讲的是水下机器人巡检
    2611.04096  Online Hamilton-Jacobi Reachability Onboard the Robot Control
                —— 有 GPU 加速，但讲的是控制理论
    2506.11108  CAGSR-vLLM-MTC
                —— 有 multi-turn，但讲的是对话推理

一筛保留 44 篇里，有 12 篇题名连 kernel 类词都没有。

## 二筛判据（三选一即可）

  P1  题名里同时出现 kernel 语境词与生成/优化词
  P2  摘要里有「kernel 语境 + 生成/优化」在**同一句**内出现
  P3  题名或摘要明确提到具体 kernel benchmark / 工具
      （KernelBench、Triton、CUDA、SASS、PTX、cuBLAS、CUTLASS 等）

这条改写把「同文」收紧成「同句」，因为同一个摘要讲 GPU 加速的机器人
和讲 kernel 生成是两件事，词频统计分不开。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

KERNEL = re.compile(
    r"\b(cuda|triton|gpu kernel|kernel generation|kernel optimization"
    r"|gpu program|sass|ptx|cublas|cutlass|ascend|npu kernel|hip|opencl"
    r"|kernelbench|flashattention|attention kernel|matmul kernel)\b", re.I)

GEN = re.compile(
    r"\b(generat\w+|optimi\w+|refine\w*|improv\w+|synthes\w+|tuning"
    r"|speedup|faster|high-performance|efficien\w+)\b", re.I)

# 明确的 kernel 生成/优化标识物
MARKER = re.compile(
    r"\b(kernelbench\w*|triton|cuda|sass|ptx|cublas|cutlass|tilelang"
    r"|flashattention|tvm|tensorrt|ascend|npu)\b", re.I)


def sentences(text: str) -> list[str]:
    # 粗略分句：句号/问号/换行
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if p.strip()]


def main() -> int:
    d = json.loads((HERE / "screened_agent.json").read_text(encoding="utf-8"))
    kept = d["kept"]
    print(f"一筛保留 {len(kept)} 篇，做二筛\n")

    out, dropped = [], []
    for r in kept:
        title = r["title"]
        summ = r.get("summary") or ""

        p1 = bool(KERNEL.search(title) and GEN.search(title))
        # P2：同一句里同时有 kernel 与生成/优化
        p2 = any(KERNEL.search(s) and GEN.search(s) for s in sentences(summ))
        p3 = bool(MARKER.search(title + " " + summ[:1200]))

        reasons = [n for n, v in (("P1", p1), ("P2", p2), ("P3", p3)) if v]
        rec = dict(r)
        rec["_pass"] = reasons
        if reasons:
            out.append(rec)
        else:
            dropped.append(rec)

    out.sort(key=lambda r: (len(r["_pass"]), len(r["_agent_signals"])),
             reverse=True)

    print(f"二筛保留 {len(out)} 篇，剔除 {len(dropped)} 篇\n")
    print("=== 保留 ===")
    for r in out:
        print(f"  {r['arxiv_id']}  [{'/'.join(r['_pass'])}] "
              f"[{'+'.join(r['_agent_signals'])}]")
        print(f"      {r['title'][:84]}")

    print("\n=== 二筛剔除 ===")
    for r in dropped:
        print(f"  {r['arxiv_id']}  {r['title'][:68]}")

    (HERE / "screened2_agent.json").write_text(
        json.dumps({"kept": out, "dropped": [r["arxiv_id"] for r in dropped]},
                   ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n写入 screened2_agent.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
