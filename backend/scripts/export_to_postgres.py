# -*- coding: utf-8 -*-
"""Export all local data from SQLite into PostgreSQL for pgAdmin.

Usage:
    python backend/scripts/export_to_postgres.py --password YOUR_POSTGRES_PASSWORD [--dbname paybridge] [--user postgres] [--port 5432]
"""
import argparse
import os
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
for _p in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd
from sqlalchemy import create_engine, text

from app.db.base import Base, init_db

DATA_DIR = BACKEND_DIR / "data"
SQLITE_DB_PATH = DATA_DIR / "payment_data.db" if (DATA_DIR / "payment_data.db").exists() else (DATA_DIR / "opspilot.db")


def create_postgres_db_if_not_exists(user, password, host, port, dbname):
    """Ensure destination database exists in PostgreSQL."""
    try:
        conn = psycopg2.connect(dbname="postgres", user=user, password=password, host=host, port=port)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
        exists = cur.fetchone()
        if not exists:
            print(f"Creating database '{dbname}' in PostgreSQL...")
            cur.execute(f'CREATE DATABASE "{dbname}";')
            print(f"Database '{dbname}' created successfully!")
        else:
            print(f"Database '{dbname}' already exists.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error connecting to PostgreSQL server: {e}")
        return False


def migrate_data(pg_engine, sqlite_engine):
    """Copy all tables and rows from SQLite to PostgreSQL."""
    # List of tables in dependency order
    tables_order = [
        "merchants",
        "customers",
        "users",
        "payment_orders",
        "payment_transactions",
        "payment_events",
        "payment_attempts",
        "refunds",
        "disputes",
        "settlements",
        "settlement_items",
        "gateway_health_metrics",
        "payment_incidents",
        "incident_merchants",
        "reconciliation_discrepancies",
        "payment_ingestion_runs",
        "payment_ingestion_records",
        "alerts",
        "anomalies",
        "workflows",
        "approvals",
        "action_records",
        "audit_logs",
        "evaluation_results",
        "buildings",
        "apartments",
        "devices",
        "water_plans",
        "rental_plans",
        "plan_assignments",
        "water_usage",
        "monthly_revenue",
        "ingestion_runs",
        "validation_results",
    ]

    print("\nTransferring data from SQLite to PostgreSQL...")
    transferred_summary = {}

    with sqlite_engine.connect() as s_conn, pg_engine.begin() as pg_conn:
        # Temporarily disable foreign key constraints for fast bulk load
        pg_conn.execute(text("SET session_replication_role = 'replica';"))

        for table in tables_order:
            try:
                # Check if table exists in SQLite
                check = s_conn.execute(text(f"SELECT 1 FROM sqlite_master WHERE type='table' AND name='{table}';")).fetchone()
                if not check:
                    continue

                # Read from SQLite
                df = pd.read_sql_table(table, con=s_conn)
                if df.empty:
                    continue

                # Write to PostgreSQL
                df.to_sql(table, con=pg_conn, if_exists="append", index=False, method="multi", chunksize=1000)
                transferred_summary[table] = len(df)
                print(f"  [OK] Table '{table}': {len(df):,} rows transferred")
            except Exception as e:
                # If table already has data or error
                print(f"  [WARN] Table '{table}': {e}")

        # Re-enable foreign key constraints
        pg_conn.execute(text("SET session_replication_role = 'DEFAULT';"))

    return transferred_summary


def update_env_file(db_url):
    """Update or create .env with the new PostgreSQL connection string."""
    env_path = PROJECT_ROOT / ".env"
    lines = []
    found = False

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    lines.append(f"DATABASE_URL={db_url}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"\nDATABASE_URL={db_url}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\nUpdated .env with: DATABASE_URL={db_url}")


def main():
    parser = argparse.ArgumentParser(description="Export SQLite data into PostgreSQL for pgAdmin")
    parser.add_argument("--password", "-p", required=True, help="Your PostgreSQL password")
    parser.add_argument("--user", "-u", default="postgres", help="PostgreSQL user (default: postgres)")
    parser.add_argument("--host", default="localhost", help="PostgreSQL host (default: localhost)")
    parser.add_argument("--port", default="5432", help="PostgreSQL port (default: 5432)")
    parser.add_argument("--dbname", "-d", default="paybridge", help="PostgreSQL database name (default: paybridge)")
    args = parser.parse_args()

    print("=" * 65)
    print(" PayBridge SQLite -> PostgreSQL Migration for pgAdmin")
    print("=" * 65)
    print(f"Source SQLite DB : {SQLITE_DB_PATH}")
    print(f"Target Postgres  : postgresql://{args.user}:****@{args.host}:{args.port}/{args.dbname}")
    print("-" * 65)

    if not SQLITE_DB_PATH.exists():
        print(f"Error: Source SQLite database not found at {SQLITE_DB_PATH}")
        sys.exit(1)

    # 1. Ensure Postgres Database exists
    ok = create_postgres_db_if_not_exists(args.user, args.password, args.host, args.port, args.dbname)
    if not ok:
        sys.exit(1)

    # 2. Setup SQLAlchemy engines
    pg_url = f"postgresql+psycopg2://{args.user}:{args.password}@{args.host}:{args.port}/{args.dbname}"
    os.environ["DATABASE_URL"] = pg_url

    pg_engine = create_engine(pg_url)
    sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")

    # 3. Create all tables in PostgreSQL
    print("\nCreating schema & tables in PostgreSQL...")
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=pg_engine)
    print("All tables created in PostgreSQL successfully!")

    # 4. Migrate data
    summary = migrate_data(pg_engine, sqlite_engine)

    # 5. Update .env
    update_env_file(pg_url)

    print("\n" + "=" * 65)
    print(" SUCCESS! Your data is now in PostgreSQL!")
    print("=" * 65)
    print(f"Total tables populated: {len(summary)}")
    print(f"Total rows transferred: {sum(summary.values()):,}")
    print("\nTo view in pgAdmin:")
    print("  1. Open pgAdmin 4")
    print("  2. Connect to Servers -> PostgreSQL 18")
    print(f"  3. Expand Databases -> '{args.dbname}' -> Schemas -> public -> Tables")
    print("  4. Right click on 'payment_transactions' -> View/Edit Data -> All Rows")
    print("=" * 65)


if __name__ == "__main__":
    main()
