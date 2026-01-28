#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除数据库中所有文章内容中的特定点号模式：
.
(空行)
.
(空行)
.
"""

import pymysql
import re
from config import Config

def remove_dot_pattern():
    """删除文章内容中的点号模式（每个点一行，点之间有空行）"""
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

                # 匹配模式：点号(可能有空白) + 换行 + 空行 + 点号(可能有空白) + 换行 + 空行 + 点号(可能有空白)
                # 这个正则匹配：. \n \n . \n \n .
                pattern = r'^\s*\.\s*\n\s*\n\s*\.\s*\n\s*\n\s*\.\s*$'

                # 也匹配多行中的这个模式（不仅仅是整个文本）
                pattern_multiline = r'\n\s*\.\s*\n\s*\n\s*\.\s*\n\s*\n\s*\.\s*\n'

                new_content = content

                # 先处理文本中间出现的模式
                new_content = re.sub(pattern_multiline, '\n', new_content)

                # 处理开头的模式
                new_content = re.sub(r'^\s*\.\s*\n\s*\n\s*\.\s*\n\s*\n\s*\.\s*\n', '', new_content)

                # 处理结尾的模式
                new_content = re.sub(r'\n\s*\.\s*\n\s*\n\s*\.\s*\n\s*\n\s*\.\s*\s*$', '', new_content)

                # 如果内容发生了变化，则更新数据库
                if new_content != content:
                    cursor.execute(
                        "UPDATE articles SET content = %s WHERE id = %s",
                        (new_content, article_id)
                    )

                    updated_count += 1
                    print(f"  - 更新文章 ID: {article_id}")

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
    print("开始删除文章中的点号模式（. 空行 . 空行 .）...")
    print("-" * 60)

    # 确认操作
    confirm = input("此操作将修改数据库中的文章内容，是否继续？(yes/no): ")

    if confirm.lower() in ['yes', 'y']:
        remove_dot_pattern()
    else:
        print("操作已取消")
