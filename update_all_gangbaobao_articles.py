#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重新抓取所有港保保文章，替换掉有杂质的内容
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pymysql
from datetime import datetime
import time
import random

DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def clean_content(text):
    """清理文本，移除导航等杂质"""
    lines = text.split('\n')
    clean_lines = []

    # 要过滤的关键词
    skip_keywords = [
        'Nav', 'Home', '首页', '香港保险产品', '香港保险公司', '保险资讯',
        '投保攻略', '售后服务', '投保优惠', '关于我们', '储蓄分红保险',
        '重大疾病保险', '人寿保险', '医疗险', '保险产品对比', '香港友邦',
        '香港保诚', '香港安盛', '香港富通', '香港大都会', '其他保险公司',
        '港险优势', '两地差异', '保险知识', '港险对比评测', '续费攻略',
        '理赔攻略', '香港银行开户', '常见问题', '客户留影', '关注港保保',
        '公众号', '咨询客服', '扫一扫', '备案号', '©', '港保保网站地图',
        '微信扫描', '了解更多保险问题', '港保保致力于', '充裕未来',
        '友邦「充裕未来', '赴港签约保险', '香港保险续费', '咨询电话',
        '客服QQ', '公司地址', '粤ICP备', '本站支持'
    ]

    for line in lines:
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        # 跳过太短的行（通常是导航）
        if len(line) < 8:
            continue
        # 跳过包含关键词的行
        if any(kw in line for kw in skip_keywords):
            continue
        # 跳过纯数字（如"1"）
        if line.isdigit():
            continue

        clean_lines.append(line)

    return '\n\n'.join(clean_lines)

def extract_clean_content(url):
    """提取干净的文章内容"""
    print(f"  → 抓取: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(ignore_https_errors=True)
            page.goto(url, timeout=30000, wait_until='networkidle')
            time.sleep(2)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # 查找所有richContent
        all_rich = soup.find_all(class_=lambda x: x and 'richContent' in str(x))

        # 找到最长的那个
        max_len = 0
        best_content = None

        for elem in all_rich:
            text = elem.get_text(strip=True)
            # 跳过导航、页脚
            if '首页' in text[:100] or '港保保网站地图' in text:
                continue
            if len(text) > max_len:
                max_len = len(text)
                best_content = elem

        if not best_content:
            return None

        # 移除图片、脚本
        for tag in best_content.select('script, style, img'):
            tag.decompose()

        # 获取文本
        raw_text = best_content.get_text(separator='\n', strip=True)

        # 清理
        clean_text = clean_content(raw_text)

        # 添加作者（如果有）
        author_elem = soup.select_one('.newsInfo_author')
        if author_elem:
            author = author_elem.get_text(strip=True)
            clean_text = f"{author}\n\n{clean_text}"

        if len(clean_text) < 100:
            return None

        return clean_text

    except Exception as e:
        print(f"    ✗ 错误: {e}")
        return None

def main():
    print("=" * 80)
    print("重新抓取港保保文章 - 清除杂质")
    print("=" * 80)

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 获取所有港保保文章
    cur.execute("""
        SELECT id, title, link
        FROM articles
        WHERE source = '港保保'
        ORDER BY created_at DESC
    """)

    articles = cur.fetchall()
    print(f"\n找到 {len(articles)} 篇港保保文章\n")

    updated = 0
    failed = 0

    for idx, article in enumerate(articles, 1):
        print(f"[{idx}/{len(articles)}] {article['title'][:40]}")

        # 提取干净内容
        clean_text = extract_clean_content(article['link'])

        if clean_text:
            # 更新数据库
            cur.execute("""
                UPDATE articles
                SET content = %s
                WHERE id = %s
            """, (clean_text, article['id']))
            conn.commit()

            print(f"    ✓ 已更新 ({len(clean_text)} 字)")
            updated += 1
        else:
            print(f"    ✗ 提取失败")
            failed += 1

        # 延时
        time.sleep(random.uniform(1, 2))

    conn.close()

    print(f"\n{'=' * 80}")
    print(f"完成！")
    print(f"成功更新: {updated} 篇")
    print(f"失败: {failed} 篇")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()
