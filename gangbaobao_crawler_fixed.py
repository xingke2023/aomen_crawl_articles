#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
港保保网站爬虫 - 修复版（正确提取文章正文）
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time
import random
import sys

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

BASE_URL = 'http://gangbaobaohk.com'
SOURCE = '港保保'
TAGS = '香港保险'

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def get_page_content(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(ignore_https_errors=True)
            page.goto(url, timeout=30000, wait_until='networkidle')
            time.sleep(2)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"  ✗ 获取页面失败: {e}")
        return None

def parse_article_list(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    found_links = set()

    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if not re.search(r'/h-nd-\d+\.html', href):
            continue

        if href.startswith('/'):
            full_url = BASE_URL + href
        elif href.startswith('http'):
            full_url = href
        else:
            continue

        title = link.get_text().strip()
        if len(title) < 5:
            parent = link.find_parent(['h2', 'h3', 'div'])
            if parent:
                title = parent.get_text().strip()

        if len(title) >= 5 and full_url not in found_links:
            articles.append({'title': title[:200], 'link': full_url})
            found_links.add(full_url)

    return articles

def parse_article_content(url):
    """抓取文章正文 - 找到最长的richContent"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在抓取: {url}")

    html = get_page_content(url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # 查找所有 richContent 元素
    all_rich = soup.find_all(class_=lambda x: x and ('richContent' in ' '.join(x) if isinstance(x, list) else ('richContent' in str(x))))

    # 找到文本最长的那个
    max_len = 0
    content_div = None

    for elem in all_rich:
        text = elem.get_text(strip=True)
        # 过滤掉页脚、导航等
        if any(skip in text for skip in ['首页', 'Nav', '港保保网站地图', '扫一扫', '备案号']):
            continue

        if len(text) > max_len and len(text) > 200:
            max_len = len(text)
            content_div = elem

    if not content_div:
        print("  ✗ 未找到文章内容")
        return None

    # 移除图片、脚本等
    for unwanted in content_div.select('script, style, img'):
        unwanted.decompose()

    # 获取纯文本
    content = content_div.get_text(separator='\n', strip=True)

    # 清理空行
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    content = '\n\n'.join(lines)

    # 提取作者
    author_elem = soup.select_one('.newsInfo_author')
    if author_elem:
        author = author_elem.get_text(strip=True)
        content = f"{author}\n\n{content}"

    if len(content) < 100:
        print(f"  ✗ 内容太短 ({len(content)} 字)")
        return None

    print(f"  ✓ 提取成功 ({len(content)} 字)")
    return {'content': content, 'publish_time': None}

def save_article(conn, article_data):
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM articles WHERE link = %s",
                (article_data['link'],)
            )
            if cursor.fetchone():
                return 'duplicate'

            cursor.execute(
                """INSERT INTO articles
                   (title, link, source, tags, content, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (article_data['title'], article_data['link'], SOURCE, TAGS,
                 article_data['content'], datetime.now())
            )
            conn.commit()
            return 'success'
    except Exception as e:
        print(f"  ✗ 保存失败: {e}")
        conn.rollback()
        return 'error'

def main(start_url, max_articles):
    print("=" * 80)
    print("港保保爬虫 - 修复版")
    print(f"来源: {SOURCE} | 标签: {TAGS}")
    print("=" * 80)

    conn = get_connection()
    total_saved = 0

    try:
        html = get_page_content(start_url)
        if not html:
            return

        articles = parse_article_list(html, start_url)
        print(f"\n找到 {len(articles)} 篇文章\n")

        for idx, article in enumerate(articles, 1):
            if total_saved >= max_articles:
                break

            print(f"[{idx}/{len(articles)}] {article['title'][:50]}")

            time.sleep(random.uniform(1, 3))

            result = parse_article_content(article['link'])
            if result:
                article_data = {
                    'title': article['title'],
                    'link': article['link'],
                    'content': result['content']
                }

                status = save_article(conn, article_data)
                if status == 'success':
                    total_saved += 1
                    print("  ✓ 保存成功")
                elif status == 'duplicate':
                    print("  ⊙ 已存在")

    finally:
        conn.close()
        print(f"\n总共保存: {total_saved} 篇")

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    max_art = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    main(url, max_art)
