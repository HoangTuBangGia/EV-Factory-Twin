#!/usr/bin/env python3
"""Seed default demo accounts (Designer, Monitor, Admin) into Supabase PostgreSQL."""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg


def load_env_file(env_path: Path) -> None:
    """Simple helper to load .env key-values if not already set."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


async def main() -> None:
    backend_env = Path(__file__).parent.parent / "apps" / "backend" / ".env"
    load_env_file(backend_env)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable is not set.")
        print("Please set DATABASE_URL in apps/backend/.env or export it in your shell.")
        sys.exit(1)

    # Clean up scheme for asyncpg if needed
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    seed_file = Path(__file__).parent.parent / "supabase" / "seed.sql"
    if not seed_file.exists():
        print(f"❌ Error: seed file not found at {seed_file}")
        sys.exit(1)

    sql_content = seed_file.read_text(encoding="utf-8")

    print("📡 Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as err:
        print(f"❌ Connection failed: {err}")
        sys.exit(1)

    try:
        print("🌱 Seeding demo users (Designer, Monitor, Admin)...")
        await conn.execute(sql_content)
        print("✅ Demo users successfully seeded!")
        print("\n--- Seed Accounts Created / Updated ---")
        print("1. Designer: designer@example.com / Designer123!")
        print("2. Monitor:  monitor@example.com  / Monitor123!")
        print("3. Admin:    admin@example.com    / Admin123!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
