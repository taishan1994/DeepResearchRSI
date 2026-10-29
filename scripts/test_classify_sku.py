"""sku 分类器的回归用例。

每一条都对应一次真实发生过的误判（或一次险些发生的误判）。
新增规则时必须先让这些继续通过。

用法：python scripts/test_classify_sku.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_sku import classify  # noqa: E402

# (说明, statement, evidence_text, 期望 sku)
CASES = [
    ('RTX 6000D 是独立产品，不是第四个 SKU',
     'RTX 6000D 显存削减为 448-bit / 84GB。',
     '',
     'na'),
    ('陈述讲的是 PRO 5000，证据顺带提到 6000，不应算 unspecified',
     'RTX PRO 5000 72GB 版除显存容量外规格与 48GB 版一致。',
     'RTX PRO 6000 有 96GB',
     'na'),
    ('PRO 4500 的 Workstation Edition 不能算成 6000 的 ws（干扰项远离产品名）',
     'RTX PRO 6000 双卡扩展开销很低。',
     'RTX PRO 6000 1x 4,962 tok/s 404.6W。                                                                                RTX PRO 4500 Workstation Edition 1x 2,777 289.8W',
     'unspecified'),
    ('完整 SKU 名可以离得远一些',
     'RTX PRO 6000 存在成熟的 llama.cpp 路径。',
     'GPU: NVIDIA RTX PRO 6000 Blackwell Server Edition ... sm_120a',
     'se'),
    ('WS 后跟「的」也是 WS',
     '已发生 RTX PRO 6000 WS 的 16-pin 熔毁案例。',
     '',
     'ws'),
    ('WS<->5090 是对照标注，不是 SKU',
     'Pro 6000 与 5090 的渲染差距很小。',
     '这与两源 WS<->5090 比值（+13.9% / +8.4%）方向一致',
     'unspecified'),
    ('Pro WS 是主板型号，不是 SKU',
     '测试平台为 ASUS Pro WS WRX90E-SAGE，插 16 张 RTX PRO 6000。',
     '',
     'unspecified'),
    ('显式三个 SKU',
     '三款 RTX PRO 6000 均支持 MIG。',
     '',
     'all'),
    ('Max-Q 与 Workstation Edition 同时出现',
     'RTX PRO 6000 Max-Q 与 Workstation Edition 整卡功耗差异很大。',
     '',
     'mq+ws'),
    ('只有 Max-Q 一个 SKU',
     'RTX PRO 6000 Max-Q 的整卡功耗仅 99.3 W。',
     '',
     'mq'),
]


def main() -> int:
    failures = []
    for why, stmt, ev, want in CASES:
        got, reason = classify(stmt, ev)
        mark = "OK  " if got == want else "FAIL"
        print(f"  [{mark}] want={want:<12} got={got:<12} {why}")
        if got != want:
            failures.append(f"{why}: want {want}, got {got} ({reason})")
    print(f"\n{len(CASES) - len(failures)}/{len(CASES)} 通过")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
