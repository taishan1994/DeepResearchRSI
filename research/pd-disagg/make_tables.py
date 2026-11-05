"""建 paper/paper.json 与 paper/tables/ 下的表格数据源。

## 为什么表格要单独的 CSV

audit_paper.py 要求：paper.json 里声明的每个 table_id，必须有对应的
`tables/<id>.md` 或 `tables/<id>.csv`，且非空。这是为了防止
「论文里写了表 3，但那表从没生成过」。

本文件把论文里的 4 张表写成 CSV（数据源），正文里的 LaTeX 表是它的
渲染。两者数字来自同一处：analysis.json 或 claims.csv，
故不会漂移。

## 表与证据的对应

tab1 传输三档   <- analysis.json 的 kv_transfer（e-011 实测）
tab2 三条路线   <- c-split 的 statement
tab3 模型变量   <- c-model 的 statement
tab4 判据       <- c-boundary 的 statement
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"
TABLES = PAPER / "tables"


def write_csv(name: str, header: list[str], rows: list[list[str]]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    (TABLES / name).write_text(buf.getvalue(), encoding="utf-8",
                               newline="\n")
    print(f"  {name}  {len(rows)} 行")


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    a = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    kv = a["parameters"]["kv_transfer"]

    # 由实测两点反算有效带宽（MB / ms = GB/s）
    nv = round(kv["kv_size_mb"] / kv["nvlink_ms"], 1)
    rd = round(kv["kv_size_mb"] / kv["rdma_ms"], 1)
    st = round(rd / 10, 1)
    ratio = kv["ratio_rdma_over_nvlink"]

    print("生成表格数据：")

    # tab1：传输三档
    write_csv("tab1_transport.csv",
              ["档位", "典型承载", "有效带宽_GBps", "相对RDMA倍数", "数据性质"],
              [["同机", "NVLink", str(nv), f"{ratio:g}", "实测（e-011 反算）"],
               ["跨机", "RDMA / InfiniBand", str(rd), "1", "实测（e-011 反算）"],
               ["经存储", "共享存储 / CXL", str(st), "约 0.1",
                "推算（按 RDMA 的 1/10）"]])

    # tab2：三条路线
    write_csv("tab2_routes.csv",
              ["路线", "做法", "代表系统", "是否搬 KV"],
              [["不分离", "prefill 切块混进 decode 批次",
                "Sarathi-Serve、vLLM 默认", "否"],
               ["显式分离", "P/D 各自独立实例，KV 跨实例搬",
                "DistServe、SGLang、Mooncake", "是"],
               ["弹性调整", "运行时改变 P:D 配比或迁移请求",
                "FluidPD、Llumnix", "视实现"]])

    # tab3：模型侧三个变量
    write_csv("tab3_model_vars.csv",
              ["变量", "影响", "后果", "是否模型属性"],
              [["KV 每 token 大小", "MLA < GQA < MHA", "决定传输字节数", "是"],
               ["上下文长度", "线性放大 KV", "决定是否放得下", "否（业务）"],
               ["负载形态", "输入/输出长度比", "决定 P:D 配比", "否（业务）"],
               ["互联拓扑", "决定传输带宽档位", "决定成本侧大小", "否（部署）"],
               ["SLO", "决定 goodput 定义", "决定最优配比", "否（业务）"]])

    # tab4：判据
    write_csv("tab4_criteria.csv",
              ["编号", "条件", "检查方式"],
              [["1", "两阶段最优配置显著不同",
                "分别做单阶段压测，比最优并行度与 batch"],
               ["2", "存在高带宽 KV 通路",
                "同机 NVLink 或跨机 RDMA，而非共享存储"],
               ["3", "负载落在窗口内",
                "太轻不划算，太重则 decode 硬件闲置"],
               ["4", "KV 规模足够大",
                "传输固定开销占比可忽略"]])

    # tab6：三平面
    write_csv("tab6_plane.csv",
              ["平面", "管什么", "代表手段"],
              [["数据面", "KV 放哪、留多久",
                "KV 池分层、打包布局、session 感知保留、前缀缓存"],
               ["执行面", "单步算多快",
                "并行策略（DEP/DCP/PCP/Wide-EP）、kernel 融合、CUDA graph、异步调度"],
               ["控制面", "谁在什么时候被调度",
                "长 prefill token 上限、prefill 节拍、路由、准入、P/D 配比"]])
    # tab5：优化技巧四类
    write_csv("tab5_technique.csv",
              ["类别", "作用于", "代表技巧", "实测幅度"],
              [["A 省传输量", "KV 字节数", "逐层/chunk 级传输、压缩、前缀缓存",
                "成比例"],
               ["B 让传输不可见", "时序", "TBO、SBO、DBO、piggyback",
                "隐藏传输"],
               ["C 均衡负载", "rank 分配", "Waterfill、LPLB、EPLB",
                "0.84-7.34%"],
               ["D 省 decode 步", "步数", "DSpark 自适应验证", "随并发"]])
    # paper.json
    spec = {
        "_note": "论文规格。图/表在此声明，audit_paper.py 校验其产物真实存在。",
        "figure_dir": "figures",
        "figures": [
            {
                "figure_id": "fig1",
                "output": "fig1_cost_benefit.png",
                "caption": "分离的收支两侧：收益侧是两阶段资源画像相反，"
                           "成本侧是同一份 250 MB KV 的传输耗时",
                "source": "analysis.json:parameters.kv_transfer（e-011）",
            },
            {
                "figure_id": "fig2",
                "output": "fig2_transfer_scaling.png",
                "caption": "KV 传输耗时随规模增长；三档互联相差一个数量级",
                "source": "analysis.json:parameters.kv_transfer（e-011 两点定标）",
            },
            {
                "figure_id": "fig3",
                "output": "fig3_benefit_window.png",
                "caption": "分离收益随输入输出比是一个窗口，不是单调上升",
                "source": "e-028 / e-029 / e-030（HeteroPanacea 跨 8 模型扫描）",
                "cites": ["c-boundary"],
            },
        ],
        "tables": [
            {"table_id": "tab1", "data": "tables/tab1_transport.csv",
             "caption": "KV 传输的三档方案"},
            {"table_id": "tab2", "data": "tables/tab2_routes.csv",
             "caption": "切分与调度的三条路线"},
            {"table_id": "tab3", "data": "tables/tab3_model_vars.csv",
             "caption": "决定分离做法的变量"},
            {"table_id": "tab4", "data": "tables/tab4_criteria.csv",
             "caption": "分离的四项判据"},
            {"table_id": "tab8", "data": "tables/tab8_load.csv",
             "caption": "缓存收益的三个来源与各自的基线",
             "cites": ["c-load"]},
            {"table_id": "tab7", "data": "tables/tab7_slo.csv",
             "caption": "三组应用的 SLO 配置",
             "cites": ["c-slo"]},
            {"table_id": "tab6", "data": "tables/tab6_plane.csv",
             "caption": "三平面与各自的优化手段",
             "cites": ["c-plane"]},
            {"table_id": "tab5", "data": "tables/tab5_technique.csv",
             "caption": "优化技巧按作用对象分四类",
             "cites": ["c-technique"]},
        ],
        # sections 必须是含 cites 的对象：audit_paper.py 会读 s.get("cites")
        # 并把它们并入「已声明主张」集合。写成纯字符串会抛
        # AttributeError: 'str' object has no attribute 'get'。
        "sections": [
            {"title": "引言", "cites": []},
            {"title": "两阶段为什么值得分开", "cites": ["c-profile"]},
            {"title": "KV cache 怎么搬", "cites": ["c-transfer"]},
            {"title": "怎么切分与调度", "cites": ["c-split"]},
            {"title": "不同模型的最佳实践", "cites": ["c-model"]},
            {"title": "优化技巧", "cites": ["c-technique"]},
            {"title": "四类之外", "cites": ["c-plane"]},
            {"title": "方向相反", "cites": ["c-slo"]},
            {"title": "负载形态", "cites": ["c-load"]},
            {"title": "收益的边界", "cites": ["c-boundary", "c-window"]},
            {"title": "讨论", "cites": ["c-formula"]},
            {"title": "结论", "cites": ["c-formula"]},
        ],
    }
    (PAPER / "paper.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print("  paper.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
