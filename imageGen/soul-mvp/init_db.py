"""
数据库初始化脚本
基于soul.md第10节的DDL创建所有表
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mvpdbuser:mvpdbpw@localhost:5432/mvpdb")

# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=True)


def create_tables():
    """创建所有数据库表"""
    
    # Soul表
    soul_table_sql = """
    CREATE TABLE IF NOT EXISTS soul (
      soul_id       TEXT PRIMARY KEY,
      display_name  TEXT NOT NULL,
      updated_at_ts BIGINT NOT NULL
    );
    """
    
    # Soul风格配置表
    soul_style_profile_sql = """
    CREATE TABLE IF NOT EXISTS soul_style_profile (
      soul_id          TEXT PRIMARY KEY,
      base_model_ref   TEXT NOT NULL,
      lora_ids_json    JSONB NOT NULL,
      palette_json     JSONB NOT NULL,
      negatives_json   JSONB NOT NULL,
      motion_module    TEXT,
      extra_json       JSONB NOT NULL DEFAULT '{}',
      updated_at_ts    BIGINT NOT NULL
    );
    """
    
    # 提示词键表
    prompt_key_sql = """
    CREATE TABLE IF NOT EXISTS prompt_key (
      pk_id         TEXT PRIMARY KEY,
      soul_id       TEXT NOT NULL,
      key_norm      TEXT NOT NULL,
      key_hash      TEXT NOT NULL,
      key_embed     BYTEA,
      meta_json     JSONB NOT NULL DEFAULT '{}',
      updated_at_ts BIGINT NOT NULL
    );
    """
    
    # 变体表
    variant_sql = """
    CREATE TABLE IF NOT EXISTS variant (
      variant_id    TEXT PRIMARY KEY,
      pk_id         TEXT NOT NULL,
      soul_id       TEXT NOT NULL,
      asset_url     TEXT NOT NULL,
      storage_key   TEXT NOT NULL,
      seed          BIGINT,
      phash         BIGINT,
      meta_json     JSONB NOT NULL DEFAULT '{}',
      updated_at_ts BIGINT NOT NULL
    );
    """
    
    # 用户已看记录表
    user_seen_sql = """
    CREATE TABLE IF NOT EXISTS user_seen (
      user_id       TEXT NOT NULL,
      variant_id    TEXT NOT NULL,
      seen_at_ts    BIGINT NOT NULL,
      PRIMARY KEY (user_id, variant_id)
    );
    """
    
    # 地标日志表
    landmark_log_sql = """
    CREATE TABLE IF NOT EXISTS landmark_log (
        soul_id       TEXT NOT NULL,
        city_key      TEXT NOT NULL,
        landmark_key  TEXT NOT NULL,
        user_id       TEXT NOT NULL DEFAULT '',
        used_at_ts    BIGINT NOT NULL,
        PRIMARY KEY (soul_id, city_key, landmark_key, user_id)
    );
    """
    
    # 工作锁表
    work_lock_sql = """
    CREATE TABLE IF NOT EXISTS work_lock (
      lock_key      TEXT PRIMARY KEY,
      owner_id      TEXT NOT NULL,
      expires_at_ts BIGINT NOT NULL,
      updated_at_ts BIGINT NOT NULL
    );
    """
    
    # 幂等性表
    idempotency_sql = """
    CREATE TABLE IF NOT EXISTS idempotency (
      idem_key      TEXT PRIMARY KEY,
      result_json   JSONB NOT NULL,
      updated_at_ts BIGINT NOT NULL
    );
    """
    
    # 执行所有SQL
    with engine.connect() as conn:
        conn.execute(text(soul_table_sql))
        conn.execute(text(soul_style_profile_sql))
        conn.execute(text(prompt_key_sql))
        conn.execute(text(variant_sql))
        conn.execute(text(user_seen_sql))
        conn.execute(text(landmark_log_sql))
        conn.execute(text(work_lock_sql))
        conn.execute(text(idempotency_sql))
        conn.commit()
        
        print("所有数据库表创建成功！")


def create_indexes():
    """创建索引（可选，用于性能优化）"""
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_prompt_key_soul_id ON prompt_key(soul_id);",
        "CREATE INDEX IF NOT EXISTS idx_variant_pk_id ON variant(pk_id);",
        "CREATE INDEX IF NOT EXISTS idx_variant_soul_id ON variant(soul_id);",
        "CREATE INDEX IF NOT EXISTS idx_user_seen_user_id ON user_seen(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_landmark_log_soul_city ON landmark_log(soul_id, city_key);",
        "CREATE INDEX IF NOT EXISTS idx_work_lock_expires ON work_lock(expires_at_ts);",
    ]
    
    with engine.connect() as conn:
        for sql in indexes_sql:
            conn.execute(text(sql))
        conn.commit()
        
        print("所有索引创建成功！")


def insert_sample_data():
    """插入示例数据"""
    
    # 插入示例Soul
    sample_souls_sql = """
    INSERT INTO soul (soul_id, display_name, updated_at_ts) VALUES
    ('nova', 'Nova', EXTRACT(EPOCH FROM NOW()) * 1000),
    ('valentina', 'Valentina', EXTRACT(EPOCH FROM NOW()) * 1000)
    ON CONFLICT (soul_id) DO NOTHING;
    """
    
    # 插入示例风格配置
    sample_styles_sql = """
    INSERT INTO soul_style_profile (soul_id, base_model_ref, lora_ids_json, palette_json, negatives_json, motion_module, extra_json, updated_at_ts) VALUES
    ('nova', 'dreamshaper_8', '["anime_style@v1", "pastel_colors@v2"]', '{"primary": "#FFB6C1", "secondary": "#87CEEB"}', '["blurry", "low quality"]', 'animate_diff_v1', '{"strength": 0.8}', EXTRACT(EPOCH FROM NOW()) * 1000),
    ('valentina', 'realistic_vision_v5', '["realistic_portrait@v1", "elegant_style@v2"]', '{"primary": "#8B0000", "secondary": "#FFD700"}', '["cartoon", "anime"]', 'animate_diff_v1', '{"strength": 0.9}', EXTRACT(EPOCH FROM NOW()) * 1000)
    ON CONFLICT (soul_id) DO NOTHING;
    """
    
    with engine.connect() as conn:
        conn.execute(text(sample_souls_sql))
        conn.execute(text(sample_styles_sql))
        conn.commit()
        
        print("示例数据插入成功！")


def test_connection():
    """测试数据库连接"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"数据库连接成功！PostgreSQL版本: {version}")
            return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False


if __name__ == "__main__":
    print("开始初始化数据库...")
    
    # 测试连接
    if not test_connection():
        print("请确保PostgreSQL容器正在运行！")
        print("运行命令: docker run -d --name soul-mvp -e POSTGRES_USER=mvpdbuser -e POSTGRES_PASSWORD=mvpdbpw -e POSTGRES_DB=mvpdb -p 5432:5432 postgres:15.14-alpine3.21")
        exit(1)
    
    # 创建表
    create_tables()
    
    # 创建索引
    create_indexes()
    
    # 插入示例数据
    insert_sample_data()
    
    print("数据库初始化完成！")
