import pymysql

def update_schema():
    connection = pymysql.connect(
        host='localhost',
        port=8510,
        user='root',
        password='Uu8297636',
        database='aomen_article_crawl',
        charset='utf8mb4'
    )
    try:
        with connection.cursor() as cursor:
            # 檢查列是否存在
            cursor.execute("SHOW COLUMNS FROM articles LIKE 'is_parsed'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE articles ADD COLUMN is_parsed TINYINT(1) DEFAULT 0")
                print("✓ 已添加 is_parsed 字段")
            else:
                print("✓ is_parsed 字段已存在")
        connection.commit()
    finally:
        connection.close()

if __name__ == '__main__':
    update_schema()
