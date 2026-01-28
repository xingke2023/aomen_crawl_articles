import pymysql

def create_images_table():
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
            sql = """
            CREATE TABLE IF NOT EXISTS images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                article_id INT NOT NULL,
                original_url VARCHAR(1000) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                created_at DATETIME,
                INDEX idx_article_id (article_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(sql)
            print("✓ 已成功創建 images 表")
        connection.commit()
    except Exception as e:
        print(f"創建表失敗: {e}")
    finally:
        connection.close()

if __name__ == '__main__':
    create_images_table()
