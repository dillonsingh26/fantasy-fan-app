import os, pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    from dotenv import load_dotenv
    load_dotenv()
    DB_URL = os.getenv("DATABASE_URL")

engine = create_engine(DB_URL, pool_pre_ping=True)

with engine.begin() as conn:
    # show tables in public schema
    df = pd.read_sql(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        ORDER BY table_name;
    """), conn)

print("Connected! Tables I see:\n", df.to_string(index=False))