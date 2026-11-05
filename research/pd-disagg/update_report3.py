"""给 REPORT.md 补第 3 轮内容：优化技巧层。

## 为什么 REPORT 必须写这一层

REPORT.md 是归档的入口文档。用户指出第 1 轮缺优化技巧，
若 REPORT 不写，下次读这个归档的人（包括我自己）还会以为
「技术 = 传输 / 切分 / 模型」三层，重复同一个缺口。

## 补什么

1. §1 结论后加一小节：技巧层的四类划分与最实用的一句
2. §3 量化发现表补 6 行技巧实测
3. §6 脚本表补 5 个新脚本
4. 新增 §「第 3 轮补的是什么」（说明为什么之前漏了）

第 4 条最重要——它记录了**漏掉的原因**，不只是漏掉的结果。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "REPORT.md"

TECHNIQUE_SECTION = """## 1.5 第 3 轮补的一层：优化技巧

前三轮把「技术」理解成架构层（为什么分 / 怎么搬 / 怎么切），
漏掉了**具体优化技巧**这一层。用户指出后重查，语料里实际浮现出
22 个技巧词，远超最初举的四个例子（lplb / waterfill / tbo / dspark）。

补上之后技术栈是四层，第四层按**作用对象**分四类：

| 类别 | 作用于 | 代表技巧 | 实测幅度 |
|---|---|---|---|
| A 省传输量 | KV 字节数 | 逐层传输、chunk 级传输、压缩/量化、前缀缓存 | 成比例 |
| B 让传输不可见 | 传输与计算时序 | TBO、SBO、DBO、piggyback | 隐藏传输 |
| C 均衡负载 | rank 分到多少 | Waterfill、LPLB、EPLB、请求迁移 | 0.84–7.34% |
| D 省 decode 步 | 要跑多少步 | DSpark 自适应验证、投机解码 | 随并发 |

另有四条不落在这四类里，但量级更大：

- **准入与拒绝**：Mooncake 的预测式 early rejection，模拟场景吞吐
  最高 +525%、真实负载多处理 75% 请求。它提升的不是「算得更多」，
  而是「算的都是有用的」。
- **并行度重切分**：运行中改 DP/TP/PP 布局，rollout makespan
  528.8 s → 259.1 s，decode 吞吐 2.04×，代价是权重 reshard。
- **数据通路**：zero-copy 让 kernel 直接操作应用数据区；
  GPUDirect RDMA 让网卡直读显存，绕过主机内存。
- **弹性配比 / 请求迁移**：FluidPD 改 P:D 比、Llumnix 迁移请求。

### 最实用的一句

**同类技巧互相替代，异类可以叠加。** 所以取舍不是「选哪个」，
而是「每类选一个」。

### 为什么之前会漏

因为检索是按**架构术语**做的（`disaggregated prefill`、
`KV transfer`），而这些技巧的名字（TBO、LPLB、Waterfill、DSpark）
不在这套术语里，它们出现在**框架文档与工程博客**中，
不在 arXiv 论文的标题或摘要里。46 篇论文全文里 TBO 命中 47 篇、
chunked prefill 28 篇，但像 LPLB、Waterfill、DSpark 这几个词
一次都没出现——它们是 2026 年的工程实现，还没有对应论文。

教训：**只检索论文会系统性漏掉工程侧的优化技巧。**

### 一个必须点出的交互

PD 分离与这些技巧不是并列关系。以 LPLB 为例：DP attention 下
不同 EP rank 在同一步跑不同 forward 模式（prefill / decode / idle），
**没有单个 rank 看得到全局 token 分布**，均衡算法必须额外做一次
all-reduce 才能拿到全局视图。这既是开销也是延迟。

这解释了为什么有些在不分离部署里跑得好的技巧，搬到 PD 上收益变薄：
**信息可见性被架构改变了。**

### 前置依赖：开了可能是负收益

每条技巧都有适用下限，这是最容易被忽略的：

- LPLB 在无冗余副本（`red0`）时只有 all-reduce 开销、没有收益
- 逐层传输在 KV 太小时，细粒度同步的固定开销反超收益
- DBO 在 token 数低于阈值时不拆分（拆完 GEMM 变窄反而慢）
- DSpark 需要 ALWAYS 级 CUDA graph，不支持 `--enforce-eager` / LoRA / PP

"""

NEW_ROWS = """| Waterfill 吞吐提升 | 1.48%–4.66%（3 个数据集） | e-048 |
| LPLB 吞吐提升 | 0.84%–7.34%（有冗余副本时） | e-049 |
| LPLB 在 red0 下 | 只有开销，无收益 | e-053 |
| DSpark 末位 draft token 存活率 | <10%（首位 >70%） | e-055 |
| Mooncake early rejection | 模拟场景 +525%，真实 +75% 请求 | e-061 |
| 并行度重切分 | makespan 528.8s → 259.1s，2.04× | e-062 |
"""

NEW_SCRIPTS = """| `fetch_technique_docs.py` | **第 3 轮**：抓技巧层的一手文档快照 |
| `add_technique_evidence.py` | **第 3 轮**：补 18 条技巧证据 |
| `add_technique_extra.py` | **第 3 轮**：补数据通路/准入/重切分 4 条 |
| `add_technique_claim.py` | **第 3 轮**：新增 c-technique 主张 |
| `make_technique_data.py` | **第 3 轮**：技巧层数值 → paper/data |
| `update_intro.py` | 同步引言计数与贡献项 |
| `update_conclusion.py` | 结论从三层改为四层 |
"""


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")

    if "第 3 轮补的一层" not in s:
        anchor = "## 2. 交付物"
        i = s.find(anchor)
        if i < 0:
            print("[!] 交付物锚点未找到")
            return 1
        s = s[:i] + TECHNIQUE_SECTION + "\n" + s[i:]
        print("已插入技巧层小节")

    if "e-048" not in s:
        anchor = "| DeepSeek-V3.2 在 DP=16 的空转率 | 36.21%–59.98% | e-039 |\n"
        i = s.find(anchor)
        if i < 0:
            print("[!] 量化表锚点未找到")
        else:
            j = i + len(anchor)
            s = s[:j] + NEW_ROWS + s[j:]
            print("已补 6 行技巧实测")

    if "fetch_technique_docs.py" not in s:
        anchor = "| `mine_model_results.py` |"
        i = s.find(anchor)
        if i < 0:
            print("[!] 脚本表锚点未找到")
        else:
            s = s[:i] + NEW_SCRIPTS + s[i:]
            print("已补 7 个新脚本")

    s = s.replace("| `paper/build_body.py` |", "| `paper/build_body.py` |", 1)
    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"\nREPORT.md {len(s):,} 字符")
    for probe in ("第 3 轮补的一层", "同类技巧互相替代", "e-061", "前置依赖"):
        print(f"  含 {probe:<20} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
