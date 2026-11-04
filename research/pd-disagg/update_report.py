"""更新 REPORT.md：加入第 2 轮的窗口发现与新增脚本。

## 为什么用插入而不是整文件重写

REPORT.md 已有 162 行、结构完整。整文件重写风险大
（上一次 write 就因文件被并发修改而失败）。
这里只做三个定点改动：

1. §1 结论后插入「收益有上界」段——本轮最重要的发现
2. §3 量化发现表补 6 行新证据
3. §6 脚本表补 4 个新脚本

其余保持原样。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "REPORT.md"

WINDOW_SECTION = """**第 2 轮的关键修正**：这个差随负载是**有上下界的窗口，且非单调**，
不是单调门槛。跨 8 个模型、扫 9 个输入输出比（e-028 至 e-030）：

| I/O | 相对不分离 | 说明 |
|---|---|---|
| 0.01, 1 | < 1.00×（PD 最高 0.89×） | **8 个模型全部不分离最优** |
| 10 | 2.10× | 翻转集中在一个数量级内 |
| 100 | 1.05–1.92× | PDAF 对 8/8 模型超过不分离 |
| 500 | 1.5–1.8× | 平台期 |
| 1000 | **1.27×** | **回落：decode 硬件开始闲置** |

第三行到第五行是本文最有价值的发现：**收益有上界**。此前讨论分离的
文献几乎只谈下界（负载太轻不划算），没谈上界。实践含义直接——
按「负载越重越该分离」判断，会在最重的工作负载上做分离，
而那恰好是收益回落的区间。

因此给出的不是配置表，而是四项判据（`paper/tables/tab4_criteria.csv`）：
两阶段最优配置显著不同、存在高带宽 KV 通路、**负载落在窗口内**、
KV 规模足够大。第三条的措辞在本轮被改过：原先是「负载足够重」。

"""

NEW_ROWS = """| Qwen3-32B @ 8K 的 KV | **GB 级**，100 Gbps RDMA 上传输需数百毫秒 | e-032 |
| Llama2-7B 上 GPU 的延迟/吞吐优势 | 39× / 41× | e-033 |
| Llama 3.3 70B 分离后能耗降幅 | prefill 39%、decode 48% | e-034 |
| DeepSeek-V2-Lite 的 P95 TTFT 降幅 | 81%，SLO 达成率升 79% | e-035 |
| DeepSeek-V3.2 在 DP=16 的空转率 | 36.21%–59.98% | e-039 |
"""

NEW_SCRIPTS = """| `mine_model_results.py` | **第 2 轮**：按模型名挖定量结果（扫 16816 句） |
| `add_model_evidence.py` | **第 2 轮**：补 13 条证据（27 → 40） |
| `add_window_claim.py` | **第 2 轮**：新增 c-window 主张（收益窗口） |
| `paper/build_body.py` | **拼接 7 节成 body.tex 并断言内容确实进来** |
| `paper/wrap_circled.py` | **给圈码包 `\\sym{}`（否则静默丢字）** |
| `paper/restore_tab3.py` | 恢复重写时误删的模型变量表 |
| `paper/cite_window.py` | 给正文补 c-window 引用 |
"""


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")

    # ---- 1) 结论段：在「文献报告的加速倍数…」之后插入窗口 ----
    if "第 2 轮的关键修正" not in s:
        anchor = "文献报告的加速倍数都是这个差在特定条件下的取值。\n"
        i = s.find(anchor)
        if i < 0:
            print("[!] 结论锚点未找到")
        else:
            j = i + len(anchor)
            s = s[:j] + "\n" + WINDOW_SECTION + s[j:]
            print("已插入窗口段")
    else:
        print("窗口段已存在")

    # ---- 2) 量化表补行 ----
    if "e-032" not in s:
        anchor = "| 集群 InfiniBand 规格 | 800 Gbps（≈100 GB/s） | e-006 |\n"
        i = s.find(anchor)
        if i < 0:
            print("[!] 量化表锚点未找到")
        else:
            j = i + len(anchor)
            s = s[:j] + NEW_ROWS + s[j:]
            print("已补 6 行量化发现")
    else:
        print("量化行已存在")

    # ---- 3) 脚本表补行 ----
    if "mine_model_results.py" not in s:
        anchor = "| `build_pd.py` | 建 sources/evidence/claims/documents |\n"
        i = s.find(anchor)
        if i < 0:
            print("[!] 脚本表锚点未找到")
        else:
            j = i + len(anchor)
            s = s[:j] + NEW_SCRIPTS + s[j:]
            print("已补 7 个新脚本")
    else:
        print("脚本行已存在")

    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"\nREPORT.md {len(s):,} 字符")
    for probe in ("窗口", "e-032", "mine_model_results", "9 页"):
        print(f"  含 {probe:<22} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
