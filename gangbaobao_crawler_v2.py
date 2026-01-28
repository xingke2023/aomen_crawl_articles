#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
港保保网站爬虫 v2 - 使用 Playwright
目标网站: http://gangbaobaohk.com/
标签: 香港保险
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time
import random
import sys
from urllib.parse import urljoin, urlparse
import warnings

# 忽略警告
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

# 爬虫配置
BASE_URL = 'http://gangbaobaohk.com'
SOURCE = '港保保'
TAGS = '香港保险'
PAGE_DELAY_RANGE = (2, 4)
ARTICLE_DELAY_RANGE = (1, 3)
MAX_RETRIES = 2

def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def get_page_content(url, wait_for_selector=None):
    """使用 Playwright 获取页面内容"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                ignore_https_errors=True
            )
            page = context.new_page()

            # 访问页面
            page.goto(url, timeout=30000, wait_until='networkidle')

            # 如果指定了选择器，等待元素加载
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=5000)
                except:
                    pass

            # 额外等待确保内容加载
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

    # 查找所有链接
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')

        # 跳过无效链接
        if not href or href in ['#', '/', 'javascript:void(0)', 'javascript:;']:
            continue

        # 跳过分类、导航等页面，只保留文章详情页
        # 根据观察，文章详情页格式为 h-nd-数字.html
        if not re.search(r'/h-nd-\d+\.html', href):
            continue

        # 构建完整URL
        full_url = urljoin(base_url, href)

        # 只保留同域名的链接
        if urlparse(full_url).netloc != urlparse(base_url).netloc:
            continue

        # 获取标题
        title = link.get_text().strip()

        # 如果标题太短，尝试从父元素获取
        if len(title) < 5:
            parent = link.find_parent(['h1', 'h2', 'h3', 'h4', 'div', 'li'])
            if parent:
                title = parent.get_text().strip()

        # 过滤导航文字
        skip_words = ['首页', '关于', '联系', '更多', '下一页', '上一页', '返回', 'more', 'next', 'prev', 'nav']
        if any(word in title.lower() for word in skip_words):
            continue

        # 如果标题合适且URL未重复
        if len(title) >= 5 and full_url not in found_links:
            articles.append({
                'title': title[:200],
                'link': full_url
            })
            found_links.add(full_url)

    return articles

def parse_article_content(url):
    """抓取文章详细内容"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在抓取文章: {url}")

    html = get_page_content(url, wait_for_selector='article, .article, .content')
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # 尝试多种选择器查找正文内容
    content_selectors = [
        'article',
        '.article-content',
        '.post-content',
        '.entry-content',
        '.content',
        'div[class*="content"]',
        '.text-content',
        'main .container',
        '#article-content'
    ]

    content_div = None
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div and len(content_div.get_text(strip=True)) > 100:
            break

    # 如果还是找不到，尝试查找最大的文本块
    if not content_div or len(content_div.get_text(strip=True)) < 100:
        all_divs = soup.find_all(['div', 'article', 'section'])
        max_text_len = 0
        for div in all_divs:
            text = div.get_text(strip=True)
            if len(text) > max_text_len:
                max_text_len = len(text)
                content_div = div

    content = ""
    if content_div and len(content_div.get_text(strip=True)) > 100:
        # 移除不需要的元素
        for unwanted in content_div.select('script, style, .share, .social, .advertisement, .related, nav, aside, footer, .comment, header, .navigation, .menu'):
            unwanted.decompose()

        # 提取文本内容
        content = content_div.get_text(separator='\n', strip=True)

        # 清理空行和多余空白
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n\n'.join(lines)

        # 如果内容太短，可能抓取错了
        if len(content) < 100:
            content = ""

    # 尝试提取发布时间
    publish_time = None
    time_selectors = [
        'time',
        '.post-date',
        '.publish-date',
        '.entry-date',
        '.date',
        'span[class*="date"]',
        'div[class*="date"]',
        'span[class*="time"]'
    ]

    for selector in time_selectors:
        time_elem = soup.select_one(selector)
        if time_elem:
            time_str = time_elem.get('datetime') or time_elem.get_text().strip()

            # 尝试多种时间格式
            time_patterns = [
                r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2}(:\d{2})?)',
                r'(\d{4}[-/]\d{2}[-/]\d{2})',
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                r'(\d{4}\.\d{2}\.\d{2})'
            ]

            for pattern in time_patterns:
                match = re.search(pattern, time_str)
                if match:
                    try:
                        time_text = match.group(1).replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-')
                        # 尝试解析时间
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%d-%m-%Y']:
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

    if content:
        return {
            'content': content,
            'publish_time': publish_time
        }
    else:
        return None

def save_article(conn, article_data):
    """保存文章到数据库"""
    try:
        with conn.cursor() as cursor:
            # 检查文章是否已存在
            cursor.execute(
                "SELECT id, content FROM articles WHERE link = %s OR (title = %s AND source = %s)",
                (article_data['link'], article_data['title'], SOURCE)
            )
            existing = cursor.fetchone()

            if existing:
                if existing['content']:
                    print(f"  ⊙ 文章已存在且有内容，跳过")
                    return False
                else:
                    # 更新已存在但无内容的记录
                    cursor.execute(
                        """UPDATE articles
                           SET content = %s, publish_time = %s, source = %s, tags = %s
                           WHERE id = %s""",
                        (article_data['content'], article_data['publish_time'],
                         SOURCE, TAGS, existing['id'])
                    )
                    print(f"  ✓ 更新已存在记录")
                    conn.commit()
                    return True

            # 插入新记录
            cursor.execute(
                """INSERT INTO articles
                   (title, link, source, tags, content, publish_time, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (article_data['title'], article_data['link'], SOURCE, TAGS,
                 article_data['content'], article_data['publish_time'], datetime.now())
            )
            conn.commit()
            print(f"  ✓ 保存新文章成功 (字数: {len(article_data['content'])})")
            return True

    except Exception as e:
        print(f"  ✗ 保存失败: {e}")
        conn.rollback()
        return False

def crawl_site(start_url, max_articles=100):
    """爬取网站"""
    print("=" * 80)
    print(f"港保保网站爬虫启动 v2 (Playwright)")
    print(f"目标网站: {start_url}")
    print(f"来源标识: {SOURCE}")
    print(f"标签: {TAGS}")
    print(f"最大文章数: {max_articles}")
    print("=" * 80)

    conn = get_connection()
    total_found = 0
    total_saved = 0
    processed_urls = set()

    try:
        # 获取首页HTML
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在获取首页...")
        html = get_page_content(start_url)

        if not html:
            print("✗ 无法获取首页内容")
            return

        # 解析文章列表
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在解析文章列表...")
        articles = parse_article_list(html, start_url)

        print(f"\n找到 {len(articles)} 篇文章")

        # 处理每篇文章
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

            # 随机延时
            time.sleep(random.uniform(*ARTICLE_DELAY_RANGE))

            # 抓取文章内容
            result = parse_article_content(article['link'])

            if result and result['content']:
                # 保存文章
                article_data = {
                    'title': article['title'],
                    'link': article['link'],
                    'content': result['content'],
                    'publish_time': result['publish_time']
                }

                if save_article(conn, article_data):
                    total_saved += 1

                total_found += 1
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
        print(f"{'=' * 80}")

if __name__ == '__main__':
    # 可以从命令行传入URL和最大文章数
    start_url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    max_articles = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    crawl_site(start_url, max_articles)
