#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新已有文章的来源和标签字段
"""

import pymysql

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl',
    'charset': 'utf8mb4'
}

def update_existing_articles():
    """更新现有文章的 source 和 tags 字段"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # 更新所有 kknews.cc 来源的文章
        print("正在更新 kknews.cc 来源的文章...")

        cursor.execute("""
            UPDATE articles
            SET source = 'kknews',
                tags = '澳门'
            WHERE link LIKE '%kknews.cc%'
              AND (source IS NULL OR source = '')
        """)

        affected_rows = cursor.rowcount
        connection.commit()

        print(f"✓ 已更新 {affected_rows} 篇文章")
        print("  来源: kknews")
        print("  标签: 澳门")

        # 显示统计信息
        cursor.execute("""
            SELECT source, tags, COUNT(*) as count
            FROM articles
            WHERE source IS NOT NULL
            GROUP BY source, tags
        """)

        results = cursor.fetchall()
        print("\n当前文章统计:")
        print("-" * 60)
        print(f"{'来源':<20} {'标签':<20} {'数量':<10}")
        print("-" * 60)
        for row in results:
            print(f"{row[0] or '未设置':<20} {row[1] or '未设置':<20} {row[2]:<10}")
        print("-" * 60)

    except Exception as e:
        print(f"✗ 更新失败: {e}")
        connection.rollback()
    finally:
        if 'connection' in locals():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    update_existing_articles()
