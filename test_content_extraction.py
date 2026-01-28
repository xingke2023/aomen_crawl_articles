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

# 查找正文内容区域
print('=== 方法1: 查找 .formMiddle ===')
form_middle = soup.select_one('.formMiddle')
if form_middle:
    # 移除导航和页脚
    for unwanted in form_middle.select('nav, .nav, footer, .footer, aside, .menu, .sidebar'):
        unwanted.decompose()

    text = form_middle.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    print(f'找到文本长度: {len(text)}')
    print('\n前20行:')
    for line in lines[:20]:
        print(f'  {line[:80]}')

    print('\n后10行:')
    for line in lines[-10:]:
        print(f'  {line[:80]}')

print('\n=== 方法2: 查找 .form ===')
form = soup.select_one('.form')
if form:
    # 移除所有class包含nav的元素
    for elem in form.find_all(class_=lambda x: x and ('nav' in str(x).lower() or 'menu' in str(x).lower())):
        elem.decompose()

    # 移除特定的导航区域
    for selector in ['.nav', 'nav', '.menu', '.sidebar', 'aside', 'footer', '.footer', '.webCompany']:
        for elem in form.select(selector):
            elem.decompose()

    paragraphs = form.find_all(['p', 'div'], recursive=True)
    print(f'\n找到 {len(paragraphs)} 个段落')

    # 只保留文本内容较多的段落
    content_parts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        # 过滤掉导航文字
        if len(text) > 30 and not any(word in text for word in ['Nav', '首页', 'Home', '关注港保保', '扫一扫', '备案号']):
            content_parts.append(text)

    print(f'\n过滤后剩余 {len(content_parts)} 个有效段落')
    print('\n前10段:')
    for part in content_parts[:10]:
        print(f'  {part[:100]}...')
