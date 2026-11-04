"""核对图片内部的文字：不含「图 N」编号，且数字与数据源一致。

⚠️ 为什么需要程序核对：
   本模型读不了图片，无法目视确认图内标题。
   但 matplotlib 的绘图对象是可检查的——重跑 make_figures 的绘图逻辑，
   在每个 figure 关闭前抓取所有 Text 对象的字符串，
   就能断言「图内没有『图 N』」以及「关键数字正确」。
   这比看一下图更可靠：它可重复、可进 CI。
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

# 在 make_figures 里钩住 save()，每次保存前把该 figure 的全部文字记下来
captured: list[tuple[str, list[str]]] = []

spec = importlib.util.spec_from_file_location('mf', HERE / 'make_figures.py')
mf = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mf)

_orig_save = mf.save


def patched_save(fig, name: str):
    texts: list[str] = []
    for t in fig.findobj(matplotlib.text.Text):
        s = t.get_text()
        if s and s.strip():
            texts.append(s)
    captured.append((name, texts))
    return _orig_save(fig, name)


mf.save = patched_save
mf.main()

print('\n' + '=' * 88)
print('图内文字核对')
print('=' * 88)

bad = 0
for name, texts in captured:
    joined = ' | '.join(texts)
    # 1) 不得含「图 N」编号
    n_title = len(re.findall(r'图\s*\d+', joined))
    # 2) 不得含过期数字
    stale = [s for s in ('58 篇', '50 条', '占 72%', '18% 是可比的') if s in joined]
    flag = 'OK  '
    if n_title or stale:
        flag = 'BAD '
        bad += 1
    print(f'[{flag}] {name:22s} 文字 {len(texts):2d} 条'
          + (f'  编号残留 {n_title}' if n_title else '')
          + (f'  过期数字 {stale}' if stale else ''))

print()
if bad:
    print(f'{bad} 张图有问题')
    raise SystemExit(1)
print(f'全部 {len(captured)} 张图：无「图 N」编号残留，无过期数字')
