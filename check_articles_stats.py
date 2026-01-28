#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看文章统计信息
"""

import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl',
    'charset': 'utf8mb4'
}

def show_stats():
    """显示文章统计"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("=" * 80)
        print("文章统计信息")
        print("=" * 80)

        # 按来源和标签分组统计
        cursor.execute("""
            SELECT source, tags, COUNT(*) as count
            FROM articles
            GROUP BY source, tags
            ORDER BY source, tags
        """)

        results = cursor.fetchall()
        print(f"\n{'来源':<15} {'标签':<15} {'数量':>10}")
        print("-" * 80)
        for row in results:
            source = row[0] or '未设置'
            tags = row[1] or '未设置'
            count = row[2]
            print(f"{source:<15} {tags:<15} {count:>10}")

        # 总计
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        print("-" * 80)
        print(f"{'总计':<15} {'':<15} {total:>10}")
        print("=" * 80)

        # 显示最近添加的文章
        cursor.execute("""
            SELECT title, source, tags, created_at
            FROM articles
            ORDER BY created_at DESC
            LIMIT 10
        """)

        results = cursor.fetchall()
        print("\n最近添加的 10 篇文章:")
        print("-" * 80)
        for idx, row in enumerate(results, 1):
            print(f"{idx}. [{row[1]}] {row[0][:50]}")
            print(f"   标签: {row[2]} | 时间: {row[3]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == '__main__':
    show_stats()
