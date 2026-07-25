from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states.states import AIConsultantState
from services.ai_service import get_pharmacy_consultation, analyze_prescription_image
from keyboards.reply import get_cancel_keyboard, get_main_keyboard

router = Router()

@router.message(F.text.in_(["🤖 AI Farmatsevt", "🤖 AI Farmatsevt Maslahati"]))
async def start_ai_consultant(message: Message, state: FSMContext):
    await state.set_state(AIConsultantState.waiting_for_query)
    text = """🤖 **AI Farmatsevt Maslahatchiga Xush Kelibsiz!**

Sizni qiynayotgan simptomlar, dori-darmonlar yoki ularning dozasi va qo'llanishi haqida savolingizni matn ko'rinishida yozib yuboring.

*Masalan: "Boshim qattiq og'riyapti, qanday dori tavsiya qilasiz?" yoki "Paratsetamol bilan Ibuprofen o'rtasida qanday farq bor?"*"""
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

@router.message(AIConsultantState.waiting_for_query, F.text & (F.text != "❌ Bekor qilish"))
async def process_ai_query(message: Message, state: FSMContext):
    processing_msg = await message.answer("🤖 *Claude AI fikrlamoqda... Biroz kuting...*", parse_mode="Markdown")
    
    reply = await get_pharmacy_consultation(message.text)
    
    await processing_msg.delete()
    await message.answer(reply, parse_mode="Markdown", reply_markup=get_main_keyboard(message.from_user.id))
    await state.clear()

@router.message(F.text.in_(["📸 Retsept Skaneri (AI)", "📸 Retseptni Tahlil Qilish (AI)"]))
async def start_prescription_analysis(message: Message, state: FSMContext):
    await state.set_state(AIConsultantState.waiting_for_prescription_photo)
    text = """📸 **Shifokor Retseptini AI Orqali Skanerlash**

Iltimos, shifokor yozgan retsept yoki dori qutisining aniq tasvirini (fotosuratini) yuboring.

Claude Vision AI tasvirni o'qib, undagi dori nomlari, doza va tavsiyalarni o'zbek tilida tahlil qilib beradi. 👁️"""
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

@router.message(AIConsultantState.waiting_for_prescription_photo, F.photo)
async def process_prescription_photo(message: Message, state: FSMContext, bot: Bot):
    processing_msg = await message.answer("👁️ *Claude Vision AI tasvirni skanerlamoqda... Biroz kuting...*", parse_mode="Markdown")
    
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    image_bytes = downloaded_file.read()

    analysis_result = await analyze_prescription_image(image_bytes, mime_type="image/jpeg")

    await processing_msg.delete()
    await message.answer(analysis_result, parse_mode="Markdown", reply_markup=get_main_keyboard(message.from_user.id))
    await state.clear()

@router.message(AIConsultantState.waiting_for_prescription_photo, ~F.photo & (F.text != "❌ Bekor qilish"))
async def invalid_prescription_input(message: Message):
    await message.answer("Iltimos, retsept yoki dori qutisining **fotosuratini** yuboring.")
