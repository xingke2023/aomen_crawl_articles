import cloudscraper
from bs4 import BeautifulSoup
import uuid

# 1024代理配置
PROXY_HOST = 'us.1024proxy.io:3000'
PROXY_USERNAME_TEMPLATE = 'wk4n3645-region-Rand-sid-{session_id}-t-1'
PROXY_PASSWORD = 'tw2fvu8c'

def test_crawl():
    print("=== 测试爬虫 ===\n")

    # 生成代理
    session_id = uuid.uuid4().hex[:8]
    username = PROXY_USERNAME_TEMPLATE.format(session_id=session_id)
    proxy_url = f'http://{username}:{PROXY_PASSWORD}@{PROXY_HOST}'

    proxy = {
        'http': proxy_url,
        'https': proxy_url
    }

    print(f"1. 代理会话ID: {session_id}")
    print(f"2. 代理地址: {PROXY_HOST}\n")

    # 创建scraper
    scraper = cloudscraper.create_scraper()

    # 测试URL
    test_url = 'https://kknews.cc/story/jeqn22q.html'
    print(f"3. 测试URL: {test_url}\n")

    # 添加请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://kknews.cc/',
        'Connection': 'keep-alive',
    }

    try:
        print("4. 开始请求...")
        response = scraper.get(test_url, proxies=proxy, headers=headers, timeout=30)

        print(f"   ✓ HTTP状态码: {response.status_code}")
        print(f"   ✓ 响应大小: {len(response.text)} 字节\n")

        if response.status_code != 200:
            print(f"✗ 失败: HTTP {response.status_code}")
            print(f"响应内容预览:\n{response.text[:500]}")
            return

        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        print("5. 检查页面结构:")

        # 检查标题
        title = soup.find('title')
        if title:
            print(f"   标题: {title.get_text().strip()}")

        # 检查 .article-content
        content_div = soup.select_one('.article-content')
        if content_div:
            print(f"   ✓ 找到 .article-content")
            text = content_div.get_text(strip=True)
            print(f"   ✓ 内容长度: {len(text)} 字符")
            print(f"   ✓ 内容预览: {text[:200]}...")
        else:
            print(f"   ✗ 未找到 .article-content")
            print("\n   查找其他可能的选择器:")

            # 尝试其他选择器
            selectors = ['article', '.content', '.post-content', 'main', '#content']
            for sel in selectors:
                elem = soup.select_one(sel)
                if elem:
                    text = elem.get_text(strip=True)
                    print(f"     ✓ {sel}: {len(text)} 字符")
                else:
                    print(f"     ✗ {sel}: 未找到")

            # 显示页面主要div
            print("\n   页面主要元素:")
            divs = soup.find_all('div', class_=True, limit=10)
            for div in divs[:5]:
                classes = ' '.join(div.get('class', []))
                print(f"     - div.{classes}")

        print("\n✓ 测试完成!")

    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_crawl()
