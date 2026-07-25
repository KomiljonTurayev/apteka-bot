import aiosqlite
import logging

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    active_substance TEXT,
    price REAL NOT NULL,
    manufacturer TEXT,
    country TEXT,
    stock INTEGER DEFAULT 100,
    requires_prescription INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE INDEX IF NOT EXISTS idx_med_name ON medicines(name);
CREATE INDEX IF NOT EXISTS idx_med_active ON medicines(active_substance);
CREATE INDEX IF NOT EXISTS idx_med_price ON medicines(price);

CREATE TABLE IF NOT EXISTS pharmacy_branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    work_hours TEXT NOT NULL,
    latitude REAL,
    longitude REAL
);

CREATE TABLE IF NOT EXISTS branch_medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 50,
    FOREIGN KEY (branch_id) REFERENCES pharmacy_branches(id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    UNIQUE(branch_id, medicine_id)
);

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    full_name TEXT,
    phone_number TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    UNIQUE(user_id, medicine_id)
);

CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    branch_id INTEGER,
    quantity INTEGER DEFAULT 1,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    UNIQUE(user_id, medicine_id, branch_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    delivery_type TEXT NOT NULL,
    address_or_location TEXT,
    phone TEXT NOT NULL,
    status TEXT DEFAULT 'Yangi',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price_per_unit REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
"""

DEFAULT_CATEGORIES = [
    ("Shamollash va Isitma", "Isitma tushiruvchi va shamollashga qarshi dorilar"),
    ("Og'riqsizlantiruvchilar", "Bosh, tish va bo'g'im og'riqlariga qarshi vositalar"),
    ("Oshqozon va Hazm (Ich ketishi)", "Hazm qilish va oshqozon-ichak infeksiyalariga qarshi preparatlar"),
    ("Vitaminlar va Minerallar", "Immunitetni oshiruvchi vitamin komplekslari"),
    ("Yurak va Qon bosimi", "Qon bosimini me'yorlashtiruvchi preparatlar"),
    ("Antibiyotiklar va Antiseptiklar", "Shifokor retsepti bilan beriladigan preparatlar")
]

DEFAULT_MEDICINES = [
    (3, "Нифуроксазид-ЛФ (Nifuroksazid-LF) 200mg", "Oshqozon-ichak infeksiyalari va ich ketishiga qarshi samarali antiseptik. 24 kapsula.", "Нифуроксазид (Nifuroxazide)", 38000.0, "Лекфарм (Lekpharm)", "Belarus", 120, 0),
    (3, "Энтерофурил (Enterofuril) 200mg", "Oshqozon-ichak mikrobial buzilishlarida ich ketishga qarshi dori.", "Нифуроксазид (Nifuroxazide)", 52000.0, "Bosnalijek", "Bosniya va Gertsegovina", 90, 0),
    (3, "Лoperaмид (Loperamid) 2mg", "Otkir va surunkali ich ketishni tez to'xtatuvchi vosita.", "Лoperaмид (Loperamide)", 6000.0, "Ozon Pharma", "Rossiya", 200, 0),
    (3, "Mezim Forte", "Ovqat hazm qilishni yaxshilovchi fermentiv preparat.", "Pancreatin", 27000.0, "Berlin-Chemie", "Germaniya", 110, 0),
    (3, "Smekta (Vanil)", "Ich ketishi va oshqozon buzilishida sorbent dori.", "Diosmectite", 34000.0, "Ipsen", "Fransiya", 75, 0),
    (3, "Espumisan L", "Qorin dam bo'lishi va gaz yig'ilishiga qarshi tomchi.", "Simethicone", 42000.0, "Berlin-Chemie", "Germaniya", 65, 0),
    (1, "Paracetamol 500mg (Парацетамол)", "Isitma va og'riqqa qarshi samarali vosita. 10 ta tabletka.", "Paratsetamol", 4500.0, "Jurabek Laboratories", "O'zbekiston", 200, 0),
    (1, "Trimol (Тримол)", "Shamollash, bosh va bo'g'im og'riqlarida kompleks yordam.", "Paratsetamol, Kofein", 11000.0, "Nobel Pharmsanoat", "O'zbekiston", 150, 0),
    (1, "Grippokold (Гриппоколд)", "Gripp va shamollash alomatlarini tezda bartaraf etadi.", "Paratsetamol, Phenylephrine", 24000.0, "World Medicine", "Buyuk Britaniya", 80, 0),
    (1, "Fervex (Лимон) 8 sachet", "Gripp alomatlariga qarshi kukun ichimlik.", "Paratsetamol, C vitamini", 32000.0, "UPSA", "Fransiya", 90, 0),
    (2, "Nurofen Express 200mg (Нурофен)", "Tez ta'sir etuvchi kapsulalar. Tish va bosh og'rig'iga qarshi.", "Ibuprofen", 36000.0, "Reckitt Benckiser", "Germaniya", 120, 0),
    (2, "Ketanov 10mg (Кетанов)", "Kuchli og'riqsizlantiruvchi vosita. 10 tabletka.", "Ketorolac", 17000.0, "Ranbaxy", "Hindiston", 90, 1),
    (2, "No-Shpa 40mg (Но-шпа)", "Oshqozon va mushaklar spazmiga qarshi samarli dori.", "Drotaverine", 28000.0, "Sanofi", "Vengriya", 110, 0),
    (2, "Анальгин (Analgin) 500mg", "Bosh va tish og'rig'iga qarshi tezkor vosita.", "Metamizole Sodium", 3500.0, "Borisov Plant", "Belarus", 300, 0),
    (4, "Vitrum Junior", "Bolalar va o'smirlar uchun vitamin kompleks.", "Multivitamin", 92000.0, "Unipharm", "AQSH", 50, 0),
    (4, "Askorbin kislotasi (C vitamini)", "Immunitetni mustahkamlovchi C vitamini. 20 ta drajye.", "Ascorbic Acid", 3500.0, "UzPharma", "O'zbekiston", 300, 0),
    (4, "Magne B6 (Магне В6)", "Asab tizimi va mushaklar uchun Magniy va B6 vitamini.", "Magnesium, Pyridoxine", 88000.0, "Sanofi", "Fransiya", 85, 0),
    (5, "Kapoten 25mg (Капотен)", "Qon bosimining to'satdan ko'tarilishida tez yordam.", "Captopril", 21000.0, "EGIS", "Vengriya", 60, 1),
    (5, "Concor 5mg (Конкор)", "Yurak urishini me'yorlashtiruvchi va bosim tushiruvchi.", "Bisoprolol", 49000.0, "Merck", "Germaniya", 95, 1),
    (5, "Валидол (Validol) 60mg", "Yurak sohasidagi yengil og'riqlar va tinchlantiruvchi dori.", "Menthol solution", 5000.0, "Pharmak", "Ukraina", 200, 0),
    (6, "Amoksiklav 625mg (Амоксиклав)", "Keng qamrovli antibiyotik. Shifokor retsepti bilan.", "Amoxicillin, Clavulanic Acid", 73000.0, "Sandoz", "Sloveniya", 40, 1),
    (6, "Azitromitsin 500mg (Азитромицин)", "Kuchli 3 kunlik antibiyotik kursi.", "Azithromycin", 29000.0, "Jurabek Laboratories", "O'zbekiston", 70, 1)
]

DEFAULT_BRANCHES = [
    ("Markaziy Apteka 24/7 (Amir Temur)", "Toshkent sh., Amir Temur ko'chasi 15-uy", "+998 71 200-00-11", "24/7 (Sutka davomida)", 41.311081, 69.279737),
    ("Chilonzor Filiali (9-kvartal)", "Toshkent sh., Chilonzor 9-kvartal, 2-uy", "+998 71 200-00-22", "08:00 - 23:00", 41.278912, 69.204561),
    ("Yunusobod Filiali (Mega Planet qoshida)", "Toshkent sh., Yunusobod 4-mavze, 10-uy", "+998 71 200-00-33", "08:00 - 22:00", 41.365412, 69.284512),
    ("Mirzo Ulug'bek Filiali (Buyuk Ipak Yo'li)", "Toshkent sh., M.Ulug'bek ko'chasi 45-uy", "+998 71 200-00-44", "08:00 - 23:00", 41.327512, 69.329812),
    ("Sergeli Filiali (Dehqon bozori yonida)", "Toshkent sh., Sergeli 3-mavze, 1-uy", "+998 71 200-00-55", "08:00 - 22:00", 41.223412, 69.215612)
]
