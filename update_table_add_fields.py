import pymysql
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 8510,
    'user': 'root',
    'password': 'Uu8297636',
    'database': 'aomen_article_crawl',
    'charset': 'utf8mb4'
}

def update_table():
    """添加 source 和 tags 字段到 articles 表"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        print("正在更新 articles 表结构...")

        # 添加 source 字段（来源）
        try:
            cursor.execute("""
                ALTER TABLE articles
                ADD COLUMN source VARCHAR(100) DEFAULT NULL COMMENT '文章来源'
                AFTER link
            """)
            print("✓ 添加 source 字段成功")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⊙ source 字段已存在，跳过")
            else:
                raise

        # 添加 tags 字段（标签）
        try:
            cursor.execute("""
                ALTER TABLE articles
                ADD COLUMN tags VARCHAR(200) DEFAULT NULL COMMENT '文章标签（多个标签用逗号分隔）'
                AFTER source
            """)
            print("✓ 添加 tags 字段成功")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⊙ tags 字段已存在，跳过")
            else:
                raise

        connection.commit()
        print("\n✓ 表结构更新完成")

        # 显示当前表结构
        cursor.execute("DESCRIBE articles")
        columns = cursor.fetchall()
        print("\n当前 articles 表结构：")
        print("-" * 80)
        for col in columns:
            print(f"{col[0]:20} {col[1]:30} {col[2]:10} {col[3]:10}")
        print("-" * 80)

    except Exception as e:
        print(f"✗ 更新失败: {e}")
        connection.rollback()
    finally:
        if 'connection' in locals():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    update_table()
