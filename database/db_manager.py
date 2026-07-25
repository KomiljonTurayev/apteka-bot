import aiosqlite
import logging
import math
from config import DB_PATH
from database.models import CREATE_TABLES_SQL, DEFAULT_CATEGORIES, DEFAULT_MEDICINES, DEFAULT_BRANCHES

logger = logging.getLogger(__name__)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance between two coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.executescript(CREATE_TABLES_SQL)
        
        # Check and migrate missing columns in medicines table
        async with db.execute("PRAGMA table_info(medicines)") as cursor:
            med_cols = [row[1] for row in await cursor.fetchall()]
            if 'manufacturer' not in med_cols:
                await db.execute("ALTER TABLE medicines ADD COLUMN manufacturer TEXT")
            if 'country' not in med_cols:
                await db.execute("ALTER TABLE medicines ADD COLUMN country TEXT")

        # Check and migrate missing columns in users table
        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_cols = [row[1] for row in await cursor.fetchall()]
            if 'latitude' not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN latitude REAL")
            if 'longitude' not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN longitude REAL")

        await db.commit()

        # Seed categories if empty
        async with db.execute("SELECT COUNT(*) FROM categories") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                await db.executemany(
                    "INSERT INTO categories (name, description) VALUES (?, ?)",
                    DEFAULT_CATEGORIES
                )
                await db.commit()

        # Upsert default medicines
        for med in DEFAULT_MEDICINES:
            async with db.execute("SELECT COUNT(*) FROM medicines WHERE name = ?", (med[1],)) as cursor:
                exists = (await cursor.fetchone())[0] > 0
                if not exists:
                    await db.execute("""
                        INSERT INTO medicines (category_id, name, description, active_substance, price, manufacturer, country, stock, requires_prescription)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, med)
        await db.commit()

        # Seed branches if empty
        async with db.execute("SELECT COUNT(*) FROM pharmacy_branches") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                await db.executemany(
                    "INSERT INTO pharmacy_branches (name, address, phone, work_hours, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
                    DEFAULT_BRANCHES
                )
                await db.commit()

        # Seed branch_medicines for realistic price variations per branch
        async with db.execute("SELECT COUNT(*) FROM branch_medicines") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                branches = await get_all_branches()
                medicines = await get_all_medicines()
                branch_meds = []
                for b in branches:
                    for idx, m in enumerate(medicines):
                        # Slight variation in price across branches (-5% to +10%)
                        price_multiplier = 1.0 + ((b['id'] * 3 + idx * 7) % 15 - 5) / 100.0
                        branch_price = round(m['price'] * price_multiplier, -2)
                        stock = 30 + (b['id'] * 10 + idx * 5) % 70
                        branch_meds.append((b['id'], m['id'], branch_price, stock))
                
                await db.executemany("""
                    INSERT INTO branch_medicines (branch_id, medicine_id, price, stock)
                    VALUES (?, ?, ?, ?)
                """, branch_meds)
                await db.commit()

    logger.info("Database initialized successfully.")

# --- USER OPS ---
async def add_or_update_user(telegram_id: int, full_name: str, phone_number: str = None, latitude: float = None, longitude: float = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, full_name, phone_number, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
            full_name = excluded.full_name,
            phone_number = COALESCE(excluded.phone_number, users.phone_number),
            latitude = COALESCE(excluded.latitude, users.latitude),
            longitude = COALESCE(excluded.longitude, users.longitude)
        """, (telegram_id, full_name, phone_number, latitude, longitude))
        await db.commit()

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            return await cursor.fetchone()

# --- MEDICINES & MULTI-BRANCH STOCK OPS ---
async def get_all_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories") as cursor:
            return await cursor.fetchall()

async def get_all_medicines():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM medicines") as cursor:
            return await cursor.fetchall()

async def get_medicines_by_category(category_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM medicines WHERE category_id = ?", (category_id,)) as cursor:
            return await cursor.fetchall()

async def get_medicines_sorted_by_price(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM medicines ORDER BY price ASC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

from services.translit import cyrillic_to_latin, normalize_query

async def search_medicines(query: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q_raw = query.strip()
        q_lat = cyrillic_to_latin(q_raw)
        q_norm = normalize_query(q_raw)

        patterns = [f"%{q_raw}%", f"%{q_lat}%", f"%{q_norm}%"]
        
        sql = """
            SELECT DISTINCT * FROM medicines 
            WHERE 
                name LIKE ? OR description LIKE ? OR active_substance LIKE ? OR manufacturer LIKE ? OR country LIKE ?
                OR name LIKE ? OR description LIKE ? OR active_substance LIKE ? OR manufacturer LIKE ? OR country LIKE ?
                OR name LIKE ? OR description LIKE ? OR active_substance LIKE ? OR manufacturer LIKE ? OR country LIKE ?
            ORDER BY price ASC
        """
        params = []
        for p in patterns:
            params.extend([p, p, p, p, p])

        async with db.execute(sql, params) as cursor:
            return await cursor.fetchall()

async def get_medicine(medicine_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM medicines WHERE id = ?", (medicine_id,)) as cursor:
            return await cursor.fetchone()

async def add_medicine(category_id: int, name: str, description: str, active_substance: str, price: float, stock: int = 100, requires_prescription: int = 0, manufacturer: str = "", country: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO medicines (category_id, name, description, active_substance, price, manufacturer, country, stock, requires_prescription)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (category_id, name, description, active_substance, price, manufacturer, country, stock, requires_prescription))
        await db.commit()
        return cursor.lastrowid

async def get_medicine_branches_info(medicine_id: int, user_lat: float = None, user_lon: float = None):
    """Retrieves all pharmacy branches selling this medicine with prices, stock, and distance."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = """
            SELECT bm.price as branch_price, bm.stock as branch_stock, b.*
            FROM branch_medicines bm
            JOIN pharmacy_branches b ON bm.branch_id = b.id
            WHERE bm.medicine_id = ?
            ORDER BY bm.price ASC
        """
        async with db.execute(sql, (medicine_id,)) as cursor:
            rows = await cursor.fetchall()
            
            branches = []
            for r in rows:
                b_dict = dict(r)
                if user_lat and user_lon:
                    b_dict['distance_km'] = round(calculate_distance(user_lat, user_lon, r['latitude'], r['longitude']), 2)
                else:
                    b_dict['distance_km'] = None
                branches.append(b_dict)
            
            return branches

async def get_branch(branch_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pharmacy_branches WHERE id = ?", (branch_id,)) as cursor:
            return await cursor.fetchone()

# --- FAVORITES OPS ---
async def add_favorite(user_id: int, medicine_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO favorites (user_id, medicine_id)
            VALUES (?, ?)
            ON CONFLICT(user_id, medicine_id) DO NOTHING
        """, (user_id, medicine_id))
        await db.commit()

async def remove_favorite(user_id: int, medicine_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM favorites WHERE user_id = ? AND medicine_id = ?", (user_id, medicine_id))
        await db.commit()

async def is_favorite(user_id: int, medicine_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ? AND medicine_id = ?", (user_id, medicine_id)) as cursor:
            return (await cursor.fetchone())[0] > 0

async def get_user_favorites(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT m.* 
            FROM favorites f
            JOIN medicines m ON f.medicine_id = m.id
            WHERE f.user_id = ?
            ORDER BY m.name ASC
        """, (user_id,)) as cursor:
            return await cursor.fetchall()

# --- CART OPS ---
async def add_to_cart(user_id: int, medicine_id: int, quantity: int = 1, branch_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO cart (user_id, medicine_id, branch_id, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, medicine_id, branch_id) DO UPDATE SET
            quantity = quantity + excluded.quantity
        """, (user_id, medicine_id, branch_id, quantity))
        await db.commit()

async def get_user_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.id as cart_id, c.quantity, m.id as medicine_id, m.name, 
                   COALESCE(bm.price, m.price) as price, m.requires_prescription,
                   b.name as branch_name
            FROM cart c
            JOIN medicines m ON c.medicine_id = m.id
            LEFT JOIN branch_medicines bm ON (c.medicine_id = bm.medicine_id AND c.branch_id = bm.branch_id)
            LEFT JOIN pharmacy_branches b ON c.branch_id = b.id
            WHERE c.user_id = ?
        """, (user_id,)) as cursor:
            return await cursor.fetchall()

async def remove_from_cart(cart_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
        await db.commit()

async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()

# --- ORDER OPS ---
async def create_order(user_id: int, total_amount: float, delivery_type: str, address_or_location: str, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, total_amount, delivery_type, address_or_location, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, total_amount, delivery_type, address_or_location, phone))
        order_id = cursor.lastrowid

        cart_items = await get_user_cart(user_id)
        for item in cart_items:
            await db.execute("""
                INSERT INTO order_items (order_id, medicine_id, quantity, price_per_unit)
                VALUES (?, ?, ?, ?)
            """, (order_id, item['medicine_id'], item['quantity'], item['price']))
        
        await clear_cart(user_id)
        await db.commit()
        return order_id

async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()

async def get_order_items(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT oi.*, m.name
            FROM order_items oi
            JOIN medicines m ON oi.medicine_id = m.id
            WHERE oi.order_id = ?
        """, (order_id,)) as cursor:
            return await cursor.fetchall()

async def update_order_status(order_id: int, new_status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        await db.commit()

# --- BRANCHES OPS ---
async def get_all_branches():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pharmacy_branches") as cursor:
            return await cursor.fetchall()

async def get_nearest_branches(user_lat: float, user_lon: float):
    branches = await get_all_branches()
    branch_list = []
    for b in branches:
        dist = calculate_distance(user_lat, user_lon, b['latitude'], b['longitude'])
        branch_dict = dict(b)
        branch_dict['distance_km'] = round(dist, 2)
        branch_list.append(branch_dict)
    
    branch_list.sort(key=lambda x: x['distance_km'])
    return branch_list
