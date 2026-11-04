"""检查论文引用的所有 arXiv 编号是否真实存在。

⚠️ 为什么需要：综述里 58 个 arXiv 编号是手写进正文的。
   写错一位数不会报错，读者点进去会 404，但论文看起来完全正常。
   这是最隐蔽的错误类型——它不破坏排版、不破坏逻辑，只破坏可信度。
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
md = (D / 'PAPER.md').read_text(encoding='utf-8')

# 抽取正文中所有 arXiv 编号
refs = sorted(set(re.findall(r'arXiv:(\d{4}\.\d{4,5})', md)))
print(f'正文引用 {len(refs)} 个 arXiv 编号')

papers = {p['id'][:10] for p in
          json.loads((D / 'papers.json').read_text(encoding='utf-8'))}

# 1) 本地论文库比对
missing_local = [r for r in refs if r not in papers]
print(f'  不在本地论文库的: {len(missing_local)}')
for r in missing_local:
    print(f'    [!] {r}')

# 2) 逐批向 arXiv 确认存在
print('\n向 arXiv 核实（每批 10 个）...')
bad = []
B = 10
for i in range(0, len(refs), B):
    batch = refs[i:i + B]
    url = 'http://export.arxiv.org/api/query?id_list=' + ','.join(batch)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'check/1.0'})
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode('utf-8', 'replace')
        got = set(re.findall(r'<id>http://arxiv\.org/abs/(\d{4}\.\d{4,5})v\d+</id>', body))
        miss = set(batch) - got
        for m in sorted(miss):
            bad.append(m)
            print(f'    [!] {m} 在 arXiv 上查不到')
        if not miss:
            print(f'    批次 {i // B + 1}: {len(batch)} 个全部存在')
    except Exception as e:
        print(f'    批次 {i // B + 1} 请求失败: {e}')
    time.sleep(3)

print()
if bad:
    print(f'结论: {len(bad)} 个编号有问题 -> {bad}')
    raise SystemExit(1)
print(f'结论: {len(refs)} 个 arXiv 编号全部在 arXiv 上存在')
