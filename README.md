# xhs-analyzer-skill

一个 [Claude Code](https://claude.ai/claude-code) Skill，用于**爬取小红书博主全量历史笔记并生成深度分析报告**。

## 功能

- 🔍 支持按**昵称**或**主页链接**分析任意公开博主
- 📦 自动爬取历史笔记（默认最新 200 篇，可自定义数量或抓取全部）
- 🤖 由 Claude 完成 7 个维度的深度分析：
  - 基础信息 & 粉丝数据
  - 内容主题聚类
  - 发布时间规律
  - 账号转型轨迹
  - 爆款内容归因
  - 竞品洞察建议
- 📄 输出两份报告：**账号分析报告** + **全量笔记列表**
- ☁️ 支持导出到**飞书文档**或**本地 MD 文件**

## 安装

### 前置条件

- macOS / Linux
- Python 3.9+
- [Claude Code](https://claude.ai/claude-code) 已安装

### 一键安装

```bash
git clone https://github.com/caitlinChang/xhs-analyzer-skill.git
cd xhs-analyzer-skill
chmod +x install.sh
./install.sh
```

安装脚本会自动完成：
- 安装 `playwright` Python 包
- 安装 Playwright Chromium 浏览器
- 复制 Skill 文件到 `~/.claude/commands/`
- 复制爬虫脚本到 `~/.claude/scripts/`
- 创建 Cookie 配置模板

## 使用方法

在 Claude Code 中：

```
/xhs 博主昵称
```

```
/xhs https://www.xiaohongshu.com/user/profile/<user_id>
```

### 控制抓取数量

默认抓取最新 200 篇，也可以在对话中指定：

```
/xhs 某博主 抓100篇
/xhs 某博主 全部
```

### 首次使用：提供 Cookie

小红书需要登录才能查看完整内容。首次运行时 Claude 会引导你获取 Cookie：

1. 用 Chrome 打开 [xiaohongshu.com](https://www.xiaohongshu.com) 并登录
2. 按 `F12` → **Application** → **Cookies** → `www.xiaohongshu.com`
3. 将所有 Cookie 拼成 `key=value; key=value` 格式告诉 Claude

Cookie 会保存在 `~/.claude/xhs_config.json`，下次自动复用，失效时会提示重新填写。

### 输出示例

运行完成后 Claude 会询问输出方式：

```
分析完成！报告输出到哪里？
1. 飞书文档（默认）
2. 本地 MD 文件（当前目录）
```

**输出文件示例：**

| 文件 | 内容 |
|------|------|
| `{博主昵称}_账号分析报告_{日期}.md` | 7 个维度的深度分析 |
| `{博主昵称}_全量笔记_{日期}.md` | 全量笔记按点赞排序 |

## 更新

已安装的用户运行以下命令即可更新（无需重装 Playwright）：

```bash
curl -fsSL https://raw.githubusercontent.com/caitlinChang/xhs-analyzer-skill/main/commands/xhs.md -o ~/.claude/commands/xhs.md
curl -fsSL https://raw.githubusercontent.com/caitlinChang/xhs-analyzer-skill/main/scripts/xhs_scrape.py -o ~/.claude/scripts/xhs_scrape.py
```

## 注意事项

- 请**仅用于分析公开账号**，不要用于任何商业爬取目的
- 请合理控制使用频率，脚本内置了请求间隔（每篇笔记 1.5~2.5 秒）
- Cookie 属于个人隐私凭证，请勿分享给他人
- 笔记数量较多时（如 400+ 篇）爬取可能需要 10~20 分钟

## 文件结构

```
xhs-analyzer-skill/
├── README.md
├── install.sh                  # 一键安装脚本
├── commands/
│   └── xhs.md                  # Skill 主文件（→ ~/.claude/commands/）
└── scripts/
    └── xhs_scrape.py           # Playwright 爬虫脚本（→ ~/.claude/scripts/）
```

## License

MIT
