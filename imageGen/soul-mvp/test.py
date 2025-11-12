# test_supabase_connection.py
import psycopg2

DATABASE_URL = "postgresql://postgres.lxbsvqznatdkcqxmutgb:030816@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require"
# 计算资源"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("✅ 连接成功，PostgreSQL 版本：", cur.fetchone()[0])
    cur.close()
    conn.close()
except Exception as e:
    print("❌ 连接失败:", e)