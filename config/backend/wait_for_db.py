import time
import pymysql
import os

while True:
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "db"),
            user=os.getenv("DB_USER", "pos_user"),
            password=os.getenv("DB_PASSWORD", "pos_pass"),
            database=os.getenv("DB_NAME", "pos_db"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        conn.close()
        print("✅ Database ready")
        break
    except Exception as e:
        print(f"⏳ Waiting for DB... ({e})")
        time.sleep(2)