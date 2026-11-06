"""把快照压成可读的证据摘要（digest）。"""
from __future__ import annotations
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

def clean(text: str) -> str:
    # HTML->text 后每行被切断，且表格单元格带 | 与换行。先合并成段落。
    text = text.replace("\u2009", " ").replace("\u00a0", " ")
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text

def sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)
    for p in parts:
        p = p.strip()
        if not (60 <= len(p) <= 420):
            continue
        if p.count("|") >= 2:
            continue
        # 代码/公式碎片：符号密度过高
        sym = sum(1 for ch in p if ch in "{}[]<>\\=;")
        if sym > 0.03 * len(p):
            continue
        if len(re.findall(r"[A-Za-z]", p)) < 0.45 * len(p):
            continue
        yield p

PAT = {
    "X": r"\d+(?:\.\d+)?\s*(?:x|X|\u00d7)",
    "%": r"\d+(?:\.\d+)?\s*%",
    "FB": r"feedback|reward|verif|correctness|unit test|profil|counter|roofline",
    "IT": r"iterat|round|trial|rollout|budget",
    "CO": r"cost|token|GPU hour|wall-clock|overhead|expensive|budget",
    "BL": r"baseline|compared|outperform|beat|torch\.compile|cuBLAS|PyTorch",
}

def score(s: str):
    hits = [k for k, p in PAT.items() if re.search(p, s, re.I)]
    return hits

def main():
    inc = json.loads((HERE / "included_rsi.json").read_text(encoding="utf-8"))
    out = []
    for c in inc["core"]:
        aid = c["arxiv_id"]
        stem = "doc-arxiv-" + aid.replace(".", "-")
        full = DOCS / f"{stem}-full.txt"
        snap = full if full.is_file() else DOCS / f"{stem}.txt"
        if not snap.is_file():
            continue
        text = clean(snap.read_text(encoding="utf-8"))
        kind = "full" if snap is full else "abs"
        seen = set()
        picks = []
        for s in sentences(text):
            if s in seen:
                continue
            h = score(s)
            # 必须含一个硬数（倍数或百分比）+ 一个语境信号，或三个语境信号
            hard = ("X" in h) or ("%" in h)
            ctx = len([k for k in h if k in ("FB", "IT", "CO", "BL")])
            if not ((hard and ctx >= 1) or ctx >= 3):
                continue
            seen.add(s)
            picks.append((len(h), s, h))
        picks.sort(key=lambda x: -x[0])
        picks = picks[:22]
        out.append(f"{aid} [{kind}] {c['title'][:90]}  ({c['topic']})")
        for _, s, h in picks:
            out.append(f"  - {s}")
        out.append("")
    (HERE / "digest.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(len(out), "lines")

if __name__ == "__main__":
    main()