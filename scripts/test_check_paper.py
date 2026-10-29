"""check_paper.py 的负向测试：故意注入缺陷，确认每条都能拦住，确认 check_paper.py 每条都能拦住。

只读原文件、在副本上改、跑检查、恢复。不修改真实 PAPER.md。

一个检查器如果只会在正确输入上说 OK，它就不是检查器，是印章。
用法：python scripts/test_check_paper.py
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

PAPER = Path('research/rtx-pro-6000/paper/PAPER.md')
BAK = Path('D:/github/_paper_bak.md')

shutil.copy2(PAPER, BAK)
orig = PAPER.read_text(encoding='utf-8')

CASES = [
    ('I1 章号跳号', lambda t: t.replace('## 5　DeepSeek', '## 7　DeepSeek', 1)),
    ('I2 小节错章', lambda t: t.replace('### 3.2　往上比', '### 4.2　往上比', 1)),
    ('I3 表标题跳号', lambda t: t.replace('*表 5　买得起', '*表 8　买得起', 1)),
    ('I5 主张数过期', lambda t: re.sub(r'本文引用的 \d+ 条主张', '本文引用的 99 条主张', t, 1)),
    ('I5 unspecified 过期',
     lambda t: re.sub(r'有 \*\*\d+ 条是 `unspecified`\*\*', '有 **77 条是 `unspecified`**', t, 1)),
]

results = []
try:
    for name, mutate in CASES:
        mutated = mutate(orig)
        if mutated == orig:
            results.append((name, 'SKIP', '变异未生效'))
            continue
        PAPER.write_text(mutated, encoding='utf-8', newline='\n')
        r = subprocess.run([sys.executable, 'scripts/check_paper.py'],
                           capture_output=True, text=True, encoding='utf-8')
        caught = r.returncode != 0
        # 找出触发的哪条
        hit = [l.strip() for l in r.stdout.split('\n') if '[FAIL]' in l]
        results.append((name, 'CAUGHT' if caught else 'MISSED',
                        hit[0] if hit else ''))
finally:
    shutil.copy2(BAK, PAPER)
    BAK.unlink()
    print('已恢复原文件')

print()
for name, verdict, detail in results:
    mark = 'OK  ' if verdict == 'CAUGHT' else ('SKIP' if verdict == 'SKIP' else 'FAIL')
    print(f'  [{mark}] {name:<24} {detail[:78]}')

missed = [r for r in results if r[1] == 'MISSED']
print(f'\n{len(results) - len(missed)}/{len(results)} 缺陷被拦下')
sys.exit(1 if missed else 0)
