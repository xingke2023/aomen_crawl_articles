import cloudscraper
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
import time

def crawl_kknews(url):
    print(f"开始抓取: {url}")
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"抓取失敗，狀態碼: {response.status_code}")
            return []
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 獲取當前頁面標題
        current_title = soup.title.string if soup.title else "無標題"
        print(f"當前頁面標題: {current_title}")
        
        # 提取文章鏈結和標題
        article_links = []
        seen_urls = set()
        
        # 匹配常見的文章路徑
        pattern = re.compile(r'/(story|culture|entertainment|history|health|digital|game)/.*\.html')
        
        for a in soup.find_all('a', href=pattern):
            href = a.get('href')
            title = a.get_text().strip()
            
            # 補全 URL
            if href.startswith('/'):
                full_url = f"https://kknews.cc{href}"
            else:
                full_url = href
                
            if full_url not in seen_urls and title:
                article_links.append({
                    'title': title,
                    'link': full_url
                })
                seen_urls.add(full_url)
        
        return article_links

    except Exception as e:
        print(f"抓取過程中出錯: {e}")
        return []

def save_to_db(articles):
    if not articles:
        return
    
    print(f"正在保存 {len(articles)} 條數據到數據庫...")
    
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
            # 根據用戶提供的結構：title, link, content, publish_time, created_at
            sql = "INSERT INTO articles (title, link, created_at) VALUES (%s, %s, %s)"
            now = datetime.now()
            
            for article in articles:
                # 檢查是否已存在
                cursor.execute("SELECT id FROM articles WHERE link = %s", (article['link'],))
                if cursor.fetchone():
                    continue
                    
                cursor.execute(sql, (
                    article['title'],
                    article['link'],
                    now
                ))
        
        connection.commit()
        print("✓ 數據保存成功")
        
    except Exception as e:
        print(f"✗ 數據庫操作失敗: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    target_url = "https://kknews.cc/story/pgoogee.html"
    articles = crawl_kknews(target_url)
    
    if articles:
        print(f"\n成功抓取到 {len(articles)} 篇文章")
        save_to_db(articles)
    else:
        print("未抓取到任何文章")