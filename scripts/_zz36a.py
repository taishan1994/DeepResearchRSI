"""测量 Prism tokens.estimate 的兜底启发式在中文上的低估幅度。

Prism/src/prism/tokens.py 第 26-27 行：
    # Heuristic: ~4 chars per token, min 1 token for any non-empty text.
    return max(1, len(text) // 4)

本脚本不依赖 tiktoken（未安装），
故用「一个汉字约等于 1 token」这个保守参考比，
以及用本仓库自己的 REPORT.md 中文段落做样本。
"""


def estimate(text):
    """逐字复制 Prism/src/prism/tokens.py 第 20-27 行的无依赖分支。"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def cjk_ratio(text):
    n = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return n / max(1, len(text))


samples = {
    '纯 ASCII（英文代码风格）':
        'def compute_total(items): return sum(i.price for i in items)\n',
    '纯中文（一句技术判断）':
        '当一个精确率指标的分子可以由不含任何正确答案的输入产生时，'
        '它量的是词汇重叠，而不是检索。',
    '中英混排（本报告典型段落）':
        '`Prism/src/prism/packer.py` 第 288-289 行写 `used += t` 与 '
        '`pkg.fits_in = used`，其中 `t` 是含 `full_source` 的估算。',
    '纯 ASCII 长文本（README 风格）':
        'The compiler and test runner are a free big model: '
        'they catch what a small model misses. ' * 3,
}

print('=' * 74)
print('Prism tokens.estimate 的兜底分支：max(1, len(text) // 4)')
print('=' * 74)
print('%-30s %7s %7s %8s %8s' % ('样本', '字符', 'estimate', '汉字比', '汉字数'))
print('-' * 74)
rows = []
for name, text in samples.items():
    e = estimate(text)
    r = cjk_ratio(text)
    n = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    rows.append((name, len(text), e, r, n))
    print('%-30s %7d %7d %7.2f %8d' % (name, len(text), e, r, n))

print()
print('=' * 74)
print('关键推论')
print('=' * 74)
cjk_only = [r for r in rows if r[0].startswith('纯中文')][0]
print('纯中文样本：%d 字符 -> estimate = %d' % (cjk_only[1], cjk_only[2]))
print('  若按「一个汉字约 1 token」这个保守参考，真实约 %d token' % cjk_only[4])
print('  低估倍数约 %.2fx' % (cjk_only[4] / max(1, cjk_only[2])))
print()
print('成因：len(text) 数的是「字符数」，而码点 1 个 = 1 个字符，')
print('      故一个汉字被当成 0.25 个 token；')
print('      而主流 tokenizer 里一个汉字通常是 1 到 2 个 token。')
print()
print('故 Prism 的 token_budget 在中文任务上是一个「乐观上界」：')
print('  声明 6000 token 的预算，实际可能装进 15000 到 24000 token 的文本。')
