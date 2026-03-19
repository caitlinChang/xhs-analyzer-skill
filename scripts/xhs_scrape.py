"""
小红书博主全量笔记爬虫
用法：
  python3 xhs_scrape.py --user-id <ID> --cookies-file ~/.claude/xhs_config.json
  python3 xhs_scrape.py --name <昵称> --cookies-file ~/.claude/xhs_config.json
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

# ── 依赖检查 ──────────────────────────────────────────────
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[错误] 未安装 playwright，请运行：python3 -m playwright install chromium")
    sys.exit(1)

OUTPUT_DIR = Path("/tmp/xhs_raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ── Cookie 工具 ───────────────────────────────────────────

def load_cookies(cookies_file: str) -> str:
    path = Path(cookies_file).expanduser()
    if not path.exists():
        return ""
    with open(path) as f:
        config = json.load(f)
    return config.get("cookies", "")


def parse_cookies(cookie_str: str) -> list:
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies.append({
                "name": k.strip(),
                "value": v.strip(),
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
    return cookies


def is_login_valid(html: str) -> bool:
    return "window.__INITIAL_STATE__" in html and "login" not in html[:200].lower()


# ── HTML 解析工具 ─────────────────────────────────────────

def extract_initial_state(html: str) -> dict:
    marker = "window.__INITIAL_STATE__="
    idx = html.find(marker)
    if idx == -1:
        return {}
    start = idx + len(marker)
    depth, end = 0, start
    for i, ch in enumerate(html[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    raw = html[start:end].replace(":undefined", ":null")
    try:
        return json.loads(raw)
    except Exception:
        return {}


def parse_note_id_time(note_id: str) -> str:
    """从笔记 ID 高位 4 字节解析发布时间"""
    try:
        ts = int(note_id[:8], 16)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "未知"


# ── 搜索博主 ──────────────────────────────────────────────

async def search_user_by_name(page, name: str) -> str | None:
    print(f"[搜索] 正在搜索博主：{name}")
    search_url = f"https://www.xiaohongshu.com/search_result?keyword={name}&type=user"
    await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(2)

    html = await page.content()
    state = extract_initial_state(html)

    users = []
    for v in state.get("search", {}).values():
        if isinstance(v, dict) and "users" in v:
            users = v["users"]
            break

    if not users:
        links = await page.query_selector_all("a[href*='/user/profile/']")
        for link in links:
            href = await link.get_attribute("href")
            if href:
                m = re.search(r"/user/profile/([a-f0-9]+)", href)
                if m:
                    return m.group(1)
        return None

    for u in users:
        if u.get("nickname") == name or u.get("nick_name") == name:
            return u.get("user_id") or u.get("id")

    first = users[0]
    print(f"  [提示] 未精确匹配，使用第一个结果：{first.get('nickname') or first.get('nick_name', '')}")
    return first.get("user_id") or first.get("id")


# ── 主页基础信息 ──────────────────────────────────────────

async def fetch_profile(page, user_id: str):
    url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
    print(f"[主页] 加载：{url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)

    html = await page.content()
    if not is_login_valid(html):
        print("[错误] Cookie 已失效，请重新提供")
        sys.exit(2)

    state = extract_initial_state(html)
    user_data = state.get("user", {}).get("userPageData", {})
    basic = user_data.get("basicInfo", {})
    interactions = user_data.get("interactions", [])

    profile = {
        "user_id": user_id,
        "nickname": basic.get("nickname", ""),
        "red_id": basic.get("redId", ""),
        "desc": basic.get("desc", ""),
        "gender": "女" if basic.get("gender") == 1 else "男",
        "ip_location": basic.get("ipLocation", ""),
        "fans": next((i["count"] for i in interactions if i["type"] == "fans"), "0"),
        "follows": next((i["count"] for i in interactions if i["type"] == "follows"), "0"),
        "interaction_total": next((i["count"] for i in interactions if i["type"] == "interaction"), "0"),
        "crawl_time": datetime.now().isoformat(),
    }
    print(f"  昵称：{profile['nickname']}  粉丝：{profile['fans']}  获赞收藏：{profile['interaction_total']}")
    return profile, html


# ── 全量笔记收集 ──────────────────────────────────────────

async def collect_all_notes(page, html: str) -> list:
    all_notes = {}

    async def handle_response(response):
        if "user_posted" in response.url:
            try:
                data = await response.json()
                for n in data.get("data", {}).get("notes", []):
                    nid = n.get("note_id") or n.get("id")
                    if nid:
                        all_notes[nid] = {
                            "id": nid,
                            "title": n.get("display_title", ""),
                            "type": n.get("type", ""),
                            "likes": int(str(n.get("interact_info", {}).get("liked_count", "0")).replace(",", "")),
                            "xsec_token": n.get("xsec_token", ""),
                            "published_at": parse_note_id_time(nid),
                        }
                print(f"  [API] 累计 {len(all_notes)} 篇，has_more={data.get('data', {}).get('has_more', False)}")
            except Exception:
                pass

    page.on("response", handle_response)
    print("[笔记列表] 开始滚动加载...")

    # 补充首屏数据
    state = extract_initial_state(html)
    for page_list in state.get("user", {}).get("notes", []):
        if isinstance(page_list, list):
            for item in page_list:
                card = item.get("noteCard", {})
                nid = item.get("id")
                if nid and nid not in all_notes:
                    all_notes[nid] = {
                        "id": nid,
                        "title": card.get("displayTitle", ""),
                        "type": card.get("type", ""),
                        "likes": int(str(card.get("interactInfo", {}).get("likedCount", "0")).replace(",", "")),
                        "xsec_token": item.get("xsecToken", ""),
                        "published_at": parse_note_id_time(nid),
                    }

    # 持续滚动
    prev_count, no_new_rounds = 0, 0
    while no_new_rounds < 4:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(random.uniform(2.0, 3.0))
        if len(all_notes) == prev_count:
            no_new_rounds += 1
        else:
            no_new_rounds = 0
            prev_count = len(all_notes)

    print(f"  [完成] 共收集到 {len(all_notes)} 篇笔记")
    return list(all_notes.values())


# ── 逐篇获取正文 ──────────────────────────────────────────

async def fetch_note_contents(context, notes: list) -> list:
    note_page = await context.new_page()
    total = len(notes)

    for i, note in enumerate(notes):
        nid = note["id"]
        token = note.get("xsec_token", "")
        url = f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={token}&xsec_source=pc_user"
        try:
            await note_page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(0.5)
            desc = await note_page.evaluate(
                "() => document.querySelector('meta[name=\"description\"]')?.content || ''"
            )
            og_desc = await note_page.evaluate(
                "() => document.querySelector('meta[property=\"og:description\"]')?.content || ''"
            )
            content = desc or og_desc or ""
            if not content or content.startswith("小红书"):
                content = "(纯视频，无文字描述)"
            note["content"] = content
            status = "✓"
        except Exception:
            note["content"] = "(获取失败)"
            status = "✗"

        print(f"  [{i+1:03d}/{total}] {status} [{note['type']}] {note['title'][:35]}")
        await asyncio.sleep(random.uniform(1.5, 2.5))

    await note_page.close()
    return notes


# ── 主流程 ────────────────────────────────────────────────

async def run(user_id: str | None, name: str | None, cookies_str: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 900},
        )
        await context.add_cookies(parse_cookies(cookies_str))
        page = await context.new_page()

        if not user_id and name:
            user_id = await search_user_by_name(page, name)
            if not user_id:
                print(f"[错误] 未找到博主「{name}」，请确认昵称或直接提供主页链接")
                await browser.close()
                sys.exit(1)

        profile, html = await fetch_profile(page, user_id)
        notes = await collect_all_notes(page, html)

        print(f"\n[正文] 开始逐篇抓取（共 {len(notes)} 篇，预计 {max(1, len(notes)*2//60)} 分钟）...")
        notes = await fetch_note_contents(context, notes)
        await browser.close()

    profile_path = OUTPUT_DIR / "profile.json"
    notes_path = OUTPUT_DIR / "notes.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    with open(notes_path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    success = sum(1 for n in notes if n.get("content") not in ("(获取失败)", ""))
    print(f"\n[完成] 笔记总数：{len(notes)} 篇，正文获取成功：{success} 篇")
    print(f"  → {profile_path}")
    print(f"  → {notes_path}")


def main():
    parser = argparse.ArgumentParser(description="小红书博主全量笔记爬虫")
    parser.add_argument("--user-id", help="博主 user_id（从主页 URL 提取）")
    parser.add_argument("--name", help="博主昵称（将自动搜索）")
    parser.add_argument("--cookies-file", default="~/.claude/xhs_config.json")
    args = parser.parse_args()

    if not args.user_id and not args.name:
        print("[错误] 请提供 --user-id 或 --name")
        sys.exit(1)

    cookies_str = load_cookies(args.cookies_file)
    if not cookies_str:
        print("[错误] Cookie 配置为空，请先在 ~/.claude/xhs_config.json 中填入 cookies 字段")
        sys.exit(2)

    asyncio.run(run(args.user_id, args.name, cookies_str))


if __name__ == "__main__":
    main()
