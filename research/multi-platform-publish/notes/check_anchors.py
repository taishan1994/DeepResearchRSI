import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "documents"

CHECKS = {
    "doc-wx-draft-add.txt": [
        "本接口用于新增常用的素材到草稿箱。",
        "1.上传到草稿箱中的素材被群发或发布后，该素材将从草稿箱中移除。",
        "POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token",
        "图文消息的具体内容，支持HTML标签，必须少于2万字符",
        "标题，总长度不超过32个字",
        "本接口不支持云调用。",
    ],
    "doc-wx-freepublish.txt": [
        "本接口用于将图文草稿提交发布。",
        "此时只意味着发布任务提交成功，并不意味着此时发布已经完成",
        "仅认证：表示仅允许企业主体已认证账号调用，未认证或不支持认证的账号无法调用。",
        "48001",
        "由于发布任务提交后，发布任务可能在一定时间后才完成",
    ],
    "doc-xhs-open-nav.txt": [
        '"navigationName":"公共API"',
        '"navigationName":"素材中心API"',
        '"navigationName":"财务API"',
    ],
    "doc-zhihu-api-ref.txt": [
        "仅支持本人**已发布**的内容；草稿、未发布或其他不可用状态的内容不在支持范围内。",
        "仅支持当前 Access Secret 所属账号的本人数据",
        "## 11. 创作能力",
        "### 11.1 API：`user_content_detail`（我的创作全文）",
        "30003 请求被风控拒绝",
    ],
    "doc-wechatsync-readme.txt": [
        "**文章同步助手不是爬虫，不模拟登录，不经过任何第三方服务器。**",
        "扩展直接使用浏览器中已有的 Cookie，无需额外授权，无需输入密码",
        "发布文章时，扩展调用的是各平台 Web 编辑器使用的同一套官方 API",
        "**草稿优先**：默认将文章同步为草稿，发布前由你人工确认，不会自动发布",
        "| 知乎 | zhihu | 主流自媒体 | ✅ |",
        "| 小红书 | xiaohongshu | 主流自媒体 | ✅ |",
        "一键同步微信公众号文章到知乎、头条、掘金、小红书、CSDN 等 29+ 平台",
        "GPL-3.0",
        "npm install -g @wechatsync/cli",
    ],
    "doc-multi-publisher.txt": [
        "9 个适配器，2 个已实测",
        "适配器就绪，待实测",
        "❌ **48001**",
        "> 是的，所有平台默认发布到草稿箱，需手动在各平台确认发布。",
        "Playwright 驱动扫码/账号登录，Cookie 自动获取保存",
        "个人未认证订阅号**在接口层就没有",
        "`mpub publish-wechat --backend`",
        "公众号以 `draft/get` 回查为准",
    ],
    "doc-artipub-readme.txt": [
        "**Before**: Used Puppeteer to automate browser interactions",
        "**Supported Platforms**: 知乎 (Zhihu), 掘金 (Juejin), CSDN, 简书 (Jianshu), SegmentFault, 开源中国 (OSCHINA)",
        "**After**: Uses AI to understand platform requirements and optimize content accordingly",
    ],
    "doc-juejin-mcp.txt": [
        "**🔒 安全可靠**：Cookie 本地存储，不上传任何数据到第三方",
        "**🚀 一键发布**：`publish_article` 自动完成创建草稿 + 发布两步操作",
        "| **Cookie** | - | 掘金登录凭证 |",
    ],
    "doc-yixiaoer.txt": [
        "有的把视频、图文、文章分别计数",
        "第一个误区是账号越多越好。平台对高度同质的内容批量分发是有风控的",
        "第二个误区是一键分发等于一稿全投。",
        "正规工具一般通过官方授权或扫码登录完成绑定",
        "免费版对账号数量和每日发布额度都有限制",
    ],
    "doc-yimei.txt": [
        "将文章，一键发布至20+平台",
        "70+自媒体统一矩阵管理",
        "图文笔记（动态）一键发布 / 定时发布 / 批量发布",
        "采用授权模式，支持多账号授权、智能回复、聚合评论等功能",
    ],
    "doc-wechatsync-site.txt": [
        "文章同步后保存在各平台的「草稿箱」中",
        "目前仅支持文字和图片的同步，音频和视频暂不支持",
        "微信公众号排版较为灵活，部分样式在其他平台可能不被支持",
        "完全免费且开源",
    ],
    "doc-wechatsync-cli.txt": [
        '"description":"WechatSync CLI - 命令行同步文章到多个平台"',
        '"license":"MIT"',
    ],
}

bad = 0
for fname, anchors in CHECKS.items():
    path = DOCS / fname
    if not path.is_file():
        print(f"[MISS] {fname}")
        bad += 1
        continue
    text = path.read_text(encoding="utf-8")
    for a in anchors:
        if a not in text:
            print(f"[NO]   {fname}: {a!r}")
            bad += 1
print("missing anchors:", bad)
