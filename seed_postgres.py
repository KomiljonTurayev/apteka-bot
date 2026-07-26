import asyncio
import os
import sys
import logging
from config import DATABASE_URL
from database.models import DEFAULT_CATEGORIES, DEFAULT_MEDICINES, DEFAULT_BRANCHES

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

POSTGRES_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS medicines (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    active_substance VARCHAR(255),
    price DOUBLE PRECISION NOT NULL,
    manufacturer VARCHAR(255),
    country VARCHAR(255),
    stock INTEGER DEFAULT 100,
    requires_prescription INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pg_med_name ON medicines(name);
CREATE INDEX IF NOT EXISTS idx_pg_med_active ON medicines(active_substance);
CREATE INDEX IF NOT EXISTS idx_pg_med_price ON medicines(price);

CREATE TABLE IF NOT EXISTS pharmacy_branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    address TEXT NOT NULL,
    phone VARCHAR(100) NOT NULL,
    work_hours VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS branch_medicines (
    id SERIAL PRIMARY KEY,
    branch_id INTEGER NOT NULL REFERENCES pharmacy_branches(id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    price DOUBLE PRECISION NOT NULL,
    stock INTEGER DEFAULT 50,
    UNIQUE(branch_id, medicine_id)
);

CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    full_name VARCHAR(255),
    phone_number VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, medicine_id)
);

CREATE TABLE IF NOT EXISTS cart (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES pharmacy_branches(id) ON DELETE SET NULL,
    quantity INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    total_amount DOUBLE PRECISION NOT NULL,
    delivery_type VARCHAR(100) NOT NULL,
    address_or_location TEXT,
    phone VARCHAR(100) NOT NULL,
    status VARCHAR(100) DEFAULT 'Yangi',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    price_per_unit DOUBLE PRECISION NOT NULL
);
"""

async def build_postgres_db(db_url: str = None):
    url = db_url or DATABASE_URL
    if not url:
        logging.error("❌ DATABASE_URL topilmadi. Iltimos, .env faylida DATABASE_URL ni belgilang.")
        sys.exit(1)

    # Convert postgres:// to postgresql:// if needed for asyncpg
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    logging.info(f"🐘 PostgreSQL Bazasiga ulaninilmoqda...")
    
    import asyncpg
    conn = await asyncpg.connect(url)
    
    try:
        logging.info("🐘 PostgreSQL Jadvallar va Indekslar yaratilmoqda...")
        await conn.execute(POSTGRES_CREATE_TABLES_SQL)

        # 1. Categories
        logging.info("Kategoriyalar joylanmoqda...")
        for cat_name, cat_desc in DEFAULT_CATEGORIES:
            await conn.execute(
                "INSERT INTO categories (name, description) VALUES ($1, $2) ON CONFLICT (name) DO NOTHING",
                cat_name, cat_desc
            )

        # 2. Medicines
        logging.info("50+ Dori-darmonlar joylanmoqda...")
        for med in DEFAULT_MEDICINES:
            cat_id, name, desc, active, price, manufacturer, country, stock, prescription = med
            await conn.execute("""
                INSERT INTO medicines (category_id, name, description, active_substance, price, manufacturer, country, stock, requires_prescription)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (name) DO NOTHING
            """, cat_id, name, desc, active, price, manufacturer, country, stock, prescription)

        # 3. Branches
        logging.info("Apteka Filiallari joylanmoqda...")
        for b_name, b_addr, b_phone, b_hours, b_lat, b_lon in DEFAULT_BRANCHES:
            await conn.execute("""
                INSERT INTO pharmacy_branches (name, address, phone, work_hours, latitude, longitude)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (name) DO NOTHING
            """, b_name, b_addr, b_phone, b_hours, b_lat, b_lon)

        # 4. Branch Medicines
        logging.info("Filiallar bo'yicha narx va zaxiralar joylanmoqda...")
        branches = await conn.fetch("SELECT id FROM pharmacy_branches")
        meds = await conn.fetch("SELECT id, price FROM medicines")

        for b in branches:
            b_id = b['id']
            for m in meds:
                m_id, base_price = m['id'], m['price']
                variation = (b_id * 3 + m_id * 5) % 15 - 5
                branch_price = round(base_price * (1 + variation / 100.0), -2)
                if branch_price < 1000:
                    branch_price = base_price
                stock = 20 + (b_id * 7 + m_id * 3) % 60
                
                await conn.execute("""
                    INSERT INTO branch_medicines (branch_id, medicine_id, price, stock)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (branch_id, medicine_id) DO NOTHING
                """, b_id, m_id, branch_price, stock)

        cats_c = await conn.fetchval("SELECT COUNT(*) FROM categories")
        meds_c = await conn.fetchval("SELECT COUNT(*) FROM medicines")
        branches_c = await conn.fetchval("SELECT COUNT(*) FROM pharmacy_branches")
        bm_c = await conn.fetchval("SELECT COUNT(*) FROM branch_medicines")

        logging.info("==========================================")
        logging.info("✅ POSTGRESQL MA'LUMOTLAR BAZASI TAYYOR!")
        logging.info(f"📁 Jami Kategoriyalar: {cats_c} ta")
        logging.info(f"💊 Jami Dorilar: {meds_c} ta")
        logging.info(f"🏬 Jami Filiallar: {branches_c} ta")
        logging.info(f"📊 Filiallardagi Narx Yozuvlari: {bm_c} ta")
        logging.info("==========================================")

    finally:
        await conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(build_postgres_db(sys.argv[1]))
    else:
        asyncio.run(build_postgres_db())
