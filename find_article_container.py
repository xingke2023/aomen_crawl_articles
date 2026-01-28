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

# 查找包含文章标题的元素
print('=== 查找标题元素 ===')
title_text = '宏利-活耀人生危疾保2'
title_elem = soup.find(string=lambda s: s and title_text in s)
if title_elem:
    print(f'找到标题: {title_elem}')
    print(f'标题标签: {title_elem.parent.name}')
    print(f'标题class: {title_elem.parent.get("class")}')

    # 向上查找包含正文的父容器
    current = title_elem.parent
    for i in range(5):
        current = current.parent
        if current:
            print(f'\n层级{i+1}: <{current.name}> class={current.get("class")}')
            # 检查是否有兄弟元素包含正文
            siblings = current.find_all(['p', 'div'], recursive=False)
            if siblings:
                print(f'  直接子元素: {len(siblings)} 个')

# 查找所有p标签
print('\n=== 查找所有P标签 ===')
all_p = soup.find_all('p')
print(f'总共 {len(all_p)} 个p标签')

# 查看p标签内容
content_p = []
for p in all_p:
    text = p.get_text(strip=True)
    if len(text) > 50:  # 至少50字的段落
        content_p.append(text)

print(f'有效段落: {len(content_p)} 个')
print('\n前5个有效段落:')
for idx, text in enumerate(content_p[:5], 1):
    print(f'\n[{idx}] {text[:200]}')

# 查找包含特定文字的div（文章开头）
print('\n=== 查找文章开头 ===')
article_start = soup.find(string=lambda s: s and '危疾的影响往往被轻视' in s)
if article_start:
    print(f'找到文章开头所在标签: {article_start.parent.name}')
    print(f'class: {article_start.parent.get("class")}')
    container = article_start.parent.parent
    print(f'父容器: <{container.name}> class={container.get("class")}')
