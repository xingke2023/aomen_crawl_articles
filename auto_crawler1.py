import cloudscraper
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time
import random
import os
import uuid
import sys
import subprocess
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from playwright.sync_api import sync_playwright

# 配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

PAGE_DELAY_RANGE = (2, 4)
ARTICLE_DELAY_RANGE = (1, 3)
IMAGE_DIR = 'downloaded_images'
MAX_RETRIES = 3

# 1024代理配置
PROXY_HOST = 'us.1024proxy.io:3000'
PROXY_USERNAME = 'wk4n3645-region-Rand'
PROXY_PASSWORD = 'tw2fvu8c'

scraper = cloudscraper.create_scraper()

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def get_proxy():
    """通过curl命令从代理服务获取真实代理地址"""
    try:
        # 使用curl命令通过代理获取真实IP信息
        cmd = [
            'curl',
            '-x', PROXY_HOST,
            '-U', f'{PROXY_USERNAME}:{PROXY_PASSWORD}',
            'ipinfo.io'
        ]

        # 执行curl命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # 解析返回的JSON数据
            ip_info = json.loads(result.stdout)
            proxy_ip = ip_info.get('ip', 'Unknown')

            # 构建代理URL格式: http://username:password@host:port
            proxy_url = f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}'

            proxy_config = {
                'http': proxy_url,
                'https': proxy_url
            }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 获取代理成功，当前IP: {proxy_ip}")
            return proxy_config
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 获取代理失败: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 获取代理超时")
        return None
    except json.JSONDecodeError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 解析代理响应失败")
        return None
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 获取代理配置失败: {e}")
        return None

def parse_search_page(search_url, use_proxy=True, retry_count=0):
    """使用Playwright解析搜索结果页面，提取所有文章链接（支持JavaScript动态加载）"""
    time.sleep(random.uniform(*PAGE_DELAY_RANGE))
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在解析搜索页面: {search_url}")

    try:
        # 获取代理配置
        proxy_config = None
        if use_proxy:
            proxy_dict = get_proxy()
            if proxy_dict:
                # 将代理格式转换为Playwright格式
                proxy_url = proxy_dict['http']
                # 解析代理URL: http://username:password@host:port
                import re
                match = re.match(r'http://([^:]+):([^@]+)@([^:]+):(\d+)', proxy_url)
                if match:
                    username, password, host, port = match.groups()
                    proxy_config = {
                        'server': f'http://{host}:{port}',
                        'username': username,
                        'password': password
                    }

        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(
                headless=True,
                proxy=proxy_config
            )

            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            page = context.new_page()

            # 访问搜索页面
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 加载页面...")
            page.goto(search_url, timeout=30000, wait_until='networkidle')

            # 等待搜索结果加载（等待Google自定义搜索结果容器）
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 等待搜索结果加载...")
            try:
                page.wait_for_selector('.gsc-results', timeout=10000)
                time.sleep(3)  # 额外等待确保所有结果加载完成
            except:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 搜索结果容器未找到，可能没有结果")

            # 获取页面HTML
            html = page.content()
            browser.close()

        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html, 'html.parser')
        articles = []

        # 查找搜索结果中的文章链接
        # Google自定义搜索的多种可能选择器
        result_selectors = [
            '.gsc-webResult .gsc-result',
            '.gs-webResult',
            '.gsc-thumbnail-inside',
            'div.gs-result'
        ]

        results = []
        for selector in result_selectors:
            results = soup.select(selector)
            if results:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 使用选择器找到结果: {selector}")
                break

        if not results:
            # 尝试查找所有包含kknews链接的元素
            all_links = soup.find_all('a', href=re.compile(r'kknews\.cc'))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 通过链接匹配找到 {len(all_links)} 个kknews链接")

            for link_elem in all_links:
                try:
                    link = link_elem.get('href', '')
                    title = link_elem.get_text().strip()

                    # 过滤太短的标题
                    if len(title) < 5:
                        # 尝试从父元素获取标题
                        parent = link_elem.find_parent()
                        if parent:
                            title = parent.get_text().strip()

                    if link and len(title) > 5 and 'kknews.cc' in link:
                        # 确保链接是完整的URL
                        if not link.startswith('http'):
                            link = 'https://kknews.cc' + link

                        # 去重
                        if not any(a['link'] == link for a in articles):
                            articles.append({
                                'title': title[:100],  # 限制标题长度
                                'link': link
                            })
                            print(f"  ✓ 找到文章: {title[:60]}")
                except Exception as e:
                    continue
        else:
            # 使用原有的解析逻辑
            for result in results:
                try:
                    # 查找链接
                    link_elem = result.find('a', href=re.compile(r'kknews\.cc'))
                    if not link_elem:
                        continue

                    link = link_elem.get('href', '')
                    title = link_elem.get_text().strip()

                    # 如果标题太短，尝试从其他元素获取
                    if len(title) < 5:
                        title_elem = result.select_one('.gs-title, .gsc-title')
                        if title_elem:
                            title = title_elem.get_text().strip()

                    # 过滤非文章链接
                    if link and ('kknews.cc' in link) and len(title) > 5:
                        # 确保链接是完整的URL
                        if not link.startswith('http'):
                            link = 'https://kknews.cc' + link

                        articles.append({
                            'title': title,
                            'link': link
                        })
                        print(f"  ✓ 找到文章: {title}")
                except Exception as e:
                    print(f"  ✗ 解析单个结果失败: {e}")
                    continue

        print(f"\n[统计] 本页找到 {len(articles)} 篇文章")
        return articles

    except Exception as e:
        print(f"解析搜索页面出错: {e}")

        if retry_count < MAX_RETRIES:
            print(f"[重试] 第 {retry_count + 1}/{MAX_RETRIES} 次重试...")
            if '403' in str(e):
                print(f"[代理] 403错误，将在重试时使用下一个代理")
            time.sleep(random.uniform(3, 8))
            return parse_search_page(search_url, use_proxy, retry_count + 1)
        else:
            print(f"[失败] 已达到最大重试次数")
            return []

def parse_article_content(url, use_proxy=True, retry_count=0):
    """抓取文章正文内容"""
    time.sleep(random.uniform(*ARTICLE_DELAY_RANGE))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在抓取文章: {url}")

    try:
        proxy = get_proxy() if use_proxy else None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://kknews.cc/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = scraper.get(url, timeout=25, proxies=proxy, headers=headers)

        if response.status_code != 200:
            raise Exception(f"HTTP状态码: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 锁定正文容器
        content_div = soup.select_one('article') or soup.select_one('#content')
        content = ""

        if content_div:
            # 清理杂质
            for unwanted in content_div.select('.author-info, .social-share, .adsbygoogle, .article-relevant, .qr-code, img, script, style'):
                unwanted.decompose()

            # 提取纯文本内容，保留段落换行
            content = content_div.get_text(separator='\n')
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n\n'.join(lines)

        # 提取发布时间
        publish_time = None
        time_tag = soup.find('time') or soup.select_one('.article-meta .time')
        if time_tag:
            time_str = time_tag.get('datetime') or time_tag.get_text().strip()
            time_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?', time_str)
            if time_match:
                try:
                    publish_time = datetime.strptime(time_match.group(), '%Y-%m-%d %H:%M:%S' if ':' in time_match.group().split()[-1] else '%Y-%m-%d %H:%M')
                except:
                    pass

        return {
            'content': content,
            'publish_time': publish_time
        }
    except Exception as e:
        print(f"抓取文章出错: {e}")

        if retry_count < MAX_RETRIES:
            print(f"[重试] 第 {retry_count + 1}/{MAX_RETRIES} 次重试...")
            if '403' in str(e):
                print(f"[代理] 403错误，将在重试时使用下一个代理")
            time.sleep(random.uniform(3, 8))
            return parse_article_content(url, use_proxy, retry_count + 1)
        else:
            print(f"[失败] 已达到最大重试次数")
            return None

def get_next_page_url(base_url, next_page):
    """生成下一页的URL"""
    try:
        parsed = urlparse(base_url)

        # 解析fragment中的参数（Google自定义搜索使用#后面的参数）
        fragment = parsed.fragment

        # 提取搜索关键词
        query_match = re.search(r'gsc\.q=([^&]+)', fragment)
        if not query_match:
            return None

        search_query = query_match.group(1)

        # 构建新的URL，更新页码
        new_fragment = f"gsc.tab=0&gsc.q={search_query}&gsc.page={next_page}"

        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            new_fragment
        ))

        return new_url
    except Exception as e:
        print(f"生成下一页URL失败: {e}")
        return None

def run_search_crawler(search_url, max_pages=10):
    """运行搜索结果爬虫"""
    print("=== 搜索结果文章爬虫启动 ===")
    print(f"搜索URL: {search_url}")
    print(f"最大页数: {max_pages}\n")

    conn = get_connection()
    total_articles = 0
    total_success = 0
    base_url = search_url  # 保存原始URL用于生成后续页面

    try:
        for current_page in range(1, max_pages + 1):
            print(f"\n{'='*60}")
            print(f"正在处理第 {current_page} 页")
            print(f"{'='*60}")

            # 生成当前页的URL
            if current_page == 1:
                page_url = search_url
            else:
                page_url = get_next_page_url(base_url, current_page)
                if not page_url:
                    print(f"\n[完成] 无法生成第 {current_page} 页URL，停止翻页")
                    break

            print(f"URL: {page_url}")

            # 解析搜索结果页面
            articles = parse_search_page(page_url)

            if not articles:
                print(f"\n[完成] 第 {current_page} 页没有找到文章，停止翻页")
                break

            # 处理每篇文章
            for idx, article in enumerate(articles, 1):
                print(f"\n--- 文章 {idx}/{len(articles)} ---")
                print(f"标题: {article['title']}")
                print(f"链接: {article['link']}")

                try:
                    with conn.cursor() as cursor:
                        # 检查文章是否已存在（按链接或标题）
                        cursor.execute("SELECT id, content FROM articles WHERE link = %s OR title = %s", (article['link'], article['title']))
                        existing = cursor.fetchone()

                        if existing:
                            if existing['content']:
                                print(f"  ⊙ 文章已存在且有内容，跳过")
                            else:
                                print(f"  ⊙ 标题重复，跳过")
                            continue

                        # 抓取文章内容
                        result = parse_article_content(article['link'])

                        if result and result['content']:
                            # 插入新记录
                            cursor.execute(
                                "INSERT INTO articles (title, link, content, publish_time, created_at) VALUES (%s, %s, %s, %s, %s)",
                                (article['title'], article['link'], result['content'], result['publish_time'], datetime.now())
                            )
                            print(f"  ✓ 保存新文章成功")
                            conn.commit()
                            total_success += 1
                        else:
                            print(f"  ✗ 抓取文章内容失败")

                        total_articles += 1

                except Exception as e:
                    print(f"  ✗ 处理文章失败: {e}")
                    conn.rollback()

            # 如果不是最后一页，等待后继续
            if current_page < max_pages:
                wait_time = random.uniform(3, 6)
                print(f"\n[翻页] 等待 {wait_time:.1f} 秒后访问第 {current_page + 1} 页...")
                time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n\n[中断] 用户停止程序")
    except Exception as e:
        print(f"\n[错误] {e}")
    finally:
        conn.close()
        print(f"\n{'='*60}")
        print(f"爬虫结束")
        print(f"{'='*60}")
        print(f"共处理: {total_articles} 篇文章")
        print(f"成功保存: {total_success} 篇文章")
        print(f"失败: {total_articles - total_success} 篇文章")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python auto_crawler1.py <搜索结果URL> [最大页数]")
        print("例子: python auto_crawler1.py 'https://kknews.cc/search/?q=赌城不是天堂#gsc.tab=0&gsc.q=赌城不是天堂&gsc.page=1' 10")
        sys.exit(1)

    search_url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    run_search_crawler(search_url, max_pages)
