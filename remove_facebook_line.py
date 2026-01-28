#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除数据库中所有文章末尾的 "點我分享到Facebook" 行
"""

import pymysql
from config import Config

def remove_facebook_line():
    """删除所有文章内容末尾的 '點我分享到Facebook' 行"""
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

                # 检查是否包含 "點我分享到Facebook"
                if "點我分享到Facebook" in content:
                    # 按行分割内容
                    lines = content.split('\n')

                    # 过滤掉包含 "點我分享到Facebook" 的行
                    filtered_lines = [line for line in lines if "點我分享到Facebook" not in line]

                    # 重新组合内容
                    new_content = '\n'.join(filtered_lines)

                    # 更新数据库
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
    print("开始删除文章中的 '點我分享到Facebook' 行...")
    print("-" * 60)

    # 确认操作
    confirm = input("此操作将修改数据库中的文章内容，是否继续？(yes/no): ")

    if confirm.lower() in ['yes', 'y']:
        remove_facebook_line()
    else:
        print("操作已取消")
