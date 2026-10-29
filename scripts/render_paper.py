"""把研究档案渲染成一篇可提交的综述论文。

设计约束（与 validate.py 的 E1/C1 同源）：

1. **不新增事实**。论文里的每个数据点都必须来自 figures/*.csv 或 tables/*.csv，
   而这两类文件的每一行都要声明 `cite` 列指向一个已存在的 claim_id。
   没有 claim_id 的数字不允许进论文。
2. **不重复测量**。渲染器只做「画」和「排版」，不做任何数值推断。
   凡是需要推导的地方，推导过程必须已经写成 claim 的 derivation 字段。
3. **可复现**。同样的 CSV 输入必须产生逐字节相同的 PNG（固定 dpi、固定 seed、
   不写时间戳到图里）。

用法：
    python scripts/render_paper.py research/rtx-pro-6000/paper
    python scripts/render_paper.py research/rtx-pro-6000/paper --check
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DPI = 200
FIGSIZE = {"bar": (7.2, 4.0), "grouped-bar": (8.0, 4.2), "scatter": (6.4, 4.4),
           "line": (7.2, 4.0), "box": (6.4, 4.0), "heatmap": (7.2, 4.4)}
PALETTE = ["#2E5E8C", "#C1553B", "#4F8A5B", "#8A6BB0", "#B08A3E", "#4A7C8C", "#9C4A6E"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def num(row: dict[str, str], key: str, default: float = float("nan")) -> float:
    raw = (row.get(key) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _pick_cjk_font() -> str | None:
    """挑一个真正含中文字形的字体；找不到就返回 None，由调用方决定降级策略。"""
    from matplotlib import font_manager

    wanted = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
              "Noto Sans SC", "Source Han Sans SC", "WenQuanYi Zen Hei",
              "PingFang SC", "Heiti SC", "Arial Unicode MS"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in wanted:
        if name in installed:
            return name
    return None


def setup(require_cjk: bool = True) -> None:
    plt.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": False,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "axes.unicode_minus": False,
    })
    cjk = _pick_cjk_font()
    if cjk:
        plt.rcParams["font.sans-serif"] = [cjk, "DejaVu Sans"]
        plt.rcParams["font.family"] = "sans-serif"
    elif require_cjk:
        raise SystemExit(
            "找不到含中文字形的字体，画出来的标题会是方块。\n"
            "请安装 Microsoft YaHei / SimHei / Noto Sans CJK 之一，"
            "或在 paper.json 里把标题改成英文。"
        )
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def draw_bar(rows, ax, spec):  # noqa: ARG001
    labels = [r["label"] for r in rows]
    vals = [num(r, "value") for r in rows]
    errs = [num(r, "error", 0.0) or 0.0 for r in rows]
    colors = [r.get("color") or PALETTE[i % len(PALETTE)] for i, r in enumerate(rows)]
    pos = np.arange(len(labels))
    ax.bar(pos, vals, color=colors, width=0.62,
           yerr=errs if any(e > 0 for e in errs) else None,
           capsize=3, error_kw={"linewidth": 0.9})
    ax.set_xticks(pos)
    rot = 0 if len(labels) <= 5 else 22
    ax.set_xticklabels(labels, rotation=rot, ha="center" if rot == 0 else "right")
    if rows and rows[0].get("unit"):
        ax.set_ylabel(rows[0]["unit"])

    finite = [v for v in vals if v == v]
    lo, hi = min(finite, default=0.0), max(finite, default=1.0)
    has_neg = lo < 0
    if has_neg:
        ax.axhline(0, color="#333", linewidth=0.9, zorder=2)
    span = (hi - lo) or 1.0
    for p, v in zip(pos, vals):
        if v != v:
            continue
        if has_neg:
            ax.text(p, v + (span * 0.02 if v >= 0 else -span * 0.02), f"{v:g}",
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=7.5)
        else:
            ax.text(p, v + hi * 0.02, f"{v:g}", ha="center", va="bottom", fontsize=7.5)


def draw_grouped_bar(rows, ax, spec):  # noqa: ARG001
    """一行一个 (group, series) 数据点。列：group, series, value[, error]。"""
    groups = list(dict.fromkeys(r["group"] for r in rows))
    series = list(dict.fromkeys(r["series"] for r in rows if r.get("series")))
    width = 0.8 / max(len(series), 1)
    pos = np.arange(len(groups))
    for si, s in enumerate(series):
        vals, errs = [], []
        for g in groups:
            hit = next((r for r in rows if r["group"] == g and r.get("series") == s), None)
            vals.append(num(hit, "value") if hit else float("nan"))
            errs.append(num(hit, "error", 0.0) or 0.0 if hit else 0.0)
        ax.bar(pos + si * width - 0.4 + width / 2, vals, width=width * 0.92,
               label=s, color=PALETTE[si % len(PALETTE)],
               yerr=errs if any(e > 0 for e in errs) else None,
               capsize=3, error_kw={"linewidth": 0.9})
        top = max((v for v in vals if v == v), default=1.0)
        for p, v in zip(pos + si * width - 0.4 + width / 2, vals):
            if v == v:
                ax.text(p, v + top * 0.015, f"{v:g}", ha="center", va="bottom",
                        fontsize=7, rotation=90)
    ax.set_xticks(pos)
    ax.set_xticklabels(groups, rotation=18, ha="right")
    if rows and rows[0].get("unit"):
        ax.set_ylabel(rows[0]["unit"])
    ax.set_ylim(0, max(num(r, "value") for r in rows) * 1.18)
    ax.legend(frameon=False, fontsize=8)


def draw_scatter(rows, ax, spec):  # noqa: ARG001
    for i, r in enumerate(rows):
        ax.scatter(num(r, "x"), num(r, "y"), s=58, color=PALETTE[i % len(PALETTE)],
                   edgecolor="white", linewidth=0.8, zorder=3)
        ax.annotate(r["label"], (num(r, "x"), num(r, "y")),
                    textcoords="offset points", xytext=(5, 4), fontsize=7.5)
    if rows and rows[0].get("xlabel"):
        ax.set_xlabel(rows[0]["xlabel"])
    if rows and rows[0].get("ylabel"):
        ax.set_ylabel(rows[0]["ylabel"])


def draw_line(rows, ax, spec):  # noqa: ARG001
    series = list(dict.fromkeys((r.get("series") or "default") for r in rows))
    for si, s in enumerate(series):
        pts = sorted((num(r, "x"), num(r, "y")) for r in rows
                     if (r.get("series") or "default") == s)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", markersize=4,
                linewidth=1.5, label=s, color=PALETTE[si % len(PALETTE)])
    if rows and rows[0].get("xlabel"):
        ax.set_xlabel(rows[0]["xlabel"])
    if rows and rows[0].get("ylabel"):
        ax.set_ylabel(rows[0]["ylabel"])
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=8)


def draw_box(rows, ax, spec):  # noqa: ARG001
    groups = list(dict.fromkeys(r["label"] for r in rows))
    data = [[num(r, "value") for r in rows if r["label"] == g] for g in groups]
    data = [d for d in data if d]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                    medianprops={"color": "#222", "linewidth": 1.2})
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(PALETTE[i % len(PALETTE)])
        patch.set_alpha(0.75)
    ax.set_xticks(np.arange(1, len(groups) + 1))
    ax.set_xticklabels(groups, rotation=22, ha="right")
    if rows and rows[0].get("unit"):
        ax.set_ylabel(rows[0]["unit"])


def draw_heatmap(rows, ax, spec):  # noqa: ARG001
    cols = list(dict.fromkeys(r["col"] for r in rows))
    rws = list(dict.fromkeys(r["row"] for r in rows))
    grid = np.full((len(rws), len(cols)), np.nan)
    for r in rows:
        grid[rws.index(r["row"]), cols.index(r["col"])] = num(r, "value")
    im = ax.imshow(grid, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, rotation=28, ha="right")
    ax.set_yticks(np.arange(len(rws)))
    ax.set_yticklabels(rws)
    for i in range(len(rws)):
        for j in range(len(cols)):
            v = grid[i, j]
            if v == v:
                ax.text(j, i, f"{v:g}", ha="center", va="center", fontsize=7.5,
                        color="#111")
    ax.grid(False)
    plt.colorbar(im, ax=ax, shrink=0.82)


DRAWERS = {"bar": draw_bar, "grouped-bar": draw_grouped_bar, "scatter": draw_scatter,
           "line": draw_line, "box": draw_box, "heatmap": draw_heatmap}


def render_figure(spec: dict, data_path: Path, out_path: Path) -> None:
    rows = read_csv(data_path)
    if not rows:
        raise SystemExit(f"图表数据为空：{data_path}")
    kind = spec["kind"]
    if kind not in DRAWERS:
        raise SystemExit(f"不支持的图表类型：{kind}")
    fig, ax = plt.subplots(figsize=FIGSIZE.get(kind, (7.2, 4.2)))
    DRAWERS[kind](rows, ax, spec)
    ax.set_title(spec["title"], pad=10)
    # 字体缺字是静默失败：图能存下来，但标题变成方块。
    # 故这里把 matplotlib 的 missing-glyph 警告升级成硬错误。
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    missing = [str(w.message) for w in caught if "missing from font" in str(w.message)]
    if missing:
        raise SystemExit(
            f"{out_path.name} 有 {len(missing)} 个字形缺失，标题会渲染成方块：\n  "
            + "\n  ".join(missing[:4])
        )


def render_table(spec: dict, data_path: Path, out_path: Path) -> str:
    rows = read_csv(data_path)
    if not rows:
        raise SystemExit(f"表格数据为空：{data_path}")
    cols = list(rows[0].keys())
    show = [c for c in cols if not c.startswith("_") and c != "cite"]
    lines = ["| " + " | ".join(show) + " |",
             "|" + "|".join("---" for _ in show) + "|"]
    for r in rows:
        lines.append("| " + " | ".join((r.get(c) or "").strip() for c in show) + " |")
    md = "\n".join(lines) + "\n"
    out_path.write_text(md, encoding="utf-8", newline="\n")
    return md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把研究档案渲染成综述论文的图表与表格")
    ap.add_argument("paper_dir", help="如 research/rtx-pro-6000/paper")
    ap.add_argument("--check", action="store_true", help="只校验不写文件")
    args = ap.parse_args(argv)

    paper_dir = Path(args.paper_dir)
    if not paper_dir.is_dir():
        raise SystemExit(f"目录不存在：{paper_dir}")

    import json
    spec_path = paper_dir / "paper.json"
    if not spec_path.is_file():
        raise SystemExit(f"缺少论文规格：{spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))

    if not args.check:
        setup(require_cjk=(spec.get("language") or "zh") == "zh")

    slug_dir = paper_dir.parent
    claims = {r["claim_id"] for r in
              read_csv(slug_dir / "claims.csv")} if (slug_dir / "claims.csv").is_file() else set()

    fig_dir = paper_dir / "figures"
    tab_dir = paper_dir / "tables"
    fig_dir.mkdir(exist_ok=True)
    tab_dir.mkdir(exist_ok=True)

    problems: list[str] = []
    made = 0

    for fig in spec.get("figures", []):
        data_rel = fig.get("data_file")
        if not data_rel:
            problems.append(f"{fig['figure_id']}: 缺少 data_file")
            continue
        data_path = paper_dir / data_rel
        if not data_path.is_file():
            problems.append(f"{fig['figure_id']}: 数据文件不存在 {data_rel}")
            continue
        rows = read_csv(data_path)
        missing = sorted({r["cite"] for r in rows if r.get("cite")} - claims)
        if missing:
            problems.append(f"{fig['figure_id']}: 引用了不存在的主张 {missing[:3]}")
        no_cite = [i + 2 for i, r in enumerate(rows) if not (r.get("cite") or "").strip()]
        if no_cite:
            problems.append(f"{fig['figure_id']}: 第 {no_cite[:5]} 行没有 cite 列")
        if args.check:
            continue
        out = fig_dir / (fig.get("output") or f"{fig['figure_id']}.png")
        render_figure(fig, data_path, out)
        made += 1

    for tab in spec.get("tables", []):
        data_rel = tab.get("data_file")
        if not data_rel:
            problems.append(f"{tab['table_id']}: 缺少 data_file")
            continue
        data_path = paper_dir / data_rel
        if not data_path.is_file():
            problems.append(f"{tab['table_id']}: 数据文件不存在 {data_rel}")
            continue
        rows = read_csv(data_path)
        missing = sorted({r["cite"] for r in rows if r.get("cite")} - claims)
        if missing:
            problems.append(f"{tab['table_id']}: 引用了不存在的主张 {missing[:3]}")
        if args.check:
            continue
        render_table(tab, data_path, tab_dir / f"{tab['table_id']}.md")
        made += 1

    for p in problems:
        print("  - " + p)
    if problems:
        print(f"[FAIL] {len(problems)} 个问题")
        return 1
    if args.check:
        print(f"[OK]   {len(spec.get('figures', []))} 图 / "
              f"{len(spec.get('tables', []))} 表，全部有 claim 支撑")
    else:
        print(f"[OK]   生成 {made} 个图表文件 -> {paper_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
