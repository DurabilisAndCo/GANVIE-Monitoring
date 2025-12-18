import sqlite3
from datetime import datetime
import pandas as pd

DB_PATH = "ganvie_durable.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS households (
        household_id INTEGER PRIMARY KEY AUTOINCREMENT,
        collected_at TEXT NOT NULL,
        zone TEXT NOT NULL,
        lat REAL,
        lon REAL,
        hh_size INTEGER,
        main_activity TEXT,
        vulnerability TEXT, -- Faible | Moyen | Élevé
        water_improved INTEGER, -- 1/0
        sanitation INTEGER,     -- 1/0
        children_schooling INTEGER, -- 1/0 (au moins un enfant scolarisé)
        health_access INTEGER, -- 1/0
        needs_water INTEGER,
        needs_sanitation INTEGER,
        needs_housing INTEGER,
        needs_education INTEGER,
        needs_health INTEGER,
        needs_economic INTEGER,
        notes TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS water_samples (
        sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
        collected_at TEXT NOT NULL,
        zone TEXT NOT NULL,
        lat REAL,
        lon REAL,
        season TEXT, -- Sèche | Pluies1 | Pluies2
        ph REAL,
        turbidity REAL,
        conductivity REAL,
        e_coli INTEGER,      -- CFU/100ml (simplifié)
        coliforms INTEGER,   -- CFU/100ml (simplifié)
        risk_level TEXT,     -- Conforme | A_surveiller | A_risque
        comments TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS targets (
        id INTEGER PRIMARY KEY CHECK (id=1),
        households_target INTEGER,
        updated_at TEXT
    );
    """)
    cur.execute("INSERT OR IGNORE INTO targets (id, households_target, updated_at) VALUES (1, 1000, ?)", (datetime.now().isoformat(),))

    conn.commit()

# ------------------ Data access helpers ------------------

def upsert_target(conn, households_target: int):
    cur = conn.cursor()
    cur.execute("UPDATE targets SET households_target=?, updated_at=? WHERE id=1", (households_target, datetime.now().isoformat()))
    conn.commit()

def get_target(conn) -> int:
    df = pd.read_sql_query("SELECT households_target FROM targets WHERE id=1", conn)
    return int(df.iloc[0]["households_target"]) if len(df) else 1000

def households_df(conn):
    return pd.read_sql_query("SELECT * FROM households", conn)

def water_df(conn):
    return pd.read_sql_query("SELECT * FROM water_samples", conn)

def insert_household(conn, row: dict):
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"]*len(row))
    cur = conn.cursor()
    cur.execute(f"INSERT INTO households ({cols}) VALUES ({placeholders})", list(row.values()))
    conn.commit()

def insert_water_sample(conn, row: dict):
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"]*len(row))
    cur = conn.cursor()
    cur.execute(f"INSERT INTO water_samples ({cols}) VALUES ({placeholders})", list(row.values()))
    conn.commit()