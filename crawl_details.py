import cloudscraper
from bs4 import BeautifulSoup
import pymysql
from datetime import datetime
import time
import re

def get_article_detail(url):
    print(f"正在抓取詳情: {url}")
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取內容 (kknews 的內容通常在 .article-content 或 <article> 標籤中)
        content_div = soup.find('div', class_='article-content') or soup.find('article')
        content = ""
        if content_div:
            # 移除不需要的元素，如廣告或推薦
            for extra in content_div.find_all(['script', 'style', 'iframe']):
                extra.decompose()
            content = content_div.get_text(separator='\n').strip()
        
        # 提取發佈時間
        # kknews 的時間通常在 meta 標籤或特定的 span 中
        publish_time = None
        time_tag = soup.find('time') or soup.find('span', string=re.compile(r'\d{4}-\d{2}-\d{2}'))
        if time_tag:
            time_str = time_tag.get('datetime') or time_tag.get_text().strip()
            # 嘗試解析時間字符串 (常見格式: 2018-09-10 10:00:00)
            try:
                # 簡單清理
                time_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?', time_str)
                if time_match:
                    publish_time = datetime.strptime(time_match.group(), '%Y-%m-%d %H:%M:%S' if ':' in time_match.group().split()[-1] else '%Y-%m-%d %H:%M')
            except:
                pass
        
        return {
            'content': content,
            'publish_time': publish_time
        }
    except Exception as e:
        print(f"抓取文章詳情出錯: {e}")
        return None

def process_few_articles(limit=3):
    try:
        connection = pymysql.connect(
            host='localhost',
            port=8510,
            user='root',
            password='Uu8297636',
            database='aomen_article_crawl',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # 獲取尚未抓取內容的文章
            cursor.execute("SELECT id, title, link FROM articles WHERE content IS NULL OR content = '' LIMIT %s", (limit,))
            articles = cursor.fetchall()
            
            if not articles:
                print("沒有需要抓取內容的文章")
                return

            for art in articles:
                print(f"\n處理文章: {art['title']}")
                detail = get_article_detail(art['link'])
                
                if detail:
                    sql = "UPDATE articles SET content = %s, publish_time = %s WHERE id = %s"
                    cursor.execute(sql, (detail['content'], detail['publish_time'], art['id']))
                    print(f"✓ 已成功更新內容和時間 (長度: {len(detail['content']) if detail['content'] else 0})")
                    connection.commit()
                
                # 禮貌爬取，延遲 2 秒
                time.sleep(2)
                
    except Exception as e:
        print(f"數據庫處理出錯: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    # 設置一個較大的數字，一次性爬完數據庫中所有剩餘的文章
    process_few_articles(100)
