"""把「四类之外」的发现写进 REPORT 与 LESSONS。

## REPORT：补一节

这轮的核心结论是「我的四类不完备」，必须写进入口文档，
否则下次读归档的人还会以为四类是完整清单。

## LESSONS：补一条方法论

值得单独成条的教训：**分类的完备性不能用分类内部的例子来验证**。
我当初的四类是「拿四个例子套出来」的，四个例子都能归类，
于是看起来完备。要验证完备性，必须换一个维度切
（这里是按实现平面），看有没有东西掉在四类之外。

这是一条通用的方法论，不是 PD 专属。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "research" / "pd-disagg" / "REPORT.md"
LESSONS = ROOT / "docs" / "LESSONS.md"

REPORT_SEC = """## 1.6 第 4 轮：四类之外还有三层

用户问「除 ABCD 四类还有其它的吗」。查证结果是：**四类不完备，
但也不错误**——它的维度是「作用于 KV 传输成本的哪个环节」，
只覆盖分离引入的额外成本。

vLLM 的大规模服务文档列出九项关键优化，把每 H200 吞吐从约
1,500 提到 2,200 tok/s——**其中六项与 KV 传输无关**：异步调度、
CUDA graph 的 `FULL_AND_PIECEWISE`、DeepGEMM、DeepEP kernel、
SiLU kernel、算子融合。

换成按**实现平面**看，有三层，其中五个维度不在四类里：

| 平面 | 管什么 | 四类漏掉的 |
|---|---|---|
| 数据面 | KV 放哪、留多久 | KV 池分层、打包布局、session 感知保留 |
| 执行面 | 单步算多快 | 并行策略选择、kernel 融合、CUDA graph、异步调度 |
| 控制面 | 谁在何时被调度 | 长 prefill token 上限、prefill 节拍、路由策略 |

### 三个幅度最大的，都不在四类里

- **并行策略**：DeepSeek V4 在 32K prompt 上 PCP8 相对 TP8 有 2.65×
  prefill 加速。这是「选哪种切法」，不是「均衡负载」。
- **调度顺序**：给单条请求每步可调度的 token 数设上限（512），
  在 B300 上跑 DeepSeek V4 Pro 使 TPGS 提升最多 93%、P90 交互性约 2.3×。
  机制是**消除队头阻塞**——一条长 prefill 会占满整个 token 预算，
  同 rank 上排队的短轮次在它结束前完全无法被调度。
- **kernel 融合**：对称内存 + kernel 内融合替代 NCCL all-gather，
  每层延迟降约 13%；latent-tail MoE 融合降端到端约 5%。

对比一下：四类里的 C 类（均衡）是个位数百分比（0.84%–7.34%）。
**四类里幅度最大的一条，不如四类外最小的一条。**

### 三个反例界定了适用条件

比正面技巧更有信息量：

1. **流水线并行不适合热轮次**：前缀已缓存、每轮只新增几百到几千
   token，没有足够新计算填满流水线，bubble 吃掉大部分收益。
   故 PP 适合冷的、计算重的 prefill，不该是热轮次的默认。
2. **上下文并行不必然迁移**：DeepSeek V4 的压缩稀疏注意力含
   indexer、compressor 与主注意力三层，CP 要切分协调全部子层。
   投入大量重叠与 kernel 优化后，DCP 只打平 DEP，未超过。
   原文结论：并行必须跟随模型架构。
3. **负载均衡可能有害**：按队列深度/KV 利用率均衡，全部劣于
   session 粘性路由。迁移要取 KV，预取的块临时占目标 rank 的 KV
   容量，导致**队列更均衡但并发更少**。

第 3 条直接修正了我的 C 类假设：均衡本身有价值。实际是
**均衡与局部性冲突，局部性常常更值钱**。

### 两套划分的关系

- 四类按**成本链**切：能对应收益与代价，但看不到传输之外的层
- 三平面按**实现层**切：完备，但不直接告诉你哪个划算
- **两者正交，叠加使用**：用三平面保证不漏，用四类判断传输那一层

"""

LESSON = """### 1.8 分类的完备性不能用分类内部的例子来验证

拿几个例子套出一个分类，若这些例子都能归类，分类就「看起来完备」。
但这是循环论证——**例子是被用来构造分类的，当然落得进去**。

**怎么发现的**：一篇综述把优化技巧按「作用于成本链的哪个环节」分成
四类（省量/隐藏/均衡/少步），四个代表技巧各归一类，包括用户点名问的
那几个，看起来完整。直到被追问「还有其它的吗」，换一个维度
（按实现平面：数据面/执行面/控制面）重切，才发现至少五个维度
掉在四类之外，且**其中三个的幅度比四类里任何一个都大**——
2.65 倍的并行策略、93% 的调度上限、13% 的算子融合。

**为什么危险**：这类欠缺不会触发任何检查。E1 覆盖率 100%、
数值回溯全通过、审计全绿——因为语料里本来就没有那一层。
检查器只在已有语料上工作。

**怎么用**：给出一个分类后，**必须换至少一个正交维度重切一次**，
并明确回答「什么东西会掉在新切法里而旧切法里没有」。
答不出，就说明旧分类的完备性没有被验证过。
另一条更省力的检测：问「本领域从业者在生产里还会调什么」，
凡是答不出对应类别的项，都是缺口。

"""


def main() -> int:
    # ---- REPORT ----
    r = REPORT.read_text(encoding="utf-8")
    if "四类之外还有三层" not in r:
        anchor = "## 2. 交付物"
        i = r.find(anchor)
        if i < 0:
            print("[!] REPORT 锚点未找到")
        else:
            r = r[:i] + REPORT_SEC + r[i:]
            REPORT.write_text(r, encoding="utf-8", newline="\n")
            print("REPORT 已补四类之外")
    else:
        print("REPORT 已含四类之外")

    # ---- LESSONS ----
    s = LESSONS.read_text(encoding="utf-8")
    if "1.8 分类的完备性" not in s:
        anchor = "## 二、数字与产物"
        i = s.find(anchor)
        if i < 0:
            print("[!] LESSONS 锚点未找到")
            return 1
        sep = "---\n\n"
        j = s.rfind(sep, 0, i)
        pos = j if j > 0 else i
        s = s[:pos] + LESSON + s[pos:]
        LESSONS.write_text(s, encoding="utf-8", newline="\n")
        print("LESSONS 已补 1.8")
    else:
        print("LESSONS 已含 1.8")

    print(f"\nREPORT {len(r):,} 字符 | LESSONS {len(s):,} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
