import cloudscraper
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time
import random
import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

PAGE_DELAY_RANGE = (0, 0)  # 无延迟
MAX_RETRIES = 3  # 最大重试次数
CONCURRENT_WORKERS = 50  # 并发线程数

# 1024代理配置
PROXY_HOST = 'us.1024proxy.io:3000'
PROXY_USERNAME = 'wk4n3645-region-Rand'
PROXY_PASSWORD = 'tw2fvu8c'

# 线程锁，用于保护数据库操作
db_lock = threading.Lock()

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

def parse_page(url, use_proxy=True, retry_count=0):
    """抓取正文文字内容（仅提取内容，不提取新链接）"""
    # 无延迟
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在分析: {url}")

    try:
        proxy = get_proxy() if use_proxy else None

        # 添加更真实的请求头
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
        print(f"[状态] HTTP {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"HTTP状态码: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 锁定正文容器
        content_div = soup.select_one('article') or soup.select_one('#content')
        content = ""

        if content_div:
            # 清理杂质
            for unwanted in content_div.select('.author-info, .social-share, .adsbygoogle, .article-relevant, .qr-code, img, script, style'):
                unwanted.decompose()

            # 提取纯文本内容，保留段落换行
            content = content_div.get_text(separator='\n')
            # 清理多余空行，但保留段落换行
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n\n'.join(lines)

        # 2. 提取发布时间
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
        print(f"抓取出错: {e}")

        # 重试逻辑
        if retry_count < MAX_RETRIES:
            print(f"[重试] 第 {retry_count + 1}/{MAX_RETRIES} 次重试...")
            # 如果是403错误，会自动轮询到下一个代理
            if '403' in str(e):
                print(f"[代理] 403错误，将在重试时使用下一个代理")
            time.sleep(random.uniform(1, 2))  # 重试前等待1-2秒
            return parse_page(url, use_proxy, retry_count + 1)
        else:
            print(f"[失败] 已达到最大重试次数，放弃该页面")
            return None

def process_article(article_data):
    """处理单个文章的抓取任务"""
    article_id = article_data['id']
    link = article_data['link']
    title = article_data['title']

    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [线程] 开始抓取: {title[:30]}...")

        result = parse_page(link)

        if result and result['content']:
            # 使用线程锁保护数据库操作
            with db_lock:
                conn = get_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE articles SET content = %s, publish_time = %s WHERE id = %s",
                            (result['content'], result['publish_time'], article_id)
                        )
                        conn.commit()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 成功保存: {title[:30]}... (字数: {len(result['content'])})")
                    return {'success': True, 'article_id': article_id}
                finally:
                    conn.close()
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 抓取失败: {title[:30]}...")
            return {'success': False, 'article_id': article_id}

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 处理出错: {title[:30]}... - {e}")
        return {'success': False, 'article_id': article_id}

def run_crawler():
    """并发抓取现有文章的内容，不新增文章"""
    print("=== 文章内容补充爬虫启动 (并发模式) ===")
    print(f"说明: 只填充现有文章的内容，不会新增文章")
    print(f"并发线程数: {CONCURRENT_WORKERS}\n")

    total_processed = 0
    total_success = 0

    try:
        while True:
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    # 统计还有多少文章需要抓取内容
                    cursor.execute("SELECT COUNT(*) as count FROM articles WHERE content IS NULL OR content = '' OR content = '抓取失败'")
                    pending_count = cursor.fetchone()['count']

                    if pending_count == 0:
                        print(f"\n{'='*60}")
                        print(f"所有文章内容已抓取完成!")
                        print(f"{'='*60}")
                        print(f"总处理: {total_processed} 篇")
                        print(f"成功: {total_success} 篇")
                        print(f"失败: {total_processed - total_success} 篇")
                        if total_processed > 0:
                            print(f"成功率: {total_success / total_processed * 100:.1f}%")
                        print(f"{'='*60}")
                        break

                    # 获取一批待抓取的文章（最多50个）
                    batch_size = min(CONCURRENT_WORKERS, pending_count)
                    cursor.execute(
                        f"SELECT id, link, title FROM articles WHERE content IS NULL OR content = '' OR content = '抓取失败' LIMIT {batch_size}"
                    )
                    articles = cursor.fetchall()

                    print(f"\n{'='*60}")
                    print(f"[进度] 剩余 {pending_count} 篇文章待抓取")
                    print(f"[批次] 本次并发抓取 {len(articles)} 篇")
                    print(f"{'='*60}\n")

            finally:
                conn.close()

            # 使用线程池并发处理
            with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
                # 提交所有任务
                futures = {executor.submit(process_article, article): article for article in articles}

                # 等待所有任务完成
                for future in as_completed(futures):
                    result = future.result()
                    total_processed += 1
                    if result['success']:
                        total_success += 1

            # 显示统计信息
            success_rate = (total_success / total_processed * 100) if total_processed > 0 else 0
            print(f"\n{'='*60}")
            print(f"--- 统计信息 ---")
            print(f"已处理: {total_processed} 篇")
            print(f"成功: {total_success} 篇")
            print(f"失败: {total_processed - total_success} 篇")
            print(f"成功率: {success_rate:.1f}%")
            print(f"{'='*60}\n")

    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print(f"用户中断程序")
        print(f"{'='*60}")
        print(f"已处理: {total_processed} 篇")
        print(f"成功: {total_success} 篇")
        print(f"失败: {total_processed - total_success} 篇")
        if total_processed > 0:
            print(f"成功率: {total_success / total_processed * 100:.1f}%")
        print(f"{'='*60}")
    except Exception as e:
        print(f"程序错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_crawler()
