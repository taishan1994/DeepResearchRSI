"""修掉 evidence 元组列表里「多出来的那一层 ) ,」。

背景：本仓库的批量脚本用「元组列表」写 CSV 行，形如

    ev = [
        (
            'e-id', 'doc-id', 'src-id',
            flat('''...'''),
            'locator',
            'supports'),
        ),
        (
            ...
        ),
    ]

最后两行 —— `'supports'),` 紧跟一行 `),` —— 是**语法错误**：
元组已经被 `'supports'),` 闭合，那一行 `),` 是多余的。
这个错误在本仓库至少出现过 12 次（第 152–173 轮）。

用法:
    python scripts/_fix_stray_closer.py scripts/_zzNNx.py

它只删除「上一行恰好是 'supports'), 而本行是 ),」的那些行，
并且要求至少删掉一行，否则拒绝写入（避免误伤已经正确的文件）。
"""
import py_compile
import sys
from pathlib import Path

CLOSER = "'supports'),"
STRAY = '),'


def fix(path: Path) -> int:
    lines = path.read_text(encoding='utf-8').split('\n')
    out = []
    removed = 0
    for i, ln in enumerate(lines):
        if ln.strip() == STRAY and i > 0 and lines[i - 1].strip() == CLOSER:
            removed += 1
            continue
        out.append(ln)
    if removed == 0:
        return 0
    path.write_text('\n'.join(out), encoding='utf-8', newline='\n')
    return removed


def main() -> int:
    targets = sys.argv[1:]
    if not targets:
        print('用法: python scripts/_fix_stray_closer.py <file.py> [...]')
        return 2
    rc = 0
    for t in targets:
        p = Path(t)
        n = fix(p)
        if n:
            print('%s: 删除 %d 行多余闭合' % (p, n))
        else:
            print('%s: 无多余闭合（未改动）' % p)
        try:
            py_compile.compile(str(p), doraise=True)
            print('%s: 编译通过' % p)
        except py_compile.PyCompileError as exc:
            print('%s: 编译失败 -> %s' % (p, exc))
            rc = 1
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
