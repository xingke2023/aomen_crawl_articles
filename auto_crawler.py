import cloudscraper
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time
import random
import os
import uuid
import requests

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

PAGE_DELAY_RANGE = (1, 3)
CYCLE_DELAY_RANGE = (300, 600)
IMAGE_DIR = 'downloaded_images'
MAX_RETRIES = 3  # 最大重试次数

# 1024代理配置 - 轮询列表
PROXY_LIST = [
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-jF5hsfwu-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-USeaCU47-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-qEeFubEz-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-5KvfNBCw-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-MDAkYrWu-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-ZcXapuWF-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-QhfpwQND-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-K2MRuv5S-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-DNymsYwD-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-2sS6DbsQ-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-pfvzJh52-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-cQbtAG7w-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-sXWPt3NH-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-SdvXaVAd-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-XigFG5xz-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-ibv2b996-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-2vJTV2X6-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-NTuSBbDT-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-jxrXL12t-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-4rWfSmc6-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-QZHghZaN-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-SaYkfHN8-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-SfWVztwd-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-TrVK1GUS-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-fs1cXUBh-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-2A9mbnYu-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-jdyiKq32-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-n3aPGJwK-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-VXd4gaQu-t-1:tw2fvu8c',
    'us.1024proxy.io:3000:wk4n3645-region-Rand-sid-NisSEHfg-t-1:tw2fvu8c',
]

# 代理轮询索引
current_proxy_index = 0
current_proxy = None

scraper = cloudscraper.create_scraper()

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def get_proxy():
    """轮询获取下一个代理配置"""
    global current_proxy, current_proxy_index

    try:
        # 获取当前代理配置
        proxy_config = PROXY_LIST[current_proxy_index]

        # 解析代理配置: host:port:username:password
        parts = proxy_config.split(':')
        host = parts[0]
        port = parts[1]
        username = parts[2]
        password = parts[3]

        # 构建代理URL格式: http://username:password@host:port
        proxy_url = f'http://{username}:{password}@{host}:{port}'

        current_proxy = {
            'http': proxy_url,
            'https': proxy_url
        }

        # 轮询到下一个代理（循环）
        current_proxy_index = (current_proxy_index + 1) % len(PROXY_LIST)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 使用代理 #{current_proxy_index}/{len(PROXY_LIST)}: {username}")
        return current_proxy

    except Exception as e:
        print(f"获取代理配置失败: {e}")
        return None

def is_article_image(img_tag, src):
    """過濾邏輯：確保只處理正文插圖"""
    blacklist = ['avatar', 'logo', 'icon', 'button', 'ads', 'share', 'pixel', 'loading']
    if any(word in src.lower() for word in blacklist):
        return False
    
    width = img_tag.get('width', '')
    height = img_tag.get('height', '')
    try:
        if (width and int(re.search(r'\d+', width).group()) < 100) or \
           (height and int(re.search(r'\d+', height).group()) < 100):
            return False
    except: pass
    
    if src.startswith('data:image'):
        return False
        
    return True

def download_image(img_url, use_proxy=True):
    """下載圖片並保存為隨機文件名"""
    try:
        if not img_url.startswith('http'):
            if img_url.startswith('//'): img_url = 'https:' + img_url
            else: return None, None

        ext = os.path.splitext(img_url.split('?')[0])[1].lower()
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = '.jpg'

        random_filename = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(IMAGE_DIR, random_filename)

        proxy = get_proxy() if use_proxy else None
        response = scraper.get(img_url, timeout=15, proxies=proxy)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return random_filename, save_path
        return None, None
    except Exception:
        return None, None

def parse_page(url, use_proxy=True, retry_count=0):
    """抓取正文文字内容"""
    time.sleep(random.uniform(*PAGE_DELAY_RANGE))
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

        # 1. 鎖定正文容器（修复：使用 article 标签）
        content_div = soup.select_one('article') or soup.select_one('#content')
        content = ""

        if content_div:
            # 清理雜質
            for unwanted in content_div.select('.author-info, .social-share, .adsbygoogle, .article-relevant, .qr-code, img, script, style'):
                unwanted.decompose()

            # 提取纯文本内容，保留段落换行
            content = content_div.get_text(separator='\n')
            # 清理多余空行，但保留段落换行
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n\n'.join(lines)
            
        # 2. 提取發布時間
        publish_time = None
        time_tag = soup.find('time') or soup.select_one('.article-meta .time')
        if time_tag:
            time_str = time_tag.get('datetime') or time_tag.get_text().strip()
            time_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?', time_str)
            if time_match:
                try: publish_time = datetime.strptime(time_match.group(), '%Y-%m-%d %H:%M:%S' if ':' in time_match.group().split()[-1] else '%Y-%m-%d %H:%M')
                except: pass

        # 3. 提取相關鏈接（从整个页面提取）
        new_links = []
        link_pattern = re.compile(r'/(story|culture|entertainment|history)/.*\.html')
        for a in soup.find_all('a', href=link_pattern):
            title = a.get_text().strip()
            href = a.get('href')
            if href and len(title) > 5:
                full_url = f"https://kknews.cc{href}" if href.startswith('/') else href
                # 去重
                if not any(link['link'] == full_url for link in new_links):
                    new_links.append({'title': title, 'link': full_url})
                
        return {
            'content': content,
            'publish_time': publish_time,
            'new_links': new_links
        }
    except Exception as e:
        print(f"抓取出錯: {e}")

        # 重试逻辑
        if retry_count < MAX_RETRIES:
            print(f"[重试] 第 {retry_count + 1}/{MAX_RETRIES} 次重试...")
            # 如果是403错误，会自动轮询到下一个代理
            if '403' in str(e):
                print(f"[代理] 403错误，将在重试时使用下一个代理")
            time.sleep(random.uniform(3, 8))  # 重试前等待3-8秒
            return parse_page(url, use_proxy, retry_count + 1)
        else:
            print(f"[失败] 已达到最大重试次数，放弃该页面")
            return None

def run_crawler():
    print("=== 文章内容爬虫启动 ===")
    
    while True:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # 優先抓取內容（包括之前标记为"抓取失败"的记录）
                cursor.execute("SELECT id, link, title FROM articles WHERE content IS NULL OR content = '' OR content = '抓取失败' LIMIT 1")
                todo = cursor.fetchone()

                if todo:
                    print(f"\n[任務] {todo['title']}")
                    result = parse_page(todo['link'])
                    if result and result['content']:
                        cursor.execute("UPDATE articles SET content = %s, publish_time = %s WHERE id = %s", (result['content'], result['publish_time'], todo['id']))
                        for link_item in result['new_links']:
                            cursor.execute("SELECT id FROM articles WHERE link = %s OR title = %s", (link_item['link'], link_item['title']))
                            if not cursor.fetchone():
                                cursor.execute("INSERT INTO articles (title, link, created_at) VALUES (%s, %s, %s)", (link_item['title'], link_item['link'], datetime.now()))
                        conn.commit()
                        print(f"✓ 已保存文章内容")
                    else:
                        # 抓取失败，不标记，下次继续尝试
                        print(f"✗ 抓取失败，将在下次继续尝试")
                else:
                    # 擴展模式
                    cursor.execute("SELECT id, link, title FROM articles WHERE is_parsed = 0 ORDER BY created_at DESC LIMIT 1")
                    to_parse = cursor.fetchone()
                    if to_parse:
                        print(f"\n[擴展] {to_parse['title']}")
                        result = parse_page(to_parse['link'])
                        if result:
                            for link_item in result['new_links']:
                                cursor.execute("SELECT id FROM articles WHERE link = %s OR title = %s", (link_item['link'], link_item['title']))
                                if not cursor.fetchone():
                                    cursor.execute("INSERT INTO articles (title, link, created_at) VALUES (%s, %s, %s)", (link_item['title'], link_item['link'], datetime.now()))
                            cursor.execute("UPDATE articles SET is_parsed = 1 WHERE id = %s", (to_parse['id'],))
                            conn.commit()
                    else:
                        sleep_time = random.uniform(*CYCLE_DELAY_RANGE)
                        print(f"\n[!] 休息中... {sleep_time/60:.1f} 分鐘")
                        time.sleep(sleep_time)
        except Exception as e:
            print(f"錯誤: {e}")
            time.sleep(60)
        finally:
            conn.close()

if __name__ == '__main__':
    run_crawler()