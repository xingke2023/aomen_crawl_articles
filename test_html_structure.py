from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = 'http://gangbaobaohk.com/h-nd-443.html'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(ignore_https_errors=True)
    page.goto(url, timeout=30000)
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, 'html.parser')

print('=== 查找所有div及其class ===')
divs = soup.find_all('div')
div_info = {}
for div in divs:
    classes = ' '.join(div.get('class', []))
    if classes:
        text_len = len(div.get_text(strip=True))
        if text_len > 200:  # 只看有内容的div
            if classes not in div_info or text_len > div_info[classes]:
                div_info[classes] = text_len

# 按文本长度排序
sorted_divs = sorted(div_info.items(), key=lambda x: x[1], reverse=True)
print('\n文本长度最多的div (class):')
for class_name, length in sorted_divs[:10]:
    print(f'  .{class_name}: {length} 字')

# 尝试找到文章正文区域
print('\n=== 查找article标签 ===')
articles = soup.find_all('article')
print(f'找到 {len(articles)} 个 article 标签')
for idx, art in enumerate(articles):
    print(f'  [{idx}] class={art.get("class")}, 文本长度={len(art.get_text(strip=True))}')
