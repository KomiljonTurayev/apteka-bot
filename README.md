# 🏥 Apteka AI Hodim — Telegram Bot (`@arzonaptekabot` Analogi)

Anthropic **Claude AI** va **aiogram 3.x** negizida yaratilgan O'zbekistondagi eng zamonaviy, aqlli va tezkor apteka Telegram bot platformasi.

---

## 🌟 Asosiy Imkoniyatlar (Features)

### 1. 🤖 AI Farmatsevt Maslahatchi (Claude AI)
- Foydalanuvchilarning kasallik alomatlari (simptomlar), dori dozalari, ta'sir etuvchi moddalari va nojo'ya ta'sirlari haqidagi savollariga O'zbek tilida atrofli javob beradi.
- Har bir javob ostida tibbiy ogohlantirish (*Medical Disclaimer*) mavjud.

### 2. 📸 Retsept va Dori Qutisini Skanerlash (Claude Vision AI)
- Shifokor qo'lda yozgan retsepti yoki dori qutisining fotosuratini **Claude Vision AI** orqali o'qib, dori nomlarini va dozalarini aniqlab beradi hamda katalogdan mos dorilarni taklif etadi.

### 3. 💰 Eng Arzon Narxlarni Topish
- Katalogdagi va qidiruvdagi dori-darmonlar barcha apteka filiallari bo'yicha eng arzon narxlar tartibida saralanadi.

### 4. 📍 Eng Yaqin Aptekalar (Geolocation & Haversine Formula)
- Foydalanuvchi o'zining Telegram lokatsiyasini yuborganda, **Haversine** formulasi yordamida eng yaqin filiallar va masofa (`km`) avtomatik hisoblab beriladi.

### 5. 🗺️ Interaktiv Xarita Lokatsiyasi
- Har bir apteka filiali ostida **`📍 Filial xaritasini yuborish`** tugmasi bor. Uni bosganda bot Telegram xaritasida (Location map) aptekaning aniq koordinatasini yuboradi.

### 6. ⭐ Sevimlilar (Favorites)
- Tez-tez xarid qilinadigan dorilarni xatcho'plarga saqlab qo'yish hamda bir bosishda savatga o'tkazish.

### 7. 🛒 Savat va Buyurtma (E-Commerce Flow)
- Dorilarni miqdorini oshirish/kamaytirish.
- Yetkazib berish (**Delivery**) yoki Olib ketish (**Self-pickup**) rejimini tanlash.
- Operatorlar/Adminlar uchun tezkor buyurtma xabarnomalari.

### 8. 👨‍💼 Admin Panel va Statuslar
- Yangi buyurtmalarni admin chatida ko'rish va statuslarini real vaqtda yangilash (`✅ Qabul qilindi`, `🚚 Yo'lda`, `🎉 Yakunlandi`, `❌ Bekor qilindi`).
- `/addmedicine` buyrug'i orqali katalogga yangi dori qo'shish.

---

## 🛠 Texnologiyalar Steki (Tech Stack)

| Texnologiya | Vazifasi |
|---|---|
| **Python 3.12** | Asosiy dasturlash tili |
| **Aiogram 3.15+** | Asinxron Telegram Bot freymvorki |
| **Anthropic Claude API** | Sun'iy intellekt (Claude 3.5 Sonnet / Haiku text & vision) |
| **SQLite (aiosqlite)** | WAL mode va Indekslar bilan tezkor ma'lumotlar bazasi (3.9ms query time) |
| **Pillow & Base64** | Retsept va tasvirlarni AI uchun qayta ishlash |
| **python-dotenv** | Konfiguratsiya va maxfiy kalitlarni boshqarish |

---

## 📁 Loyiha Tuzilishi (Project Structure)

```
apteka-bot/
├── config.py             # Konfiguratsiya va .env faylni yuklash
├── main.py               # Botni ishga tushirish (Entry point)
├── .env.example          # Namuna API kalitlar
├── requirements.txt      # Kutubxonalar ro'yxati
├── .gitignore            # Git istisno fayli (Maxfiy kalitlar va baza)
├── database/
│   ├── models.py         # SQLite sxemasi va indekslar
│   └── db_manager.py     # Asinxron CRUD, Haversine masofa va transliteratsiya
├── services/
│   ├── ai_service.py     # Claude AI va Claude Vision funksiyalari
│   └── translit.py       # Kirill <-> Lotin avto-transliterator
├── keyboards/
│   ├── inline.py         # Inline tugmalar (Katalog, Sevimlilar, Xarita)
│   └── reply.py          # Asosiy menyular
├── handlers/
│   ├── user.py           # /start, bekor qilish va filiallar
│   ├── catalog.py        # Dori izlash, arzon narxlar, yaqin aptekalar
│   ├── ai_consultant.py  # AI Farmatsevt va retsept skaneri
│   ├── order.py          # Buyurtma rasmiylashtirish va admin bildirishnomasi
│   └── admin.py          # Admin panel va status boshqaruvi
└── states/
    └── states.py         # FSM holatlari
```

---

## 🚀 Ishga Tushirish Qo'llanmasi (Quick Start)

### 1. Repozitoriyadan nusxa olish:
```bash
git clone https://github.com/KomiljonTurayev/apteka-bot.git
cd apteka-bot
```

### 2. Virtuall muhitni yaratish va kutubxonalarni o'rnatish:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Konfiguratsiyani sozlash:
Papka ichida `.env` faylini yarating va quyidagi kalitlarni kiriting:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY_HERE
ADMIN_IDS=YOUR_ADMIN_TELEGRAM_ID_HERE
```

### 4. Botni ishga tushirish:
```bash
python main.py
```

---

## ☁️ Serverga Joylashtirish (Server Deployment 24/7)

### Variant A: Systemd (Ubuntu / Linux VPS) — Tavsiya Etiladi
1. Serveringizga ulaning va proyektni ko'chiring:
   ```bash
   cd /var/www
   git clone https://github.com/KomiljonTurayev/apteka-bot.git
   cd apteka-bot
   ```
2. `.env` faylini yaratib, kalitlaringizni kiriting.
3. Systemd servisini o'rnating:
   ```bash
   sudo cp apteka-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable apteka-bot
   sudo systemctl start apteka-bot
   ```
4. Holatni tekshirish:
   ```bash
   sudo systemctl status apteka-bot
   ```

### Variant B: Docker & Docker Compose
```bash
docker-compose up -d --build
```

---

## 👨‍💻 Muallif va Litsenziya

- **Dasturchi:** Komiljon Turayev
- **Litsenziya:** MIT License
