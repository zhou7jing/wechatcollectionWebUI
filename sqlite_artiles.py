import sqlite3

DB_PATH = "articles.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seq TEXT,
        category TEXT,
        account_name TEXT,
        title TEXT,
        url TEXT UNIQUE,           -- URL 为唯一键
        publish_time DATETIME,
        content TEXT,
        source_file TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("数据库初始化完成（Python3）")

if __name__ == "__main__":
    init_db()
