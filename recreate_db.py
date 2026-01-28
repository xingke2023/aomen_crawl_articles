import pymysql

def recreate_table():
    connection = None
    try:
        connection = pymysql.connect(
            host='localhost',
            port=8510,
            user='root',
            password='Uu8297636',
            database='aomen_article_crawl',
            charset='utf8mb4'
        )

        with connection.cursor() as cursor:
            # 刪除舊表
            cursor.execute("DROP TABLE IF EXISTS articles")
            print("✓ 已刪除舊的 articles 表")

            # 創建新表
            create_sql = """
            CREATE TABLE articles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                link VARCHAR(1000) NOT NULL,
                content TEXT,
                publish_time DATETIME,
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(create_sql)
            print("✓ 已根據新結構重新創建 articles 表")

        connection.commit()

    except Exception as e:
        print(f"✗ 操作失敗: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == '__main__':
    recreate_table()
