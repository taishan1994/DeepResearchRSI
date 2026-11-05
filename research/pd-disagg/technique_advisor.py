"""按部署场景给出技巧取舍：把论文 §8 的三条判据变成可执行检查。

## 为什么做这个

论文第 8 节给的是判据，但读者仍要自己把判据套到场景上。这里把
「前置条件」这一步自动化——因为**前置条件不满足时开了是负收益**，
这是全文最容易出错、也最容易靠工具拦住的一步。

## 用法

    python technique_advisor.py --model moe --interconnect nvlink \\
        --redundant-experts yes --concurrency 128

或交互式：

    python technique_advisor.py --interactive

## 设计上的两个决定

1. **只输出「该不该上」，不输出「能快多少」。**
   速度倍数依赖具体硬件与负载，来自文献的特定配置，套到别的场景
   会误导。工具只判断适用性，幅度让用户去查原文。

2. **每条判定都带理由与来源。**
   不给理由的推荐等于猜测；给了理由，用户可以自己反驳。

## 判据从哪来

全部来自 paper/sec8_technique.tex 与 evidence.csv 的 e-041..e-062。
每条规则的 docstring 里标了证据号。
"""

from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------- 数据结构

class Verdict:
    """一条技巧的判定结果。"""

    def __init__(self, name: str, category: str, status: str,
                 reason: str, evidence: str = "") -> None:
        self.name = name
        self.category = category
        self.status = status          # 建议上 / 可选 / 不建议 / 不可用
        self.reason = reason
        self.evidence = evidence

    def __str__(self) -> str:
        mark = {"建议上": "[+]", "可选": "[~]", "不建议": "[-]",
                "不可用": "[x]"}[self.status]
        s = f"  {mark} {self.name:<22} {self.reason}"
        if self.evidence:
            s += f"  ({self.evidence})"
        return s


def advise(model: str, interconnect: str, redundant_experts: bool,
           concurrency: int, kv_per_token_gb: float,
           context_k: int) -> list[Verdict]:
    """按场景返回每条技巧的判定。

    model: dense / moe
    interconnect: nvlink / rdma / cxl
    redundant_experts: 是否有冗余专家副本（LPLB 的前置条件）
    concurrency: 目标并发（决定投机解码与 DBO 是否划算）
    kv_per_token_gb: 每 token 的 KV 大小（GB），决定 KV 总量量级
    context_k: 上下文长度（千 token）
    """
    out: list[Verdict] = []
    is_moe = model == "moe"
    kv_total_gb = kv_per_token_gb * context_k * 1000

    # ---------------- A 类：省传输量 ----------------

    # 逐层传输的前置条件：KV 总量要够大，否则细粒度同步的固定开销反超。
    # 依据 e-045 / e-046（Splitwise 明确说小 prompt 不值得逐层传）。
    if kv_total_gb >= 0.5:
        out.append(Verdict(
            "逐层传输", "A",
            "建议上",
            f"KV 约 {kv_total_gb:.1f} GB，足以摊平逐层同步开销",
            "e-045/e-046"))
    else:
        out.append(Verdict(
            "逐层传输", "A", "不建议",
            f"KV 仅约 {kv_total_gb:.2f} GB，切细后固定开销反超收益",
            "e-046"))

    # chunk 级传输需要 chunked prefill 才有意义。
    out.append(Verdict(
        "chunk 级传输", "A", "建议上",
        "与 chunked prefill 配合可让 prefill 与 KV 传输并行",
        "e-047"))

    # 前缀缓存：高并发多轮对话才有稳定命中率。
    if concurrency >= 8:
        out.append(Verdict(
            "前缀缓存", "A", "建议上",
            "并发足够，多轮/共享前缀命中率可期；命中后需搬的 KV 变小",
            "e-010"))
    else:
        out.append(Verdict(
            "前缀缓存", "A", "可选",
            "并发低，前缀复用机会少，但仍可拦截重复系统提示",
            "e-010"))

    # ---------------- B 类：让传输不可见 ----------------

    # 这一类的共同前提是 MoE + EP：没有 all-to-all 就没有可重叠的对象。
    if not is_moe:
        for name in ("TBO", "SBO", "DBO"):
            out.append(Verdict(
                name, "B", "不可用",
                "dense 模型无 MoE all-to-all，没有可被重叠的通信",
                "e-041/e-042/e-043"))
    else:
        out.append(Verdict(
            "TBO", "B", "建议上",
            "MoE 有 all-to-all；TBO 不增加峰值显存",
            "e-041"))
        out.append(Verdict(
            "SBO", "B", "可选",
            "不拆 batch，无 GEMM 变窄风险，但可重叠窗口只到 shared expert",
            "e-042"))
        # DBO 有 token 阈值：小 batch 拆两半会让 GEMM 变窄。
        if concurrency >= 32:
            out.append(Verdict(
                "DBO", "B", "建议上",
                f"并发 {concurrency} 高于拆分阈值；拆分后两半仍够宽",
                "e-043/e-044"))
        else:
            out.append(Verdict(
                "DBO", "B", "不建议",
                f"并发 {concurrency} 偏低，拆成两半后 GEMM 变窄、"
                "线程切换有成本",
                "e-044"))

    # piggyback：不分离架构下替代分离。
    out.append(Verdict(
        "piggyback", "B", "可选",
        "不分离时用它替代分离（decode 搭 prefill 便车）；"
        "已分离则优先级低",
        "c-profile"))

    # ---------------- C 类：均衡负载 ----------------

    if not is_moe:
        out.append(Verdict(
            "Waterfill / LPLB / EPLB", "C", "不可用",
            "dense 模型无专家，无负载不均问题", "e-048/e-049"))
    else:
        # Waterfill 只改 shared expert 的派发目标，无额外前置条件。
        out.append(Verdict(
            "Waterfill", "C", "建议上",
            "只改 shared expert 派发目标，不动权重、不改路由",
            "e-048"))
        # LPLB 必须要有冗余副本，否则只有 all-reduce 开销。
        if redundant_experts:
            out.append(Verdict(
                "LPLB", "C", "建议上",
                "有冗余专家副本可重新平衡；不损精度（不改 router 逻辑）",
                "e-049/e-050"))
        else:
            out.append(Verdict(
                "LPLB", "C", "不建议",
                "无冗余副本（red0）：没有可重平衡的对象，"
                "all-reduce 与求解只表现为开销",
                "e-053"))

    # 请求迁移：只在多实例且负载有偏斜时有用。
    if concurrency >= 32:
        out.append(Verdict(
            "请求迁移（Llumnix 式）", "C", "可选",
            "高并发下实例间偏斜才有意义；秒级时间尺度，与 EPLB 可叠加",
            "e-018"))
    else:
        out.append(Verdict(
            "请求迁移", "C", "不建议",
            "并发偏低，迁移开销可能超过均衡收益", "e-018"))

    # ---------------- D 类：省 decode 步 ----------------

    # DSpark / 自适应验证在低并发时收益大，高并发时靠自适应才不亏。
    if concurrency <= 64:
        out.append(Verdict(
            "DSpark 自适应验证", "D", "建议上",
            f"并发 {concurrency} 时 draft token 与真 token 争算力不严重，"
            "投机解码收益明显",
            "e-054/e-057"))
    else:
        out.append(Verdict(
            "DSpark 自适应验证", "D", "建议上",
            f"并发 {concurrency} 时固定长度 draft 会明显亏；"
            "自适应验证能在高并发维持收益",
            "e-055/e-056/e-057"))
    out.append(Verdict(
        "DSpark 的限制", "D", "可选",
        "需 ALWAYS 级 CUDA graph：不支持 --enforce-eager / LoRA / PP",
        "e-058"))

    # ---------------- 补充三类 ----------------

    if interconnect in ("rdma", "cxl"):
        out.append(Verdict(
            "GPUDirect RDMA / zero-copy", "补充", "建议上",
            f"{interconnect.upper()} 传输占比高，绕过主机内存与中间拷贝收益大",
            "e-059/e-060"))
    else:
        out.append(Verdict(
            "GPUDirect RDMA / zero-copy", "补充", "可选",
            "NVLink 域内传输已很快，收益相对小",
            "e-059/e-060"))

    out.append(Verdict(
        "准入与早拒", "补充", "建议上",
        "过载时把注定超时的请求排进队列只会拖垮其它请求；"
        "幅度最大的一条",
        "e-061"))

    if concurrency >= 64:
        out.append(Verdict(
            "并行度重切分", "补充", "可选",
            "相位持续够久才划算（重切有一次性 reshard 成本）",
            "e-062"))
    else:
        out.append(Verdict(
            "并行度重切分", "补充", "不建议",
            "低并发下相位短，摊不平一次性的权重 reshard 成本",
            "e-062"))

    return out


def render(verdicts: list[Verdict], model: str, interconnect: str,
           redundant: bool, concurrency: int) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append(f"场景：model={model}  interconnect={interconnect}  "
                 f"冗余副本={'有' if redundant else '无'}  "
                 f"并发={concurrency}")
    lines.append("=" * 72)

    cats = [("A", "A 类：省传输量"), ("B", "B 类：让传输不可见"),
            ("C", "C 类：均衡负载"), ("D", "D 类：省 decode 步"),
            ("补充", "补充三类：数据通路 / 准入 / 重切分")]
    for key, title in cats:
        sub = [v for v in verdicts if v.category == key]
        if not sub:
            continue
        lines.append("")
        lines.append(title)
        for v in sub:
            lines.append(str(v))

    go = [v for v in verdicts if v.status == "建议上"]
    no = [v for v in verdicts if v.status in ("不建议", "不可用")]

    lines.append("")
    lines.append("-" * 72)
    lines.append(f"建议上 {len(go)} 条 ｜ 不要上 {len(no)} 条")
    lines.append("")
    lines.append("顺序建议（按固定成本从低到高）：")
    lines.append("  1. A 类把传输量降下来")
    lines.append("  2. B 类把剩下的藏起来（仅 MoE）")
    lines.append("  3. D 类减少 decode 步数")
    lines.append("  4. C 类抹平尾部不均")
    lines.append("  5. 补充类：准入最先上（幅度最大、成本最低）")
    lines.append("")
    lines.append("⚠️ 本工具只判断「该不该上」，不给「能快多少」。")
    lines.append("   幅度依赖具体硬件与负载，请查对应证据的原文。")
    return "\n".join(lines)


def interactive() -> int:
    print("按提示回答，回车用方括号里的默认值。\n")
    model = input("模型类型 dense/moe [moe]: ").strip() or "moe"
    interconnect = input("互联 nvlink/rdma/cxl [rdma]: ").strip() or "rdma"
    red = input("是否有冗余专家副本 yes/no [yes]: ").strip() or "yes"
    conc = input("目标并发 [128]: ").strip() or "128"
    kv = input("每 token 的 KV 大小 GB（GQA 8K 约 0.001）[0.001]: ").strip() \
        or "0.001"
    ctx = input("上下文长度（千 token）[8]: ").strip() or "8"

    try:
        verdicts = advise(model, interconnect, red.lower().startswith("y"),
                          int(conc), float(kv), float(ctx))
    except ValueError as e:
        print(f"输入有误：{e}")
        return 1
    print()
    print(render(verdicts, model, interconnect,
                 red.lower().startswith("y"), int(conc)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="按部署场景给出 PD 优化技巧的取舍判定")
    ap.add_argument("--model", choices=["dense", "moe"], default="moe")
    ap.add_argument("--interconnect",
                    choices=["nvlink", "rdma", "cxl"], default="rdma")
    ap.add_argument("--redundant-experts",
                    choices=["yes", "no"], default="yes")
    ap.add_argument("--concurrency", type=int, default=128)
    ap.add_argument("--kv-per-token-gb", type=float, default=0.001,
                    help="每 token 的 KV 大小（GB）")
    ap.add_argument("--context-k", type=float, default=8.0,
                    help="上下文长度（千 token）")
    ap.add_argument("--interactive", action="store_true")
    args = ap.parse_args()

    if args.interactive:
        return interactive()

    red = args.redundant_experts == "yes"
    verdicts = advise(args.model, args.interconnect, red,
                      args.concurrency, args.kv_per_token_gb,
                      args.context_k)
    print(render(verdicts, args.model, args.interconnect, red,
                 args.concurrency))
    return 0


if __name__ == "__main__":
    sys.exit(main())
