import pymysql
from app import app, db

def create_database():
    """创建数据库（如果不存在）"""
    connection = None
    try:
        # 连接到MySQL服务器（不指定数据库）
        connection = pymysql.connect(
            host='localhost',
            port=8510,
            user='root',
            password='Uu8297636',
            charset='utf8mb4'
        )

        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute('CREATE DATABASE IF NOT EXISTS aomen_article_crawl CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
            print("✓ 数据库 'aomen_article_crawl' 创建成功或已存在")

        connection.commit()

    except Exception as e:
        print(f"✗ 创建数据库失败: {e}")
        raise
    finally:
        if connection:
            connection.close()

def init_tables():
    """初始化数据表"""
    try:
        with app.app_context():
            # 创建所有表
            db.create_all()
            print("✓ 数据表创建成功")

            # 显示已创建的表
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✓ 已创建的表: {', '.join(tables)}")

    except Exception as e:
        print(f"✗ 创建数据表失败: {e}")
        raise

if __name__ == '__main__':
    print("开始初始化数据库...")
    print("-" * 50)

    # 步骤1: 创建数据库
    print("步骤1: 创建数据库")
    create_database()
    print()

    # 步骤2: 创建数据表
    print("步骤2: 创建数据表")
    init_tables()
    print()

    print("-" * 50)
    print("✓ 数据库初始化完成!")
