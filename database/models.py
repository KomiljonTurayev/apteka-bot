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
    ("Shamollash va Isitma", "Isitma tushiruvchi va shamollashga qarshi preparatlar"),
    ("Og'riqsizlantiruvchilar va Spazmolitiklar", "Bosh, tish, bo'g'im og'riqlari hamda spazmlarga qarshi dorilar"),
    ("Oshqozon, Hazm va Ich ketishi", "Hazm qilishni yaxshilovchi, sorbentlar va oshqozon antiseptiklari"),
    ("Yurak, Qon bosimi va Tomirlar", "Qon bosimini me'yorlashtiruvchi va yurak preparatlari"),
    ("Nerv va Tinchlantiruvchilar", "Tinchlantiruvchi va stressga qarshi vositalar"),
    ("Allergiya va Antigistaminlar", "Mavsumiy va umumiy allergiyaga qarshi dori-darmonlar"),
    ("Vitaminlar va Immunitet", "Immunitetni mustahkamlovchi komplekslar va minerallar"),
    ("Antibiyotiklar va Antiseptiklar", "Keng qamrovli antibiyotiklar va mahalliy antiseptiklar"),
    ("Ko'z va Quloq tomchilari", "Ko'z va quloq shamollashlariga qarshi tomchilar"),
    ("Teringa va Surtmalar", "Jarohat va teridagi shamollashlarga qarshi maz va gellar")
]

DEFAULT_MEDICINES = [
    # Category 1: Shamollash va Isitma
    (1, "Парацетамол (Paracetamol) 500mg", "Isitma tushiruvchi va og'riq qoldiruvchi klassik dori. 10 tabletka.", "Парацетамол (Paracetamol)", 4500.0, "Jurabek Laboratories", "O'zbekiston", 300, 0),
    (1, "Тримол (Trimol)", "Shamollash alomatlari va bosh og'rig'iga qarshi tezkor yordam.", "Парацетамол, Кофеин", 11000.0, "Nobel Pharmsanoat", "O'zbekiston", 200, 0),
    (1, "Гриппоколд (Grippokold)", "Gripp va shamollashda burun bitishi va isitmani oladi.", "Парацетамол, Фенилэфрин", 24000.0, "World Medicine", "Buyuk Britaniya", 150, 0),
    (1, "Фервекс (Fervex Limon) 8 sachet", "Gripp va shamollash alomatlariga qarshi kukun ichimlik.", "Парацетамол, Ascorbic Acid", 34000.0, "UPSA", "Fransiya", 100, 0),
    (1, "Терафлю (Teraflu Limon) 10 sachet", "Isitma, qaltirash va burun oqishiga qarshi issiq ichimlik.", "Парацетамол, Фенилэфрин", 48000.0, "Novartis", "Shveytsariya", 90, 0),
    (1, "Колдрекс Хотакт (Coldrex HotRem) 10 sachet", "Kuchli isitma va tomoq og'rig'iga qarshi kukun.", "Парацетамол, Витамин C", 45000.0, "GlaxoSmithKline", "Buyuk Britaniya", 80, 0),

    # Category 2: Og'riqsizlantiruvchilar va Spazmolitiklar
    (2, "Нурофен Экспресс (Nurofen) 200mg", "Tish va bosh og'rig'ida tez ta'sir qiluvchi kapsula. 10 шт.", "Ибупрофен (Ibuprofen)", 36000.0, "Reckitt Benckiser", "Germaniya", 180, 0),
    (2, "Кетанов (Ketanov) 10mg", "Kuchli og'riqlarga qarshi ta'sirchan dori. 10 tabletka.", "Кеторолак (Ketorolac)", 17000.0, "Ranbaxy", "Hindiston", 140, 1),
    (2, "Но-шпа (No-Shpa) 40mg", "Oshqozon, ichak va mushaklar spazmini tez yechadi.", "Дротаверин (Drotaverine)", 28000.0, "Sanofi", "Vengriya", 160, 0),
    (2, "Анальгин (Analgin) 500mg", "Bosh va tish og'riqlariga qarshi samarli tabletka. 10 шт.", "Метамизол натрия", 3500.0, "Borisov Plant", "Belarus", 350, 0),
    (2, "Цитрамон П (Citramon)", "Bosh og'rig'i va past qon bosimida energiya beruvchi dori.", "Парацетамол, Аспирин, Кофеин", 4000.0, "Stada", "Rossiya", 250, 0),
    (2, "Спазмалгон (Spazmalgon)", "Spazm va og'riqni birgalikda bartaraf etuvchi preparat.", "Метамизол, Питофенон", 22000.0, "Sopharma", "Bolgariya", 120, 0),
    (2, "Дексалгин (Dexalgin) 25mg", "O'tkir tish va suyak og'riqlariga qarshi zamonaviy vosita.", "Декскетопрофен", 55000.0, "Menarini", "Italiya", 90, 1),

    # Category 3: Oshqozon, Hazm va Ich ketishi
    (3, "Нифуроксазид-ЛФ (Nifuroksazid-LF) 200mg", "Oshqozon-ichak infeksiyalari va ich ketishiga qarshi antiseptik. 24 kapsula.", "Нифуроксазид (Nifuroxazide)", 38000.0, "Лекфарм (Lekpharm)", "Belarus", 150, 0),
    (3, "Энтерофурил (Enterofuril) 200mg", "Ichak mikrobial buzilishlarida ich ketishga qarshi dori.", "Нифуроксазид (Nifuroxazide)", 52000.0, "Bosnalijek", "Bosniya va Gertsegovina", 110, 0),
    (3, "Лоперамид (Loperamid) 2mg", "O'tkir ich ketishni tez to'xtatuvchi preparat. 10 tabletka.", "Лоперамид (Loperamide)", 6000.0, "Ozon Pharma", "Rossiya", 250, 0),
    (3, "Мезим Форте (Mezim Forte)", "Ovqat hazm qilishni yaxshilovchi fermentiv preparat. 20 шт.", "Панкреатин (Pancreatin)", 27000.0, "Berlin-Chemie", "Germaniya", 170, 0),
    (3, "Смекта Ваниль (Smecta) 10 sachet", "Oshqozon buzilishi va zaharlanishda sorbent dori.", "Диосмектит (Diosmectite)", 34000.0, "Ipsen", "Fransiya", 130, 0),
    (3, "Эспумизан Л (Espumisan) tomchi", "Qorin dam bo'lishi va gaz yig'ilishiga qarshi tomchi.", "Симетикон (Simethicone)", 42000.0, "Berlin-Chemie", "Germaniya", 100, 0),
    (3, "Омепразол (Omeprazol) 20mg", "Jig'ildoq qaynashi va oshqozon yarasiga qarshi kapsula.", "Омепразол (Omeprazole)", 14000.0, "Noble Pharmsanoat", "O'zbekiston", 220, 0),
    (3, "Креон 10000 (Creon) 20 kapsula", "Ferment yetishmovchiligida oshqozonga yordam beruvchi dori.", "Панкреатин (Pancreatin)", 68000.0, "Abbott", "Germaniya", 90, 0),
    (3, "Линекс (Linex) 16 kapsula", "Ichak mikroflorasini tiklovchi probiotik.", "Lactobacillus, Bifidobacterium", 58000.0, "Sandoz", "Sloveniya", 120, 0),

    # Category 4: Yurak, Qon bosimi va Tomirlar
    (4, "Капотен (Kapoten) 25mg", "Qon bosimining to'satdan ko'tarilishida tez yordam. 40 шт.", "Каптоприл (Captopril)", 21000.0, "EGIS", "Vengriya", 110, 1),
    (4, "Конкор (Concor) 5mg", "Yurak urishini me'yorlashtiruvchi va bosim tushiruvchi.", "Бисопролол (Bisoprolol)", 49000.0, "Merck", "Germaniya", 140, 1),
    (4, "Валидол (Validol) 60mg", "Yurak sohasidagi yengil og'riqlar va tinchlantiruvchi dori.", "Ментол эритмаси", 5000.0, "Pharmak", "Ukraina", 300, 0),
    (4, "Корвалол (Corvalol) 25ml", "Yurak spazmi va uyqusizlikda tinchlantiruvchi tomchi.", "Фенобарбитал, Мята", 7000.0, "Pharmak", "Ukraina", 250, 0),
    (4, "Лориста (Lorista) 50mg", "Qon bosimini doimiy me'yorda ushlab turuvchi dori.", "Лозартан (Losartan)", 38000.0, "KRKA", "Sloveniya", 100, 1),
    (4, "Амлодипин (Amlodipin) 5mg", "Yuqori qon bosimiga qarshi uzoq ta'sir etuvchi vosita.", "Амлодипин (Amlodipine)", 9000.0, "Ozon Pharma", "Rossiya", 180, 1),
    (4, "Аспирин Кардио (Aspirin Cardio) 100mg", "Qonni suyultiruvchi va tromblarga qarshi preparat.", "Ацетилсалицил кислотаси", 26000.0, "Bayer", "Germaniya", 200, 0),

    # Category 5: Nerv va Tinchlantiruvchilar
    (5, "Ново-Пассит (Novo-Passit) 200ml", "Asabiylashish, xavotir va uyqusizlikka qarshi sirop.", "O'simliklar ekstrakti", 54000.0, "Teva", "Chexiya", 90, 0),
    (5, "Глицин (Glycine) 100mg", "Aqliy faoliyatni yaxshilovchi va tinchlantiruvchi tabletka.", "Глицин (Glycine)", 8000.0, "Biotiki", "Rossiya", 400, 0),
    (5, "Магне B6 (Magne B6) 50 tab", "Asab tizimi va mushaklar uchun Magniy va B6 vitamini.", "Magnesium, Pyridoxine", 88000.0, "Sanofi", "Fransiya", 130, 0),
    (5, "Валериана (Valerianka) 50 tab", "Tabiiy tinchlantiruvchi o'simlik preparati.", "Валериана ekstrakti", 4500.0, "Borisov Plant", "Belarus", 500, 0),

    # Category 6: Allergiya va Antigistaminlar
    (6, "Супрастин (Suprastin) 25mg", "O'tkir allergik reaksiyalarga qarshi tezkor tabletka.", "Хлоропирамин", 24000.0, "EGIS", "Vengriya", 170, 0),
    (6, "Зодак (Zodak) 10mg", "Mavsumiy va doimiy allergiyaga qarshi 24 soatlik dori.", "Цетиризин (Cetirizine)", 31000.0, "Zentiva", "Chexiya", 140, 0),
    (6, "Цетрин (Cetrin) 10mg", "Qichishish va allergik toshmalarga qarshi samarli vosita.", "Цетиризин (Cetirizine)", 26000.0, "Dr. Reddy's", "Hindiston", 160, 0),
    (6, "Фенистил гель (Fenistil) 30g", "Chaqish va teridagi allergik qichishishga qarshi gel.", "Диметинден", 49000.0, "GSK", "Shveytsariya", 95, 0),

    # Category 7: Vitaminlar va Immunitet
    (7, "Витрум Юниор (Vitrum Junior) 30 tab", "Bolalar va o'smirlar uchun vitamin-mineral kompleks.", "Multivitamin", 92000.0, "Unipharm", "AQSH", 80, 0),
    (7, "Аскорбин кислотаси (C vitamini)", "Immunitetni mustahkamlovchi C vitamini. 20 drajye.", "Ascorbic Acid", 3500.0, "UzPharma", "O'zbekiston", 600, 0),
    (7, "Аевит (Aevit) 30 kapsula", "A va E vitaminlari kompleksi. Teri va ko'zlar uchun.", "Vitamin A, Vitamin E", 12000.0, "Altai Vitaminy", "Rossiya", 220, 0),
    (7, "Кальцемин (Calcemin) 30 tab", "Suyak va tishlar uchun Kaltsiy va D3 vitamini.", "Calcium, Vitamin D3", 62000.0, "Bayer", "AQSH", 110, 0),
    (7, "Супрадин (Supradyn) 10 effervescent", "Quvvat beruvchi va immunitetni oshiruvchi vitamin.", "Multivitamin Complex", 75000.0, "Bayer", "Germaniya", 90, 0),

    # Category 8: Antibiyotiklar va Antiseptiklar
    (8, "Амоксиклав (Amoksiklav) 625mg", "Keng qamrovli antibiyotik. 14 tabletka.", "Amoxicillin, Clavulanic Acid", 73000.0, "Sandoz", "Sloveniya", 90, 1),
    (8, "Азитромицин (Azitromitsin) 500mg", "Nafas yo'llari va tomoq uchun 3 kunlik antibiyotik.", "Азитромицин (Azithromycin)", 29000.0, "Jurabek Laboratories", "O'zbekiston", 130, 1),
    (8, "Мирамистин (Miramistin) 150ml", "Tomoq, og'iz va yara shamollashlariga qarshi sprey antiseptik.", "Мирамистин", 58000.0, "InfaMed", "Rossiya", 110, 0),
    (8, "Хлоргексидин (Chlorhexidine) 100ml", "Jarohat va og'iz bo'shlig'i uchun dezinfeksiyalovchi eritmalar.", "Хлоргексидин 0.05%", 4000.0, "UzPharma", "O'zbekiston", 400, 0),
    (8, "Аугментин (Augmentin) 1000mg", "Kuchli antibiyotik preparat. 14 tabletka.", "Amoxicillin, Clavulanic Acid", 84000.0, "GSK", "Buyuk Britaniya", 85, 1),

    # Category 9: Ko'z va Quloq tomchilari
    (9, "Визин (Visine Classic) 15ml", "Ko me qizarishi, charchog'i va yoshlanishiga qarshi tomchi.", "Тетризолин", 42000.0, "J&J", "Fransiya", 110, 0),
    (9, "Окомистин (Okomistin) 10ml", "Ko'z va quloq bakterial infeksiyalariga qarshi antiseptik.", "Мирамистин", 28000.0, "InfaMed", "Rossiya", 120, 0),
    (9, "Отипакс (Otipax) 16g", "Quloq og'rig'i va otitda og'riqni tez oluvchi tomchi.", "Феназон, Лидокаин", 46000.0, "Biocodex", "Fransiya", 95, 0),

    # Category 10: Teringa va Surtmalar
    (10, "Левомеколь (Levomekol) 40g", "Jarohat, yiring va teridagi shamollashga qarshi maz.", "Хлорамфеникол, Метилурацил", 15000.0, "Nizhpharm", "Rossiya", 200, 0),
    (10, "Фастум гель (Fastum Gel) 50g", "Bo'g'im va mushak og'riqlariga qarshi isituvchi gel.", "Кетопрофен", 52000.0, "Menarini", "Italiya", 110, 0),
    (10, "Бепантен мазь (Bepanthen) 30g", "Teri ko'chishi, yorilishi va bolalar uchun yumshatuvchi maz.", "Декспантенол", 56000.0, "Bayer", "Germaniya", 130, 0)
]

DEFAULT_BRANCHES = [
    ("Markaziy Apteka 24/7 (Amir Temur)", "Toshkent sh., Amir Temur ko'chasi 15-uy", "+998 71 200-00-11", "24/7 (Sutka davomida)", 41.311081, 69.279737),
    ("Chilonzor Filiali (9-kvartal)", "Toshkent sh., Chilonzor 9-kvartal, 2-uy", "+998 71 200-00-22", "08:00 - 23:00", 41.278912, 69.204561),
    ("Yunusobod Filiali (Mega Planet qoshida)", "Toshkent sh., Yunusobod 4-mavze, 10-uy", "+998 71 200-00-33", "08:00 - 22:00", 41.365412, 69.284512),
    ("Mirzo Ulug'bek Filiali (Buyuk Ipak Yo'li)", "Toshkent sh., M.Ulug'bek ko'chasi 45-uy", "+998 71 200-00-44", "08:00 - 23:00", 41.327512, 69.329812),
    ("Sergeli Filiali (Dehqon bozori yonida)", "Toshkent sh., Sergeli 3-mavze, 1-uy", "+998 71 200-00-55", "08:00 - 22:00", 41.223412, 69.215612),
    ("Yashnobod Filiali (Kadeshova bozori)", "Toshkent sh., Yashnobod tumani, Aviasozlar 2-mavze", "+998 71 200-00-66", "08:00 - 23:00", 41.294512, 69.335612),
    ("Shayxontohur Filiali (Samarqand Darvoza)", "Toshkent sh., Qoratosh ko'chasi 5A-uy", "+998 71 200-00-77", "08:00 - 23:00", 41.315612, 69.234512),
    ("Olmazor Filiali (G'afur G'ulom metro)", "Toshkent sh., Sebzor ko'chasi 12-uy", "+998 71 200-00-88", "24/7 (Sutka davomida)", 41.334512, 69.256712)
]
