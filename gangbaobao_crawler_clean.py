#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
港保保网站爬虫 - 清洁版（只抓取文章正文）
目标网站: http://gangbaobaohk.com/
标签: 香港保险
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time
import random
import sys
from urllib.parse import urljoin, urlparse
import warnings

warnings.filterwarnings('ignore')

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
PAGE_DELAY_RANGE = (2, 4)
ARTICLE_DELAY_RANGE = (1, 3)

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def get_page_content(url):
    """使用 Playwright 获取页面内容"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                ignore_https_errors=True
            )
            page = context.new_page()
            page.goto(url, timeout=30000, wait_until='networkidle')
            time.sleep(2)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"  ✗ 获取页面失败: {e}")
        return None

def parse_article_list(html, base_url):
    """解析文章列表"""
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    found_links = set()

    for link in soup.find_all('a', href=True):
        href = link.get('href', '')

        # 只保留文章详情页
        if not re.search(r'/h-nd-\d+\.html', href):
            continue

        full_url = urljoin(base_url, href)

        if urlparse(full_url).netloc != urlparse(base_url).netloc:
            continue

        title = link.get_text().strip()
        if len(title) < 5:
            parent = link.find_parent(['h1', 'h2', 'h3', 'h4', 'div', 'li'])
            if parent:
                title = parent.get_text().strip()

        skip_words = ['首页', '关于', '联系', '更多', 'nav']
        if any(word in title.lower() for word in skip_words):
            continue

        if len(title) >= 5 and full_url not in found_links:
            articles.append({'title': title[:200], 'link': full_url})
            found_links.add(full_url)

    return articles

def parse_article_content(url):
    """抓取文章详细内容 - 只抓取正文"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在抓取文章: {url}")

    html = get_page_content(url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # 方法1: 查找 .richContent（文章正文容器）
    content_div = soup.select_one('.richContent')

    # 方法2: 如果没找到，尝试查找包含大量p标签的div
    if not content_div:
        all_divs = soup.find_all('div')
        max_p_count = 0
        for div in all_divs:
            p_count = len(div.find_all('p'))
            if p_count > max_p_count and p_count > 3:
                max_p_count = p_count
                content_div = div

    if not content_div:
        print("  ✗ 未找到内容容器")
        return None

    # 移除不需要的元素
    for unwanted in content_div.select('script, style, img, .share, .social, nav, aside, footer, header'):
        unwanted.decompose()

    # 提取所有p标签的文本
    paragraphs = content_div.find_all('p')
    content_lines = []

    for p in paragraphs:
        text = p.get_text(strip=True)
        # 过滤掉太短的段落和无意义文本
        if len(text) > 10 and not any(skip in text for skip in ['Nav', 'Home', '首页', '扫一扫', '备案号', '©']):
            content_lines.append(text)

    # 如果p标签内容太少，尝试直接获取文本
    if len(content_lines) < 3:
        content = content_div.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        # 过滤
        content_lines = [
            line for line in lines
            if len(line) > 10 and not any(skip in line for skip in ['Nav', 'Home', '首页', '扫一扫', '备案号', '©', '港保保', '关注', '咨询'])
        ]

    if not content_lines:
        print("  ✗ 未提取到有效内容")
        return None

    content = '\n\n'.join(content_lines)

    # 提取作者信息（如果有）
    author_elem = soup.select_one('.newsInfo_author')
    author = author_elem.get_text(strip=True) if author_elem else None

    # 如果有作者，添加到内容开头
    if author:
        content = f"{author}\n\n{content}"

    # 提取发布时间
    publish_time = None
    time_selectors = ['time', '.newsTime', '.publish-date', '.date']
    for selector in time_selectors:
        time_elem = soup.select_one(selector)
        if time_elem:
            time_str = time_elem.get('datetime') or time_elem.get_text().strip()
            time_patterns = [
                r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2}(:\d{2})?)',
                r'(\d{4}[-/]\d{2}[-/]\d{2})',
            ]
            for pattern in time_patterns:
                match = re.search(pattern, time_str)
                if match:
                    try:
                        time_text = match.group(1).replace('年', '-').replace('月', '-').replace('日', '')
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                publish_time = datetime.strptime(time_text.strip(), fmt)
                                break
                            except:
                                continue
                        if publish_time:
                            break
                    except:
                        continue
            if publish_time:
                break

    if len(content) < 100:
        print(f"  ✗ 内容太短 ({len(content)} 字)")
        return None

    return {'content': content, 'publish_time': publish_time}

def save_article(conn, article_data):
    """保存文章到数据库"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, content FROM articles WHERE link = %s",
                (article_data['link'],)
            )
            existing = cursor.fetchone()

            if existing:
                if existing['content']:
                    return 'duplicate'
                else:
                    cursor.execute(
                        """UPDATE articles
                           SET content = %s, publish_time = %s, source = %s, tags = %s
                           WHERE id = %s""",
                        (article_data['content'], article_data['publish_time'],
                         SOURCE, TAGS, existing['id'])
                    )
                    conn.commit()
                    return 'updated'

            cursor.execute(
                """INSERT INTO articles
                   (title, link, source, tags, content, publish_time, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (article_data['title'], article_data['link'], SOURCE, TAGS,
                 article_data['content'], article_data['publish_time'], datetime.now())
            )
            conn.commit()
            return 'success'

    except Exception as e:
        print(f"  ✗ 保存失败: {e}")
        conn.rollback()
        return 'error'

def crawl_site(start_url, max_articles=100):
    """爬取网站"""
    print("=" * 80)
    print(f"港保保网站爬虫启动 - 清洁版（只抓取正文）")
    print(f"目标网站: {start_url}")
    print(f"来源标识: {SOURCE}")
    print(f"标签: {TAGS}")
    print(f"最大文章数: {max_articles}")
    print("=" * 80)

    conn = get_connection()
    total_found = 0
    total_saved = 0
    total_duplicate = 0
    processed_urls = set()

    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在获取首页...")
        html = get_page_content(start_url)

        if not html:
            print("✗ 无法获取首页内容")
            return

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在解析文章列表...")
        articles = parse_article_list(html, start_url)

        print(f"\n找到 {len(articles)} 篇文章")

        for idx, article in enumerate(articles, 1):
            if total_saved >= max_articles:
                print(f"\n已达到最大文章数限制 ({max_articles})，停止抓取")
                break

            if article['link'] in processed_urls:
                continue

            processed_urls.add(article['link'])

            print(f"\n{'=' * 60}")
            print(f"文章 {idx}/{len(articles)}")
            print(f"标题: {article['title']}")
            print(f"链接: {article['link']}")
            print(f"{'=' * 60}")

            time.sleep(random.uniform(*ARTICLE_DELAY_RANGE))

            result = parse_article_content(article['link'])

            if result and result['content']:
                article_data = {
                    'title': article['title'],
                    'link': article['link'],
                    'content': result['content'],
                    'publish_time': result['publish_time']
                }

                save_result = save_article(conn, article_data)

                if save_result == 'success':
                    print(f"  ✓ 保存新文章成功 (字数: {len(article_data['content'])})")
                    total_saved += 1
                    total_found += 1
                elif save_result == 'updated':
                    print(f"  ✓ 更新已存在记录")
                    total_saved += 1
                elif save_result == 'duplicate':
                    print(f"  ⊙ 文章已存在")
                    total_duplicate += 1
            else:
                print(f"  ✗ 未能提取文章内容")

    except KeyboardInterrupt:
        print("\n\n[中断] 用户停止程序")
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print(f"\n{'=' * 80}")
        print(f"爬虫结束")
        print(f"{'=' * 80}")
        print(f"发现文章: {total_found} 篇")
        print(f"成功保存: {total_saved} 篇")
        print(f"重复跳过: {total_duplicate} 篇")
        print(f"{'=' * 80}")

if __name__ == '__main__':
    start_url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    max_articles = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    crawl_site(start_url, max_articles)
