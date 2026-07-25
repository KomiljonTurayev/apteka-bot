from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database.db_manager import update_order_status, get_order, get_all_categories, add_medicine
from states.states import AdminState
from keyboards.reply import get_cancel_keyboard, get_main_keyboard
from keyboards.inline import get_categories_keyboard

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(F.text == "👨‍💼 Admin Panel")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Bu bo'lim faqat adminlar uchun!")
        return

    text = """👨‍💼 **Apteka Admin Paneli**

Bot va dori-darmonlar bazasini boshqarishingiz mumkin.

- Dori qo'shish uchun /addmedicine buyrug'ini yuboring.
- Yangi kelgan buyurtmalar avtomatik tariqda shu chatga inline tugmalar bilan tushadi."""
    await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("status_"))
async def change_status(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split("_")
    order_id = int(parts[1])
    new_status = parts[2]

    status_labels = {
        "Accepted": "✅ Qabul qilindi",
        "Delivering": "🚚 Yo'lda (Kuryerda)",
        "Completed": "🎉 Yakunlandi (Yetkazildi)",
        "Cancelled": "❌ Bekor qilindi"
    }

    status_str = status_labels.get(new_status, new_status)
    await update_order_status(order_id, status_str)
    
    await callback.answer(f"Buyurtma #{order_id} statusi: {status_str}")
    await callback.message.edit_text(callback.message.text + f"\n\n🔄 **STATUS YANGILANDI:** {status_str}", parse_mode="Markdown")

    # Notify customer about order status update
    order = await get_order(order_id)
    if order:
        try:
            await bot.send_message(
                order['user_id'],
                f"🔔 **Buyurtmangiz statusi o'zgardi!**\n\n🆔 Buyurtma: **#{order_id}**\n📌 Yangi status: **{status_str}**",
                parse_mode="Markdown"
            )
        except Exception:
            pass

@router.message(F.text == "/addmedicine")
async def start_add_medicine(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminState.waiting_for_med_name)
    await message.answer("➕ **Yangi dori qo'shish**\n\nDori nomini kiriting:", reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

@router.message(AdminState.waiting_for_med_name, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    categories = await get_all_categories()
    
    cats_text = "\n".join([f"{c['id']}. {c['name']}" for c in categories])
    await state.set_state(AdminState.waiting_for_med_category)
    await message.answer(f"Kategoriya ID sini tanlang:\n\n{cats_text}")

@router.message(AdminState.waiting_for_med_category, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_cat(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, son (Kategoriya ID) kiriting.")
        return

    await state.update_data(category_id=int(message.text))
    await state.set_state(AdminState.waiting_for_med_desc)
    await message.answer("Dori tavsifini yozing (qisqacha ko'rsatmalari):")

@router.message(AdminState.waiting_for_med_desc, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminState.waiting_for_med_active)
    await message.answer("Ta'sir etuvchi moddasini yozing (masalan: Paracetamol):")

@router.message(AdminState.waiting_for_med_active, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_active(message: Message, state: FSMContext):
    await state.update_data(active_substance=message.text.strip())
    await state.set_state(AdminState.waiting_for_med_price)
    await message.answer("Dori narxini kiriting (so'mda, masalan 15000):")

@router.message(AdminState.waiting_for_med_price, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except ValueError:
        await message.answer("Iltimos, to'g'ri narx (son) kiriting.")
        return

    await state.update_data(price=price)
    await state.set_state(AdminState.waiting_for_med_stock)
    await message.answer("Zahira miqdorini kiriting (masalan 100):")

@router.message(AdminState.waiting_for_med_stock, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_stock(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, son kiriting.")
        return

    await state.update_data(stock=int(message.text))
    await state.set_state(AdminState.waiting_for_med_prescription)
    await message.answer("Retsept talab qilinadimi? (1 - Ha, 0 - Yo'q):")

@router.message(AdminState.waiting_for_med_prescription, F.text & (F.text != "❌ Bekor qilish"))
async def process_med_prescription(message: Message, state: FSMContext):
    req_prescription = 1 if message.text.strip() == "1" else 0
    data = await state.get_data()

    med_id = await add_medicine(
        category_id=data['category_id'],
        name=data['name'],
        description=data['description'],
        active_substance=data['active_substance'],
        price=data['price'],
        stock=data['stock'],
        requires_prescription=req_prescription
    )

    await state.clear()
    await message.answer(f"✅ **Dori muvaffaqiyatli qo'shildi!** (ID: {med_id})\nNomi: {data['name']}", reply_markup=get_main_keyboard(message.from_user.id), parse_mode="Markdown")
