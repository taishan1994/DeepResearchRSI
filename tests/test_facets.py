"""facets 契约的测试：验证「主题无关维度」能替代写死的 sku。

背景：claim.schema.json 原先只有 sku 这一个枚举维度，取值是
ws / mq / se —— 这是 RTX PRO 6000 那一个主题专用的。换个主题
（如 CUDA kernel）就得改 schema。facets 用来解决这个问题：
键值由每个研究自己声明，校验器只检查形态合法性，并把
unspecified 计入欠账统计（沿用 sku 的口径）。

本文件独立于 test_schemas.py，避免在主文件里堆过长内联脚本。
不依赖 pytest：`python tests/test_facets.py`
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi.validate import ValidationError, validate_research_dir  # noqa: E402

FAILURES: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except AssertionError as exc:
        FAILURES.append(f"{name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(f"{name}: 未预期异常 {type(exc).__name__}: {exc}")
    else:
        print(f"[PASS] {name}")


def make_archive(root: Path, claims_rows: list[dict]) -> Path:
    """造一个最小可校验归档。"""
    root.mkdir(parents=True, exist_ok=True)
    (root / "sources.csv").write_text(
        "source_id,url,source_type,trust_tier,fetched_at\n"
        "src-a,https://example.com,academic,primary,2026-11-03T00:00:00Z\n",
        encoding="utf-8",
    )
    with (root / "evidence.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["evidence_id", "source_id", "locator", "quote", "stance"],
        )
        w.writeheader()
        w.writerow({
            "evidence_id": "e-001",
            "source_id": "src-a",
            "locator": "p1",
            "quote": "q",
            "stance": "supports",
        })
    hdr = ["claim_id", "statement", "claim_type", "as_of", "confidence",
           "evidence_ids", "facets", "sku"]
    with (root / "claims.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader()
        for r in claims_rows:
            w.writerow({k: r.get(k, "") for k in hdr})
    return root


def one_claim(facets: str) -> list[dict]:
    return [{
        "claim_id": "c-a",
        "statement": "s",
        "claim_type": "measurement",
        "as_of": "2026-11-03",
        "confidence": "high",
        "evidence_ids": "e-001",
        "facets": facets,
    }]


# ------------------------------------------------------------------ tests
def test_facets_replace_hardcoded_sku() -> None:
    """facets 必须能独立工作：不填 sku 也能通过。"""
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(
            Path(td) / "a",
            one_claim(json.dumps({"precision": "fp16", "batch": "unspecified"})),
        )
        st = validate_research_dir(d)
        assert st["claims"] == 1
        assert st["sku_unspecified"] == 1, f"facets 的 unspecified 未计入：{st}"


def test_facets_multiple_dims() -> None:
    """多个 unspecified 应累加计数（每个维度都算一笔欠账）。"""
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(
            Path(td) / "a",
            one_claim(json.dumps({
                "precision": "unspecified",
                "batch": "unspecified",
                "context_len": "4096",
            })),
        )
        st = validate_research_dir(d)
        assert st["sku_unspecified"] == 2, f"应计 2 笔欠账：{st}"


def test_facets_empty_is_allowed() -> None:
    """facets 是可选字段：留空不应报错（向后兼容只填 sku 的旧归档）。"""
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(Path(td) / "a", one_claim(""))
        st = validate_research_dir(d)
        assert st["claims"] == 1
        assert st["sku_unspecified"] == 0


def test_facets_rejects_bad_json() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(Path(td) / "a", one_claim("{not json"))
        try:
            validate_research_dir(d)
        except ValidationError:
            return
        raise AssertionError("坏的 facets JSON 应被拒绝")


def test_facets_rejects_bad_key() -> None:
    """键必须是 [a-z][a-z0-9_]*，大写开头要拒绝。"""
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(Path(td) / "a", one_claim(json.dumps({"BadKey": "v"})))
        try:
            validate_research_dir(d)
        except ValidationError:
            return
        raise AssertionError("非法 facets 键应被拒绝")


def test_facets_rejects_non_object() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(Path(td) / "a", one_claim("[1,2,3]"))
        try:
            validate_research_dir(d)
        except ValidationError:
            return
        raise AssertionError("facets 为数组时应被拒绝")


def test_facets_rejects_empty_value() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = make_archive(Path(td) / "a", one_claim(json.dumps({"precision": ""})))
        try:
            validate_research_dir(d)
        except ValidationError:
            return
        raise AssertionError("facets 空值应被拒绝")


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        check(fn.__name__, fn)
    print()
    if FAILURES:
        print(f"{len(FAILURES)} 项失败：")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"全部 {len(tests)} 项通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
