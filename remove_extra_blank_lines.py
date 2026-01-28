#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除数据库中所有文章内容中多余的空行（超过两行的连续空行）
"""

import pymysql
import re
from config import Config

def remove_extra_blank_lines():
    """删除所有文章内容中超过两行的连续空行"""
    connection = None
    try:
        # 连接到数据库
        connection = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4'
        )

        print("✓ 成功连接到数据库")

        with connection.cursor() as cursor:
            # 查询所有文章
            cursor.execute("SELECT id, content FROM articles WHERE content IS NOT NULL")
            articles = cursor.fetchall()

            print(f"✓ 找到 {len(articles)} 篇文章")

            updated_count = 0

            for article_id, content in articles:
                if not content:
                    continue

                # 使用正则表达式将超过2个连续的换行符替换为2个换行符
                # \n{3,} 匹配3个或更多连续的换行符
                new_content = re.sub(r'\n{3,}', '\n\n', content)

                # 如果内容发生了变化，则更新数据库
                if new_content != content:
                    cursor.execute(
                        "UPDATE articles SET content = %s WHERE id = %s",
                        (new_content, article_id)
                    )

                    updated_count += 1

                    # 计算删除了多少个多余的空行
                    original_newlines = content.count('\n')
                    new_newlines = new_content.count('\n')
                    removed_lines = original_newlines - new_newlines

                    print(f"  - 更新文章 ID: {article_id} (删除了 {removed_lines} 个多余空行)")

            # 提交更改
            connection.commit()

            print()
            print("=" * 60)
            print(f"✓ 完成! 共更新了 {updated_count} 篇文章")
            print("=" * 60)

    except Exception as e:
        print(f"✗ 发生错误: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()
            print("✓ 数据库连接已关闭")

if __name__ == '__main__':
    print("开始删除文章中多余的空行（保留最多2行空行）...")
    print("-" * 60)

    # 确认操作
    confirm = input("此操作将修改数据库中的文章内容，是否继续？(yes/no): ")

    if confirm.lower() in ['yes', 'y']:
        remove_extra_blank_lines()
    else:
        print("操作已取消")
