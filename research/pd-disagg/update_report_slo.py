"""把 SLO 这一层写进 REPORT / LESSONS / EVOLUTION。

## REPORT

补 1.7，重点是那三组 SLO 配置表和三层次的反向证据。

## LESSONS

这一轮的教训与前一轮不同。上一轮是「分类不完备」（维度选错），
这一轮是「结论缺条件」（所有收益数字都隐含一个 SLO 形状）。

值得单独成条：**报收益时必须报出使该收益成立的条件**。
「提升 93%」不是结论，「在 SLO 形状为 X 时提升 93%」才是。

## EVOLUTION

判据九。前八条讲怎么查证据，这一条讲怎么表述结论——
属于判据体系的另一侧。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "research" / "pd-disagg" / "REPORT.md"
LESSONS = ROOT / "docs" / "LESSONS.md"
EVO = ROOT / "docs" / "EVOLUTION.md"

REPORT_SEC = """## 1.7 第 5 轮：同一技巧在不同 SLO 下方向相反

上一轮末尾提出「按 SLO 类型再切一次，看同一技巧是否反向」。
答案是**确实反向**，且反向有三层证据。

### 机制层：一个旋钮，两个 SLO

Sarathi-Serve 的 token 预算由两个相互竞争的因素决定：TBT 的 SLO 要求
与 chunk 切分自身的开销。原文：*"From a TBT minimization point of view,
a smaller token budget is preferable... However, smaller token budget can
result in excessive chunking."*

| token 预算 | TBT | 吞吐 |
|---|---|---|
| 调小 | 变好 | 变差（chunk 过碎） |
| 调大 | 变差 | 变好 |

开销有确切机制，不是含糊的"固定成本"：prompt 切成 N 个 chunk 时，
**第一个 chunk 的 KV cache 要被加载 N−1 次，第二个 N−2 次**——
计算量不变，HBM 重复读取增加。

### 陈述层：优先谁就伤害谁

原文：*"prioritizing prefills leads to high latency because it pauses
ongoing decodes"*。调度的两端各自伤害一个 SLO，没有中间地带能同时最优。

### 参数层：TTFT 跨 120 倍，TPOT 几乎不变

DistServe Table 1 的三组配置：

| 应用 | TTFT | TPOT | 特征 |
|---|---|---|---|
| Chatbot OPT-175B | 4.0s | 0.2s | TTFT 宽松、TPOT 严 |
| Code Completion OPT-66B | 0.125s | 0.2s | TTFT 极严 |
| Summarization OPT-66B | 15s | 0.15s | TTFT 极宽松、TPOT 最严 |

TTFT 从 0.125s 到 15s，跨约 120 倍；TPOT 都在 0.1–0.2s。
**决定配置的不是「SLO 严不严」，是「两个 SLO 的相对松紧」。**

这也解释了实践中的困惑：同一分离方案在 A 团队是 3 倍提升、
在 B 团队几乎没变——不是配置错，是 SLO 形状不同。

### 收益结构本身也随应用变

同一套系统：代码补全支撑 3.2× 请求率 + SLO 更严 1.5×；
聊天是 SLO 更严 1.4×–1.8×。都算显著，但结构不同——
前者体现在**能扛多少请求**，后者体现在**能扛多严的延迟**。

### 由此得到的顺序判据

**先定 SLO 形状，再按平面查漏，最后按成本链取舍。**
顺序不能颠倒：方向错了，后面做得越细越糟。

### 一处自查发现

写这节时我凭记忆引了一句"prioritizing prefills improves TTFT latency
whereas prioritizing decodes has the opposite effect"——切片时锚点
找不到。真实原文是"prioritizing prefills **leads to high latency**"。
意思相近，但不是原话。**这就是必须切片而不手抄的原因**：记忆会把
两处内容合并成一句通顺但不存在的引文。

"""

LESSON = """### 1.9 报收益时必须报出让该收益成立的条件

「某技巧提升 93%」不是结论，「在 SLO 形状为 X 时提升 93%」才是。
少掉后半句,读者无法判断这个数对他是否适用。

**怎么发现的**:整理论文时把各技巧的提升幅度并列成表,看起来信息量很大。
后来被问「同一技巧在别的场景会不会相反」,去找证据,发现**确实会**——
chunked prefill 的 token 预算,调小则 TBT 变好、吞吐变差,调大则相反;
优先 prefill 抬高已跑 decode 的延迟,优先 decode 则抬高 TTFT。
更硬的是三组真实应用:TTFT 从 0.125 秒到 15 秒跨 120 倍,
而 TPOT 都在 0.1–0.2 秒。

**为什么危险**:并列的提升幅度表会让人以为这些数可以横向比较、
可以叠加、可以无条件成立。实际上它们各自的成立条件互相冲突,
换个场景可能变负收益。而**表本身不会显示这一点**——
每一行都忠实引用了原文。

**怎么用**:任何收益数字都要附带三个条件——(1) SLO 形状
(哪个更紧、比值多少、达成率目标),(2) 硬件与互联,
(3) 负载形态(长度分布、并发、前缀复用率)。
三个缺一个,这个数就不可移植。写进表格时,宁可拆成两组也不要合并。

**另一条**:这轮还抓到自己一次记忆性引错——凭印象写的引言在原文里
不存在(真实表述是「leads to high latency」而非「improves TTFT」)。
意思相近,但不是原话。凡引用必切片,这是唯一可靠的防线。

"""

JUDGE = """### 判据九：结论必须带成立条件

前八条判据都在讲怎么把证据查对。这一条讲另一侧:**查对了的证据,
仍可能被表述成无条件结论**。

具体做法:每写一个收益数字,同时写清使它在什么条件下成立。
检查方式是问「换一个 SLO 形状/硬件/负载,这个数还成立吗」——
若答案是「不成立」,那条件就必须写进正文,而不是留在推导里。

本轮实例:整理出 2.65x / 93% / 13% 等幅度后,看似可以并列成表。
但追查后发现同一个 token 预算旋钮在两个 SLO 下方向相反,
TTFT 与 TPOT 的相对松紧才是真正的自变量。故这些数字必须
带上 SLO 形状才能比较,否则并列本身在暗示一个不存在的可比性。

"""


def main() -> int:
    # ---- REPORT ----
    r = REPORT.read_text(encoding="utf-8")
    if "方向相反" not in r:
        anchor = "## 2. 交付物"
        i = r.find(anchor)
        if i < 0:
            print("[!] REPORT 锚点未找到")
        else:
            r = r[:i] + REPORT_SEC + r[i:]
            REPORT.write_text(r, encoding="utf-8", newline="\n")
            print("REPORT 已补 SLO 一节")
    else:
        print("REPORT 已含 SLO 一节")

    # ---- LESSONS ----
    s = LESSONS.read_text(encoding="utf-8")
    if "1.9 报收益时必须" not in s:
        anchor = "## 二、数字与产物"
        i = s.find(anchor)
        if i < 0:
            print("[!] LESSONS 锚点未找到")
        else:
            sep = "---\n\n"
            j = s.rfind(sep, 0, i)
            pos = j if j > 0 else i
            s = s[:pos] + LESSON + s[pos:]
            LESSONS.write_text(s, encoding="utf-8", newline="\n")
            print("LESSONS 已补 1.9")
    else:
        print("LESSONS 已含 1.9")

    # ---- EVOLUTION ----
    e = EVO.read_text(encoding="utf-8")
    if "判据九" not in e:
        anchor = "## 三、"
        i = e.find(anchor)
        if i < 0:
            e = e + "\n\n---\n\n" + JUDGE
            print("EVOLUTION 已追加判据九（末尾）")
        else:
            sep = "---\n\n"
            j = e.rfind(sep, 0, i)
            pos = j if j > 0 else i
            e = e[:pos] + JUDGE + e[pos:]
            print("EVOLUTION 已补判据九")
        import re
        e = re.sub(r"## (\S+)条判据", "## 九条判据", e)
        e = e.replace("八条判据", "九条判据")
        EVO.write_text(e, encoding="utf-8", newline="\n")
    else:
        print("EVOLUTION 已含判据九")

    print(f"\nREPORT {len(r):,} | LESSONS {len(s):,} | EVOLUTION {len(e):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
