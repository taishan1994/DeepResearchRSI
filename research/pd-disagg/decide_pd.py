"""从 88 篇 core 里收敛到可写的一批，并用「假设检验」驱动选取。

## 为什么要第二次收敛

88 篇 core 里混进了明显不相关的：
  · 2605.11232  反洗钱合规的 LLMOps（只是提到 serving）
  · 2603.10030  DMA 流式框架的内核级缓冲编排（硬件细节）
  · 2610.07443  分离式量化架构（"disaggregated" 指量化，不是 P/D）
  · 2609.28717  FPGA-GPU 异构（硬件加速，非 PD 机制）

判据 `DISAGG` 匹配到了 "disaggregat" 一词，但该词在系统论文里
既指 P/D 分离，也指「解耦的某个组件」。这是词义歧义，不是选取错误。

## 收敛策略：按「能否支撑某一个子问题」挑选

不追求覆盖全部 88 篇，而是保证每个子问题（q1-q5）都有足够的
一手材料，且**核心假设可被检验**。

四类必须收：
  S 奠基（Splitwise/DistServe/Sarathi/Llumnix/Mooncake）
  Q 直接回答「分离何时划算」的（标题含 when/whether/pay/how far）
  M 模型特异性（MLA/GQA/MoE/长上下文/多模态，各取代表）
  T 传输与切分机制（NIXL/Mooncake/chunked/layer-wise/CXL）

其余按「是否提供可引用的量化数字」决定。判据写在 KEEP 表里，
逐条可复查。
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 人工选定：arxiv_id -> (layer, 一句话理由)
# 理由必须指向该文的具体贡献，不能写「相关」。
KEEP: dict[str, tuple[str, str]] = {
    # ---- S 奠基 ----
    "2311.18677": ("core", "Splitwise：最早提出 phase splitting，给出 P/D 分别用不同硬件的方案"),
    "2401.09670": ("core", "DistServe：提出 goodput 指标，把 P/D 放不同 GPU 并优化配比"),
    "2407.00079": ("core", "Mooncake：KVCache 为中心的分离架构，工业级部署数据"),
    "2406.03243": ("core", "Llumnix：动态调度，量化对比分离与混部的收益差"),
    "2403.02310": ("adjacent", "Sarathi-Serve：chunked prefill 代表作，分离的替代路线"),

    # ---- Q 直接回答「何时划算」----
    "2608.03741": ("core", "When Does Disaggregation Pay?：直接给出分离划算的判据"),
    "2605.28302": ("core", "How Far Can Disaggregation Go?：注意力分离的设计空间探索"),
    "2508.01989": ("core", "Aggregation or Disaggregation?：统一两者，给出切换条件"),
    "2607.25498": ("core", "Beyond PD Disaggregation：异质场景下分离的边界"),
    "2601.08833": ("core", "Revisiting Disaggregated Serving for Performance：重估分离收益"),
    "2606.17104": ("core", "Prefill/Decode-Aware 评测：按阶段评估加速器，含分离适用性"),

    # ---- M 模型特异性 ----
    "2609.26333": ("core", "Disaggregated Quantization：P 与 D 用不同量化精度（阶段特异性）"),
    "2607.18002": ("core", "ExpertPlex：MoE 的分离式服务，专家并行与 PD 的交互"),
    "2404.09526": ("core", "LoongServe：长上下文场景的弹性分离"),
    "2512.18194": ("core", "TraCT：CXL 共享内存承载 KV，长上下文分离"),
    "2606.19746": ("core", "SAC：稀疏注意力的分离式 KV Cache（CXL）"),
    "2609.31551": ("core", "EAServe：多模态的 Encode 也需分离（EPD）"),
    "2508.15881": ("core", "TPLA：张量并行下的潜在注意力，针对分离优化"),
    "2602.18755": ("core", "DualScale：按阶段分别调频/调并行（能耗视角）"),

    # ---- T 传输与切分机制 ----
    "2606.08635": ("core", "SpectrumKV：逐 token 混合精度的 KV 传输，直接压传输成本"),
    "2605.01708": ("core", "SplitZip：无损 KV 压缩，服务分离场景"),
    "2603.17456": ("core", "Stage-Aware Communication Scheduling：按阶段调度通信"),
    "2607.28633": ("core", "Topology-Aware Data Movement：拓扑感知的 KV 搬运"),
    "2610.41160": ("core", "ARK：KV 传输的路由冲突规避"),
    "2610.29873": ("core", "HAWK：GPU-NPU 异构的 KV 传输"),
    "2609.10790": ("core", "Composable CXL Memory：K8s 原生的共享内存 KV"),

    # ---- 调度与弹性 ----
    "2610.06917": ("core", "FluidPD：原地弹性伸缩，SLO 感知"),
    "2610.16592": ("core", "Prorsa：agentic 负载下的分离潜力"),
    "2609.26763": ("core", "SARA：agentic 负载的分离式资源分配"),
    "2605.02329": ("core", "Taming Request Imbalance：分离式服务的 SLO 调度"),
    "2603.04716": ("core", "SLO-Aware Compute Allocation：分离式资源分配"),
    "2607.02043": ("core", "Load-Aware Prefill Deflection：负载感知的预填充偏转"),
    "2504.09285": ("core", "DynaServe：统一且弹性的分离执行"),
    "2512.11550": ("core", "PD-Swap：在设备内交换 P/D 逻辑，避免跨机传输"),
    "2504.19867": ("core", "semi-PD：阶段内分离式共置，折中路线"),
    "2504.14489": ("core", "Prefill-decode Multiplexing：复用以求高 goodput"),
    "2507.06608": ("core", "Nexus：GPU 内部的 P/D 分离（不跨机）"),
    "2401.11181": ("core", "Inference without Interference：混合负载下分离以避免干扰"),

    # ---- 仿真与规划 ----
    "2603.21354": ("adjacent", "Workload-Router-Pool 架构：部署侧的三层划分"),
    "2610.02732": ("adjacent", "ServeTwin：经基准验证的分布式推理模拟器"),
    "2605.21312": ("adjacent", "Frontier：精确推理模拟，可评估分离配置"),

    # ---- 基准与实现 ----
    "2509.17542": ("adjacent", "分离式 P/D 推理系统（中文团队综述性工作）"),
    "2605.29639": ("adjacent", "RTP-LLM：阿里推理引擎，含分离实践"),
    "2508.02520": ("adjacent", "CloudMatrix384：华为超节点上的分离部署"),
    "2510.08544": ("adjacent", "SPAD：为 P 与 D 分别设计硬件"),
    "2606.29986": ("adjacent", "HBM Is Not All You Need：跨内存层级的分离"),
}


def main() -> int:
    d = json.loads((HERE / "screened_pd.json").read_text(encoding="utf-8"))
    allrows = {r["arxiv_id"]: r for r in d["core"] + d["adjacent"]}

    # ⚠️ 奠基工作白名单：允许绕过 screen_pd.py 的自动判据。
    #
    # 为什么需要：自动判据基于**摘要文本**，而奠基论文常常
    #   · 不用后来流行的术语（Splitwise 摘要只说 "two phases"、
    #     "separate machines"，全文不出现 "prefill"/"decode"）
    #   · 或是相邻问题（Llumnix 是调度论文，摘要无 split/disagg 字样）
    # 若严格按摘要判据，这两篇会被剔除——而整个领域是从它们开始的。
    #
    # 这正是「自动筛选在开创性工作上系统性失效」的具体表现：
    # 术语是它们发明的，当时还不流行，故检索与筛选都抓不住。
    cands = {r["arxiv_id"]: r
             for r in json.loads((HERE / "candidates_pd.json")
                                 .read_text(encoding="utf-8"))}
    for aid in ("2311.18677", "2406.03243"):
        if aid in cands and aid not in allrows:
            allrows[aid] = cands[aid]

    missing = [a for a in KEEP if a not in allrows]
    if missing:
        print(f"[!] KEEP 里有 {len(missing)} 个 ID 不在筛后候选里：{missing}")

    by_layer: dict[str, list] = {"core": [], "adjacent": []}
    for aid, (layer, why) in KEEP.items():
        if aid not in allrows:
            continue
        rec = dict(allrows[aid])
        rec["_layer"] = layer
        rec["_why"] = why
        by_layer[layer].append(rec)

    for layer in by_layer:
        by_layer[layer].sort(key=lambda r: r["published"], reverse=True)

    out = {"core": by_layer["core"], "adjacent": by_layer["adjacent"]}
    (HERE / "included_pd.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")

    print(f"纳入 {len(by_layer['core'])} core + "
          f"{len(by_layer['adjacent'])} adjacent = "
          f"{sum(len(v) for v in by_layer.values())} 篇")
    print(f"（从 88 core 收敛，依据 KEEP 表逐篇给理由）\n")

    # 按主题检查每个子问题是否有材料
    themes = {
        "q1 资源画像": ["Splitwise", "DistServe", "Phase", "prefill"],
        "q2 传输": ["KV", "transfer", "CXL", "Communication", "Data Movement",
                    "Zip", "Spectrum"],
        "q3 切分调度": ["Scheduling", "Elastic", "Multiplex", "Deflection",
                        "semi-PD", "Nexus", "Swap"],
        "q4 模型特异": ["MoE", "LoongServe", "Quantization", "Multimodal",
                        "EAServe", "Latent", "Sparse"],
        "q5 边界": ["When Does", "How Far", "Aggregation or",
                    "Revisiting", "Beyond"],
    }
    print("子问题覆盖检查：")
    for q, kws in themes.items():
        n = sum(1 for r in KEEP
                if any(k.lower() in allrows.get(a, {}).get("title", "").lower()
                       for a in KEEP for k in [kws[0]])
                and any(k.lower() in allrows.get(r, {}).get("title", "").lower()
                        for k in kws))
        hits = [a for a in KEEP
                if any(k.lower() in allrows.get(a, {}).get("title", "").lower()
                       for k in kws)]
        print(f"  {q:<14} {len(hits):>2} 篇")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
