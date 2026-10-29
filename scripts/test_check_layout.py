"""check_layout.py 的负向测试：真的把渲染器改回有缺陷的版本，确认 check_layout.py 能拦住。

做法不是伪造 PDF，而是**真的把渲染器改回有缺陷的版本**：
关闭表格的 auto_page_break 修复，重新生成一份，跑检查，再恢复。
这样测的是真实缺陷，不是模拟的。
"""

import shutil
import subprocess
import sys
from pathlib import Path

RENDER = Path('scripts/render_paper_pdf.py')
PDF = Path('research/rtx-pro-6000/paper/PAPER.pdf')
BAK_R = Path('D:/github/_render_bak.py')
BAK_P = Path('D:/github/_pdf_bak.pdf')

shutil.copy2(RENDER, BAK_R)
shutil.copy2(PDF, BAK_P)

try:
    s = RENDER.read_text(encoding='utf-8')
    # 还原成 r260 的写法：不关自动分页，单元格折行余量为 1
    broken = s.replace(
        '        prev_auto = self.auto_page_break\n'
        '        self.set_auto_page_break(False)\n'
        '        try:\n'
        '            for ri, r in enumerate(rows):\n'
        '                self._table_row(ri, r, ncol, widths)\n'
        '        finally:\n'
        '            self.set_auto_page_break(prev_auto)',
        '        for ri, r in enumerate(rows):\n'
        '            self._table_row(ri, r, ncol, widths)', 1)
    broken = broken.replace('UNIT_MM_PER_HALF_CJK)) - 2, 4)', 'UNIT_MM_PER_HALF_CJK)) - 1, 4)', 1)
    assert broken != s, '未能还原缺陷版本'
    RENDER.write_text(broken, encoding='utf-8', newline='\n')

    subprocess.run([sys.executable, 'scripts/render_paper_pdf.py',
                    'research/rtx-pro-6000/paper'],
                   capture_output=True, text=True, encoding='utf-8')
finally:
    shutil.copy2(BAK_R, RENDER)
    BAK_R.unlink()

# 现在检查这份「有缺陷」的 PDF
r = subprocess.run([sys.executable, 'scripts/check_layout.py', str(PDF)],
                   capture_output=True, text=True, encoding='utf-8')
print('--- 缺陷版 PDF 的检查结果 ---')
print(r.stdout)
print('退出码:', r.returncode)

caught = r.returncode != 0
print('能否拦住:', '能' if caught else '不能')

# 恢复正确 PDF
shutil.copy2(BAK_P, Path('research/rtx-pro-6000/paper/PAPER.pdf'))
BAK_P.unlink()

r2 = subprocess.run([sys.executable, 'scripts/check_layout.py', str(PDF)],
                    capture_output=True, text=True, encoding='utf-8')
print('\n--- 恢复后 ---')
print(r2.stdout.strip().split('\n')[-1])

sys.exit(0 if caught and r2.returncode == 0 else 1)
