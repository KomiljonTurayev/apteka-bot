from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_IDS

def get_main_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="🔍 Dori Izlash"),
            KeyboardButton(text="💰 Eng Arzon Narxlar")
        ],
        [
            KeyboardButton(text="📍 Eng Yaqin Aptekalar"),
            KeyboardButton(text="⭐ Sevimlilar")
        ],
        [
            KeyboardButton(text="🤖 AI Farmatsevt"),
            KeyboardButton(text="📸 Retsept Skaneri (AI)")
        ],
        [
            KeyboardButton(text="🛒 Savat"),
            KeyboardButton(text="🏢 Filiallar")
        ]
    ]

    if user_id and user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(text="👨‍💼 Admin Panel")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

def get_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def get_location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
