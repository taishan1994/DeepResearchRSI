"""从快照里按「锚点子串」定位证据，并生成 evidence.csv。

设计要点：**引文由脚本从快照里切出来，不由人手写**。
手写引文必然漂移（漏一个逗号、把 however 写成 but），而 E1 只认字面子串——
漂移的后果是校验失败；更糟的是有人为了让它过而把校验放宽。

故这里的流程是：给一个**一定存在于原文**的短锚点，脚本向两侧扩窗到句子边界，
再把切出来的整段写进 evidence.csv。锚点找不到就直接报错退出，不静默跳过。

⚠️ 中文语料的句子边界与英文不同：`。` 后面不带空格，`\n\n` 也未必出现
（微信文档是逐标签换行的一行一句）。故 CJK 的断句符单独列一组，
且最小引文长度按字符数而非词数设——中文 120 字已经相当于英文 300+ 字符。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_QUOTE = 120

# (evidence_id, document_id, source_id, anchor, locator, stance)
SPEC: list[tuple[str, str, str, str, str, str]] = [
    # ============ 微信公众号：draft/add ============
    ("e-wx-draft-purpose", "doc-wx-draft-add", "src-wx-draft-add",
     "本接口用于新增常用的素材到草稿箱。",
     "新增草稿 / 接口说明", "supports"),
    ("e-wx-draft-removed", "doc-wx-draft-add", "src-wx-draft-add",
     "1.上传到草稿箱中的素材被群发或发布后，该素材将从草稿箱中移除。",
     "新增草稿 / 接口说明 · 注意事项 1", "supports"),
    ("e-wx-draft-title-limit", "doc-wx-draft-add", "src-wx-draft-add",
     "标题，总长度不超过32个字",
     "新增草稿 / 请求体 articles.title", "supports"),
    ("e-wx-draft-content-limit", "doc-wx-draft-add", "src-wx-draft-add",
     "图文消息的具体内容，支持HTML标签，必须少于2万字符",
     "新增草稿 / 请求体 articles.content", "supports"),
    ("e-wx-draft-img-whitelist", "doc-wx-draft-add", "src-wx-draft-add",
     "外部图片url将被过滤",
     "新增草稿 / 请求体 articles.content · 图片 URL 限制", "supports"),
    ("e-wx-draft-server-only", "doc-wx-draft-add", "src-wx-draft-add",
     "接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用",
     "新增草稿 / 调用方式前说明", "supports"),
    ("e-wx-draft-scope", "doc-wx-draft-add", "src-wx-draft-add",
     "其他未明确声明的账号类型，如无特殊说明，均不可调用此接口。",
     "新增草稿 / 7. 适用范围", "supports"),

    # ============ 微信公众号：freepublish/submit ============
    ("e-wx-pub-purpose", "doc-wx-freepublish", "src-wx-freepublish",
     "本接口用于将图文草稿提交发布。",
     "发布草稿 / 接口说明", "supports"),
    ("e-wx-pub-async", "doc-wx-freepublish", "src-wx-freepublish",
     "此时只意味着发布任务提交成功，并不意味着此时发布已经完成",
     "发布草稿 / 4. 注意事项", "supports"),
    ("e-wx-pub-event", "doc-wx-freepublish", "src-wx-freepublish",
     "由于发布任务提交后，发布任务可能在一定时间后才完成",
     "发布草稿 / 4. 注意事项 · 事件推送", "supports"),
    ("e-wx-pub-certified-only", "doc-wx-freepublish", "src-wx-freepublish",
     "仅认证：表示仅允许企业主体已认证账号调用，未认证或不支持认证的账号无法调用。",
     "发布草稿 / 7. 适用范围", "supports"),
    ("e-wx-pub-48001", "doc-wx-freepublish", "src-wx-freepublish",
     "48001",
     "发布草稿 / 6. 错误码 · api unauthorized", "supports"),

    # ============ 小红书开放平台 ============
    ("e-xhs-nav-categories", "doc-xhs-open-nav", "src-xhs-open-nav",
     'navigationName\\":\\"公共API',
     "open.xiaohongshu.com /api/doc/list · 全部分类", "supports"),
    ("e-xhs-thirdparty-notes", "doc-xhs-tencent", "src-xhs-tencent",
     "小红书提供了官方开放平台 API",
     "腾讯云社区 / 概述", "supports"),

    # ============ 知乎开放平台 ============
    ("e-zhihu-published-only", "doc-zhihu-api-ref", "src-zhihu-api-ref",
     "仅支持本人**已发布**的内容；草稿、未发布或其他不可用状态的内容不在支持范围内。",
     "§11 创作能力 / 通用约定", "supports"),
    ("e-zhihu-own-only", "doc-zhihu-api-ref", "src-zhihu-api-ref",
     "仅支持当前 Access Secret 所属账号的本人数据",
     "§11 创作能力 / 通用约定", "supports"),
    ("e-zhihu-section-list", "doc-zhihu-api-ref", "src-zhihu-api-ref",
     "### 11.1 API：`user_content_detail`（我的创作全文）",
     "§11.1 / 创作能力接口为只读", "context"),
    ("e-zhihu-quota", "doc-zhihu-api-ref", "src-zhihu-api-ref",
     "默认每个租户每个自然日共计 100 次",
     "§11 创作能力 / 通用约定 · 额度", "supports"),
    ("e-zhihu-risk-reject", "doc-zhihu-api-ref", "src-zhihu-api-ref",
     "30003 请求被风控拒绝",
     "§11 通用错误码", "supports"),

    # ============ Wechatsync ============
    ("e-ws-not-crawler", "doc-wechatsync-readme", "src-wechatsync-readme",
     "**文章同步助手不是爬虫，不模拟登录，不经过任何第三方服务器。**",
     "README / 工作原理", "supports"),
    ("e-ws-cookie", "doc-wechatsync-readme", "src-wechatsync-readme",
     "扩展直接使用浏览器中已有的 Cookie，无需额外授权，无需输入密码",
     "README / 工作原理 · 1", "supports"),
    ("e-ws-webapi", "doc-wechatsync-readme", "src-wechatsync-readme",
     "发布文章时，扩展调用的是各平台 Web 编辑器使用的同一套官方 API",
     "README / 工作原理 · 2", "supports"),
    ("e-ws-draft-first", "doc-wechatsync-readme", "src-wechatsync-readme",
     "**草稿优先**：默认将文章同步为草稿，发布前由你人工确认，不会自动发布",
     "README / 工作原理 · 4", "supports"),
    ("e-ws-29plus", "doc-wechatsync-readme", "src-wechatsync-readme",
     "一键同步微信公众号文章到知乎、头条、掘金、小红书、CSDN 等 29+ 平台",
     "README / 首段", "supports"),
    ("e-ws-platform-zhihu", "doc-wechatsync-readme", "src-wechatsync-readme",
     "| 知乎 | zhihu | 主流自媒体 | ✅ |",
     "README / 支持 29+ 主流平台 表", "supports"),
    ("e-ws-platform-xhs", "doc-wechatsync-readme", "src-wechatsync-readme",
     "| 小红书 | xiaohongshu | 主流自媒体 | ✅ |",
     "README / 支持 29+ 主流平台 表", "supports"),
    ("e-ws-license", "doc-wechatsync-readme", "src-wechatsync-readme",
     "GPL-3.0",
     "README / License", "supports"),
    ("e-ws-cli", "doc-wechatsync-readme", "src-wechatsync-readme",
     "npm install -g @wechatsync/cli",
     "README / CLI 命令行工具", "supports"),
    ("e-ws-cli-license", "doc-wechatsync-cli", "src-wechatsync-cli",
     '"license":"MIT"',
     "npm registry / @wechatsync/cli 包元数据", "supports"),
    ("e-ws-site-draft", "doc-wechatsync-site", "src-wechatsync-site",
     "文章同步后保存在各平台的「草稿箱」中",
     "官网 FAQ / 同步后的文章在哪里", "supports"),
    ("e-ws-site-noav", "doc-wechatsync-site", "src-wechatsync-site",
     "目前仅支持文字和图片的同步，音频和视频暂不支持",
     "官网 FAQ / 支持同步音频、视频吗", "supports"),
    ("e-ws-site-style", "doc-wechatsync-site", "src-wechatsync-site",
     "部分样式在其他平台可能不被支持",
     "官网 FAQ / 同步后排版乱了怎么办", "supports"),

    # ============ multi-publisher ============
    ("e-mp-adapters", "doc-multi-publisher", "src-multi-publisher",
     "9 个适配器，2 个已实测",
     "README / 功能特性 · 多平台支持", "supports"),
    ("e-mp-pending", "doc-multi-publisher", "src-multi-publisher",
     "适配器就绪，待实测",
     "README / 平台可用性 说明", "supports"),
    ("e-mp-48001", "doc-multi-publisher", "src-multi-publisher",
     "❌ **48001**",
     "README / 平台接口权限的现实 · 个人未认证订阅号", "supports"),
    ("e-mp-draft-default", "doc-multi-publisher", "src-multi-publisher",
     "所有平台默认发布到草稿箱，需手动在各平台确认发布。",
     "README / FAQ · 可以只发布到草稿箱吗", "supports"),
    ("e-mp-playwright", "doc-multi-publisher", "src-multi-publisher",
     "Playwright 驱动扫码/账号登录，Cookie 自动获取保存",
     "README / 功能特性 · 浏览器自动登录", "supports"),
    ("e-mp-personal-no-publish", "doc-multi-publisher", "src-multi-publisher",
     "个人未认证订阅号**在接口层就没有",
     "README / 平台接口权限的现实", "supports"),
    ("e-mp-manual-final", "doc-multi-publisher", "src-multi-publisher",
     "最后一步必须人点「发表」并按弹出的「微信验证」用管理员微信扫码",
     "README / 平台接口权限的现实 · 结论", "supports"),
    ("e-mp-verify-rule", "doc-multi-publisher", "src-multi-publisher",
     "公众号以 `draft/get` 回查为准",
     "README / 判定原则", "supports"),

    # ============ ArtiPub ============
    ("e-ap-puppeteer", "doc-artipub-readme", "src-artipub-readme",
     "**Before**: Used Puppeteer to automate browser interactions",
     "README / Migration from Browser Automation", "supports"),
    ("e-ap-platforms", "doc-artipub-readme", "src-artipub-readme",
     "**Supported Platforms**: 知乎 (Zhihu), 掘金 (Juejin), CSDN, 简书 (Jianshu)",
     "README / Intelligent Multi-Platform Publishing", "supports"),
    ("e-ap-ai", "doc-artipub-readme", "src-artipub-readme",
     "**After**: Uses AI to understand platform requirements and optimize content accordingly",
     "README / Migration from Browser Automation", "supports"),

    # ============ 掘金 MCP（单平台对照） ============
    ("e-jj-cookie", "doc-juejin-mcp", "src-juejin-mcp",
     "**🔒 安全可靠**：Cookie 本地存储，不上传任何数据到第三方",
     "README / 功能特性", "supports"),
    ("e-jj-publish", "doc-juejin-mcp", "src-juejin-mcp",
     "**🚀 一键发布**：`publish_article` 自动完成创建草稿 + 发布两步操作",
     "README / 功能特性", "supports"),
    ("e-jj-cookie-req", "doc-juejin-mcp", "src-juejin-mcp",
     "| **Cookie** | - | 掘金登录凭证 |",
     "README / 环境要求", "supports"),

    # ============ 商业 SaaS 自述 ============
    ("e-yx-count-mixed", "doc-yixiaoer", "src-yixiaoer",
     "有的把视频、图文、文章分别计数",
     "蚁小二学院 / 三、三家主流工具，放进同一张表", "supports"),
    ("e-yx-risk", "doc-yixiaoer", "src-yixiaoer",
     "平台对高度同质的内容批量分发是有风控的",
     "蚁小二学院 / 六、三个容易踩的误区", "supports"),
    ("e-yx-one-draft", "doc-yixiaoer", "src-yixiaoer",
     "第二个误区是一键分发等于一稿全投。",
     "蚁小二学院 / 六、三个容易踩的误区", "context"),
    ("e-yx-auth", "doc-yixiaoer", "src-yixiaoer",
     "正规工具一般通过官方授权或扫码登录完成绑定",
     "蚁小二学院 / FAQ Q3", "supports"),
    ("e-yx-free-limit", "doc-yixiaoer", "src-yixiaoer",
     "免费版对账号数量和每日发布额度都有限制",
     "蚁小二学院 / 六、三个容易踩的误区", "supports"),
    ("e-ym-70", "doc-yimei", "src-yimei",
     "70+自媒体统一矩阵管理",
     "易媒助手官网 / 首屏标语", "supports"),
    ("e-ym-20articles", "doc-yimei", "src-yimei",
     "将文章，一键发布至20+平台",
     "易媒助手官网 / 文章发布 板块", "supports"),
    ("e-ym-11notes", "doc-yimei", "src-yimei",
     "将图文笔记一键发布至11大主流自媒体平台",
     "易媒助手官网 / 图文笔记 板块", "supports"),
]


def window(text: str, anchor: str, before: int = 200, after: int = 320) -> str:
    i = text.find(anchor)
    if i < 0:
        raise LookupError(anchor)
    lo, hi = max(0, i - before), min(len(text), i + len(anchor) + after)
    seg = text[lo:i]
    m = None
    # 中文句末标点后没有空格，故把 。！？ 单独列出；
    # 英文句点仍要求后跟空白，否则会把 1.5K / v2.0.9 切断。
    for m in re.finditer(r"(?:[。！？]\s*|[.!?]\s+|\n\n|\n(?=[0-9A-Z（一-龥]))", seg):
        pass
    if m:
        lo += m.end()
    seg2 = text[i + len(anchor):hi]
    m2 = re.search(r"(?:[。！？]|[.!?](?:\s|$)|\n\n)", seg2)
    if m2:
        hi = i + len(anchor) + m2.end()
    return expand(text, lo, hi)


def expand(text: str, lo: int, hi: int) -> str:
    """不足 MIN_QUOTE 时按行向外扩张，保证引文自带上下文。"""
    q = " ".join(text[lo:hi].split())
    for _ in range(60):
        if len(q) >= MIN_QUOTE:
            break
        nxt = text.find("\n", hi + 1) if hi < len(text) else -1
        if nxt > 0:
            hi = nxt
        else:
            prev = text.rfind("\n", 0, max(0, lo - 1)) if lo > 0 else -1
            if prev > 0:
                lo = prev + 1
            elif hi >= len(text) and lo <= 0:
                break
        q = " ".join(text[lo:hi].split())
    return q


def main() -> int:
    meta: dict[str, dict[str, str]] = {}
    with (ROOT / "documents.csv").open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            meta[row["document_id"]] = row

    rows: list[dict[str, str]] = []
    missing: list[tuple[str, str]] = []
    for eid, did, sid, anchor, locator, stance in SPEC:
        doc = meta.get(did)
        if not doc:
            raise SystemExit(f"缺文档：{did}（{eid}）")
        text = (ROOT / doc["snapshot"]).read_text(encoding="utf-8")
        try:
            quote = window(text, anchor)
        except LookupError:
            missing.append((eid, anchor))
            continue
        rows.append({
            "evidence_id": eid,
            "document_id": did,
            "source_id": sid,
            "quote": quote,
            "locator": locator,
            "stance": stance,
            "extracted_by": "build_evidence.py/1（锚点扩窗，非手写）",
        })

    if missing:
        print("以下锚点在快照里找不到——不是「失败」，是这些句子不在原文里：")
        for eid, anchor in missing:
            print(f"  - {eid}: {anchor!r}")
        print("请改锚点或删条目，不要手写引文。")
        return 1

    out = ROOT / "evidence.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["evidence_id", "document_id", "source_id", "quote",
                        "locator", "stance", "extracted_by"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)
    total = sum(len(r["quote"]) for r in rows)
    print(f"已写 {out.name}：{len(rows)} 条证据，引文合计 {total:,} 字符")
    short = [r["evidence_id"] for r in rows if len(r["quote"]) < MIN_QUOTE]
    if short:
        print(f"[WARN] 以下引文短于 {MIN_QUOTE} 字，对论证贡献有限：{short}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
