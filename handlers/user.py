from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards.reply import get_main_keyboard
from database.db_manager import add_or_update_user, get_all_branches

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await add_or_update_user(user.id, user.full_name)

    welcome_text = f"""Assalomu alaykum, {user.full_name}! 👋

Sizni **Arzon Apteka & AI Farmatsevt** botida ko'rib turganimizdan xursandmiz.

🔍 **Bizning bot orqali:**
- 💰 **Eng Arzon Narxlar**: Dorilarning arzon narxlarini topishingiz;
- 📍 **Eng Yaqin Aptekalar**: Telegram lokatsiyangiz orqali yaqin filiallarni aniqlashingiz;
- ⭐ **Sevimlilar**: Tez-tez kerak bo'ladigan dorilarni saqlab qo'yishingiz;
- 🤖 **AI Farmatsevt (Claude AI)**: Simptomlar va dozalar bo'yicha maslahat olishingiz;
- 📸 **Retsept Skaneri (AI)**: Shifokor retsepti yoki dori qutisidan avtomatik dori izlashingiz mumkin.

Quyidagi menyudan kerakli bo'limni tanlang 👇"""
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(user.id), parse_mode="Markdown")

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Jarayon bekor qilindi. Asosiy menyudasiz.", reply_markup=get_main_keyboard(message.from_user.id))

@router.message(F.text == "🏢 Filiallar")
async def show_branches(message: Message):
    branches = await get_all_branches()
    if not branches:
        await message.answer("Hozircha filiallar ma'lumoti mavjud emas.")
        return

    text = "🏢 **Bizning Dorixona Filiallarimiz:**\n\n"
    for b in branches:
        text += f"📌 **{b['name']}**\n"
        text += f"📍 Manzil: {b['address']}\n"
        text += f"📞 Aloqa: {b['phone']}\n"
        text += f"⏰ Ish vaqti: {b['work_hours']}\n\n"

    text += "📞 **Call-Markaz:** +998 71 200-00-00"
    await message.answer(text, parse_mode="Markdown")
