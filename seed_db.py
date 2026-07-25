import asyncio
import os
import aiosqlite
import logging
from database.models import CREATE_TABLES_SQL, DEFAULT_CATEGORIES, DEFAULT_MEDICINES, DEFAULT_BRANCHES
from config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def build_database():
    logging.info(f"Baza fayli: {DB_PATH}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # WAL mode va optimizatsiya
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        
        # Jadvallarni yaratish
        logging.info("Jadvallar va indekslar yaratilmoqda...")
        await db.executescript(CREATE_TABLES_SQL)
        
        # Ustunlar migratsiyasi
        async with db.execute("PRAGMA table_info(medicines)") as cursor:
            med_cols = [row[1] for row in await cursor.fetchall()]
            if 'manufacturer' not in med_cols:
                await db.execute("ALTER TABLE medicines ADD COLUMN manufacturer TEXT")
            if 'country' not in med_cols:
                await db.execute("ALTER TABLE medicines ADD COLUMN country TEXT")

        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_cols = [row[1] for row in await cursor.fetchall()]
            if 'latitude' not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN latitude REAL")
            if 'longitude' not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN longitude REAL")

        async with db.execute("PRAGMA table_info(cart)") as cursor:
            cart_cols = [row[1] for row in await cursor.fetchall()]
            if 'branch_id' not in cart_cols:
                await db.execute("ALTER TABLE cart ADD COLUMN branch_id INTEGER")

        await db.commit()

        # 1. Kategoriyalarni kiritish
        logging.info("Kategoriyalar kiritilmoqda...")
        for cat_name, cat_desc in DEFAULT_CATEGORIES:
            async with db.execute("SELECT id FROM categories WHERE name = ?", (cat_name,)) as cursor:
                if not await cursor.fetchone():
                    await db.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (cat_name, cat_desc))
        await db.commit()

        # 2. Dori-darmonlarni kiritish
        logging.info("50+ dori-darmonlar kiritilmoqda...")
        for med in DEFAULT_MEDICINES:
            cat_id, name, desc, active, price, manufacturer, country, stock, prescription = med
            async with db.execute("SELECT id FROM medicines WHERE name = ?", (name,)) as cursor:
                if not await cursor.fetchone():
                    await db.execute(
                        "INSERT INTO medicines (category_id, name, description, active_substance, price, manufacturer, country, stock, requires_prescription) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (cat_id, name, desc, active, price, manufacturer, country, stock, prescription)
                    )
        await db.commit()

        # 3. Apteka filiallarini kiritish
        logging.info("Apteka filiallari kiritilmoqda...")
        for b_name, b_addr, b_phone, b_hours, b_lat, b_lon in DEFAULT_BRANCHES:
            async with db.execute("SELECT id FROM pharmacy_branches WHERE name = ?", (b_name,)) as cursor:
                if not await cursor.fetchone():
                    await db.execute(
                        "INSERT INTO pharmacy_branches (name, address, phone, work_hours, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
                        (b_name, b_addr, b_phone, b_hours, b_lat, b_lon)
                    )
        await db.commit()

        # 4. Filiallar bo'yicha narxlar va zaxiralarni biriktirish
        logging.info("Filiallar bo'yicha narx va zaxiralar hisoblanmoqda...")
        async with db.execute("SELECT id FROM pharmacy_branches") as b_cursor:
            branches = [r[0] for r in await b_cursor.fetchall()]
        async with db.execute("SELECT id, price FROM medicines") as m_cursor:
            meds = await m_cursor.fetchall()

        for b_id in branches:
            for m_id, base_price in meds:
                async with db.execute("SELECT id FROM branch_medicines WHERE branch_id = ? AND medicine_id = ?", (b_id, m_id)) as cursor:
                    if not await cursor.fetchone():
                        variation = (b_id * 3 + m_id * 5) % 15 - 5
                        branch_price = round(base_price * (1 + variation / 100.0), -2)
                        if branch_price < 1000:
                            branch_price = base_price
                        stock = 20 + (b_id * 7 + m_id * 3) % 60
                        await db.execute(
                            "INSERT INTO branch_medicines (branch_id, medicine_id, price, stock) VALUES (?, ?, ?, ?)",
                            (b_id, m_id, branch_price, stock)
                        )
        await db.commit()

        # Statistika chiqarish
        async with db.execute("SELECT COUNT(*) FROM categories") as c1:
            cats_count = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM medicines") as c2:
            meds_count = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM pharmacy_branches") as c3:
            branches_count = (await c3.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM branch_medicines") as c4:
            bm_count = (await c4.fetchone())[0]

        logging.info("==========================================")
        logging.info("✅ MA'LUMOTLAR BAZASI MUVAFFAQIYATLI YARATILDI!")
        logging.info(f"📁 Jami Kategoriyalar: {cats_count} ta")
        logging.info(f"💊 Jami Dorilar: {meds_count} ta")
        logging.info(f"🏬 Jami Filiallar: {branches_count} ta")
        logging.info(f"📊 Filiallardagi Narx Yozuvlari: {bm_count} ta")
        logging.info("==========================================")

if __name__ == "__main__":
    asyncio.run(build_database())
