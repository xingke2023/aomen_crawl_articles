#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
港保保网站爬虫 - 无限循环版本
持续抓取，直到没有新文章或用户中断
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

def get_all_article_links(url):
    """获取页面所有文章链接"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 扫描页面: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(ignore_https_errors=True)
            page.goto(url, timeout=30000, wait_until='networkidle')
            time.sleep(2)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        links = []

        # 只抓取文章详情页
        for a in soup.find_all('a', href=re.compile(r'/h-nd-\d+\.html')):
            link = a.get('href')
            if link.startswith('/'):
                link = BASE_URL + link
            elif not link.startswith('http'):
                continue

            title = a.get_text().strip()
            if len(title) < 5:
                parent = a.find_parent(['h1', 'h2', 'h3', 'div', 'li'])
                if parent:
                    title = parent.get_text().strip()

            if len(title) >= 5:
                links.append({'title': title[:200], 'link': link})

        # 去重
        seen = set()
        unique_links = []
        for item in links:
            if item['link'] not in seen:
                seen.add(item['link'])
                unique_links.append(item)

        print(f"  → 找到 {len(unique_links)} 篇文章")
        return unique_links

    except Exception as e:
        print(f"  ✗ 扫描失败: {e}")
        return []

def get_article_content(url):
    """获取文章内容"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(ignore_https_errors=True)
            page.goto(url, timeout=30000, wait_until='networkidle')
            time.sleep(2)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # 查找内容
        content_div = None
        for selector in ['article', '.article-content', '.content', 'main']:
            content_div = soup.select_one(selector)
            if content_div and len(content_div.get_text(strip=True)) > 100:
                break

        # 找最大文本块
        if not content_div:
            all_divs = soup.find_all(['div', 'article'])
            max_len = 0
            for div in all_divs:
                text = div.get_text(strip=True)
                if len(text) > max_len:
                    max_len = len(text)
                    content_div = div

        if not content_div:
            return None

        # 清理
        for tag in content_div.select('script, style, nav, aside, footer, header, .menu'):
            tag.decompose()

        content = content_div.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        content = '\n\n'.join(lines)

        if len(content) < 100:
            return None

        return {'content': content, 'publish_time': None}

    except Exception as e:
        print(f"  ✗ 抓取失败: {e}")
        return None

def save_article(conn, title, link, content):
    """保存文章"""
    try:
        with conn.cursor() as cur:
            # 检查是否存在
            cur.execute("SELECT id FROM articles WHERE link = %s", (link,))
            if cur.fetchone():
                return 'exists'

            # 插入
            cur.execute(
                """INSERT INTO articles (title, link, source, tags, content, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (title, link, SOURCE, TAGS, content, datetime.now())
            )
            conn.commit()
            return 'success'
    except Exception as e:
        print(f"  ✗ 保存失败: {e}")
        conn.rollback()
        return 'error'

def main():
    """主函数 - 无限循环"""
    print("=" * 80)
    print("港保保爬虫 - 无限循环模式")
    print("=" * 80)
    print(f"来源: {SOURCE}")
    print(f"标签: {TAGS}")
    print("按 Ctrl+C 停止")
    print("=" * 80)

    conn = get_connection()
    round_num = 1
    total_saved = 0

    try:
        while True:
            print(f"\n{'#' * 80}")
            print(f"第 {round_num} 轮扫描开始")
            print(f"{'#' * 80}")

            # 获取所有文章链接
            articles = get_all_article_links(BASE_URL)

            if not articles:
                print("✗ 没有找到文章，等待5分钟后重试...")
                time.sleep(300)
                continue

            new_in_round = 0

            for idx, article in enumerate(articles, 1):
                print(f"\n[{idx}/{len(articles)}] {article['title'][:50]}")

                # 检查是否已存在
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM articles WHERE link = %s", (article['link'],))
                    if cur.fetchone():
                        print("  ⊙ 已存在")
                        continue

                # 抓取内容
                time.sleep(random.uniform(1, 3))
                result = get_article_content(article['link'])

                if not result:
                    print("  ✗ 无内容")
                    continue

                # 保存
                status = save_article(conn, article['title'], article['link'], result['content'])

                if status == 'success':
                    print(f"  ✓ 保存成功 ({len(result['content'])} 字)")
                    total_saved += 1
                    new_in_round += 1
                elif status == 'exists':
                    print("  ⊙ 已存在")

            print(f"\n{'=' * 80}")
            print(f"第 {round_num} 轮完成")
            print(f"本轮新增: {new_in_round} 篇")
            print(f"累计保存: {total_saved} 篇")
            print(f"{'=' * 80}")

            if new_in_round == 0:
                print("\n本轮没有新文章，等待 10 分钟后重试...")
                time.sleep(600)
            else:
                print("\n等待 3 分钟后开始下一轮...")
                time.sleep(180)

            round_num += 1

    except KeyboardInterrupt:
        print("\n\n用户中断")
    finally:
        conn.close()
        print(f"\n总共保存: {total_saved} 篇文章")

if __name__ == '__main__':
    main()
