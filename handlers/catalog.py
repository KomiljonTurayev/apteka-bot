from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db_manager import (
    get_all_categories, get_medicines_by_category, get_medicine,
    search_medicines, add_to_cart, get_user_cart, remove_from_cart, clear_cart,
    get_medicines_sorted_by_price, get_nearest_branches, get_user_favorites,
    add_favorite, remove_favorite, is_favorite, get_medicine_branches_info,
    get_user, get_branch, add_or_update_user
)
from keyboards.inline import (
    get_categories_keyboard, get_medicines_keyboard,
    get_medicine_detail_keyboard, get_cart_keyboard
)
from keyboards.reply import get_cancel_keyboard, get_main_keyboard, get_location_keyboard
from states.states import SearchState
from services.ai_service import get_pharmacy_consultation

router = Router()

async def execute_medicine_search(message: Message, query: str):
    medicines = await search_medicines(query)
    
    if not medicines:
        processing_msg = await message.answer("🤖 *Bazamizdan aniq topilmadi. Claude AI dan tibbiy ma'lumot izlanmoqda...*", parse_mode="Markdown")
        ai_reply = await get_pharmacy_consultation(f"Mijoz '{query}' nomli dorini izlamoqda. Ushbu dori haqida (ta'sir etuvchi moddasi, nimaga qo'llanilishi) qisqacha ma'lumot bering va uning o'rnini bosuvchi analog dorilarni ayting.")
        await processing_msg.delete()
        
        text = f"🔍 Bazada '{query}' bo'yicha aniq moslik topilmadi.\n\n🤖 AI Farmatsevt Maslahati:\n{ai_reply}"
        try:
            await message.answer(text, reply_markup=get_main_keyboard(message.from_user.id), parse_mode="Markdown")
        except Exception:
            await message.answer(text, reply_markup=get_main_keyboard(message.from_user.id))
    else:
        user_id = message.from_user.id
        db_user = await get_user(user_id)
        db_user_dict = dict(db_user) if db_user else {}
        u_lat = db_user_dict.get('latitude')
        u_lon = db_user_dict.get('longitude')

        text = f"🔍 **'{query}' bo'yicha topilgan dorilar va aptekalar narxlari:**\n\n"
        
        for m in medicines[:3]:
            branches = await get_medicine_branches_info(m['id'], u_lat, u_lon)
            manuf_str = f"🏭 **Ishlab chiqarilgan joyi:** {m['manufacturer']} ({m['country']})\n" if m.get('manufacturer') else ""
            presc_str = "⚠️ Retseptli dori" if m['requires_prescription'] else "🟢 Retsept talab qilinmaydi"
            
            text += f"💊 **{m['name']}**\n"
            text += f"🧪 Ta'sir etuvchi modda: {m['active_substance']}\n"
            text += manuf_str
            text += f"💵 O'rtacha narxi: **{m['price']:,.0f} so'm** ({presc_str})\n"
            text += f"🏢 **Mavjud Aptekalar va Narxlar:**\n"
            
            for b in branches[:4]:
                dist_str = f" ({b['distance_km']} km)" if b.get('distance_km') else ""
                text += f"  • {b['name']}{dist_str} — **{b['branch_price']:,.0f} so'm** (📦 {b['branch_stock']} шт)\n"
                text += f"    📍 {b['address']}\n"
            text += "\n"

        try:
            await message.answer(text, reply_markup=get_medicines_keyboard(medicines), parse_mode="Markdown")
        except Exception:
            await message.answer(text, reply_markup=get_medicines_keyboard(medicines))

@router.message(SearchState.waiting_for_search_query, F.text & (F.text != "❌ Bekor qilish"))
async def process_search_state(message: Message, state: FSMContext):
    query = message.text.strip()
    await execute_medicine_search(message, query)
    await state.clear()

# DIRECT SEARCH HANDLER: Triggers when user sends medicine name directly in chat
@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_([
    "💊 Dorilar Katalogi", "🔍 Dori Izlash", "💰 Eng Arzon Narxlar", "📍 Eng Yaqin Aptekalar",
    "⭐ Sevimlilar", "🤖 AI Farmatsevt", "🤖 AI Farmatsevt Maslahati", "📸 Retsept Skaneri (AI)",
    "📸 Retseptni Tahlil Qilish (AI)", "🛒 Savat", "🛒 Savatcha", "🏢 Filiallar", "🏢 Filiallar va Aloqa",
    "👨‍💼 Admin Panel", "❌ Bekor qilish"
]))
async def direct_medicine_search(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        query = message.text.strip()
        await execute_medicine_search(message, query)

@router.message(F.text == "💰 Eng Arzon Narxlar")
async def show_cheapest_medicines(message: Message):
    medicines = await get_medicines_sorted_by_price(limit=20)
    if not medicines:
        await message.answer("Dorilar topilmadi.")
        return
    await message.answer("💰 **Eng Arzon Dori-Darmonlar Ro'yxati:**", reply_markup=get_medicines_keyboard(medicines), parse_mode="Markdown")

@router.message(F.text == "📍 Eng Yaqin Aptekalar")
async def request_nearest_pharmacies(message: Message):
    text = """📍 **Eng Yaqin Aptekani Topish**

Iltimos, joylashgan o'rningizni (Telegram lokatsiyasini) yuboring.
Bot sizga eng yaqin apteka filiallari va masofasini (km) hisoblab beradi. 🗺️"""
    await message.answer(text, reply_markup=get_location_keyboard(), parse_mode="Markdown")

@router.message(F.location)
async def process_location(message: Message):
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    user_id = message.from_user.id

    # Save user location for future distance calculations
    await add_or_update_user(user_id, message.from_user.full_name, latitude=user_lat, longitude=user_lon)

    nearest_branches = await get_nearest_branches(user_lat, user_lon)
    
    text = "📍 **Sizga Eng Yaqin Apteka Filiallari:**\n\n"
    for b in nearest_branches[:5]:
        text += f"🏢 **{b['name']}** — `{b['distance_km']} km` uzoqlikda\n"
        text += f"📍 Manzil: {b['address']}\n"
        text += f"📞 Telefon: {b['phone']}\n"
        text += f"⏰ Ish vaqti: {b['work_hours']}\n\n"

    await message.answer(text, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

@router.message(F.text == "⭐ Sevimlilar")
async def show_favorites(message: Message):
    user_id = message.from_user.id
    favs = await get_user_favorites(user_id)
    if not favs:
        await message.answer("⭐ Sevimlilar ro'yxatingiz bo'sh.\n\nDori sahifasidagi '⭐ Sevimlilarga qo'shish' tugmasini bosib saqlashingiz mumkin.", reply_markup=get_main_keyboard(user_id))
        return
    await message.answer("⭐ **Sizning Sevimli Dorilaringiz:**", reply_markup=get_medicines_keyboard(favs), parse_mode="Markdown")

@router.callback_query(F.data.startswith("cat_"))
async def show_category_medicines(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    medicines = await get_medicines_by_category(cat_id)
    
    if not medicines:
        await callback.message.edit_text("Ushbu kategoriyada hozircha dorilar mavjud emas.", reply_markup=get_categories_keyboard(await get_all_categories()))
        return
    
    await callback.message.edit_text("💊 **Mavjud dori-darmonlar ro'yxati:**", reply_markup=get_medicines_keyboard(medicines), parse_mode="Markdown")

@router.callback_query(F.data == "back_categories")
async def back_to_categories(callback: CallbackQuery):
    categories = await get_all_categories()
    await callback.message.edit_text("💊 **Kategoriyalardan birini tanlang:**", reply_markup=get_categories_keyboard(categories), parse_mode="Markdown")

@router.callback_query(F.data.startswith("med_"))
async def show_medicine_detail(callback: CallbackQuery):
    med_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    med = await get_medicine(med_id)
    if not med:
        await callback.answer("Dori topilmadi", show_alert=True)
        return

    db_user = await get_user(user_id)
    db_user_dict = dict(db_user) if db_user else {}
    u_lat = db_user_dict.get('latitude')
    u_lon = db_user_dict.get('longitude')

    branches = await get_medicine_branches_info(med_id, u_lat, u_lon)
    is_fav = await is_favorite(user_id, med_id)
    prescription_text = "⚠️ *Ushbu dori faqat shifokor retsepti bo'yicha beriladi!*" if med['requires_prescription'] else "🟢 Retsept talab qilinmaydi."
    manufacturer_info = f"🏭 **Ishlab chiqaruvchi:** {med['manufacturer']} ({med['country']})\n" if med['manufacturer'] else ""

    text = f"""💊 **{med['name']}**

📝 **Tavsif:** {med['description']}
🧪 **Ta'sir etuvchi modda:** {med['active_substance']}
{manufacturer_info}💰 **Asosiy Narxi:** **{med['price']:,.0f} so'm**

🏢 **Mavjud Apteka Filiallaridagi Narxlar va Zaxira:**\n"""

    for b in branches:
        dist_str = f" | 📏 `{b['distance_km']} km`" if b.get('distance_km') else ""
        text += f"• **{b['name']}**{dist_str}\n"
        text += f"  💵 Narxi: **{b['branch_price']:,.0f} so'm** | 📦 Zaxira: {b['branch_stock']} шт\n"
        text += f"  📍 Manzil: {b['address']} | 📞 {b['phone']}\n\n"

    text += f"{prescription_text}"

    await callback.message.edit_text(text, reply_markup=get_medicine_detail_keyboard(med['id'], med['category_id'], branches, is_fav=is_fav), parse_mode="Markdown")

@router.callback_query(F.data.startswith("addcartb_"))
async def handle_add_cart_branch(callback: CallbackQuery):
    parts = callback.data.split("_")
    med_id = int(parts[1])
    branch_id = int(parts[2])
    user_id = callback.from_user.id
    
    med = await get_medicine(med_id)
    branch = await get_branch(branch_id)
    if not med or not branch:
        await callback.answer("Xatolik yuz berdi!", show_alert=True)
        return

    await add_to_cart(user_id, med_id, 1, branch_id=branch_id)
    await callback.answer(f"✅ {med['name']} ({branch['name']}) savatchaga qo'shildi!", show_alert=True)

@router.callback_query(F.data.startswith("sendmap_"))
async def send_branch_map_location(callback: CallbackQuery):
    branch_id = int(callback.data.split("_")[1])
    branch = await get_branch(branch_id)
    if not branch:
        await callback.answer("Filial topilmadi", show_alert=True)
        return

    await callback.answer("📍 Apteka lokatsiyasi yuborilmoqda...")
    await callback.message.answer_location(
        latitude=branch['latitude'],
        longitude=branch['longitude']
    )
    await callback.message.answer(
        f"🏢 **{branch['name']}**\n📍 Manzil: {branch['address']}\n📞 Aloqa: {branch['phone']}\n⏰ Ish vaqti: {branch['work_hours']}",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("addfav_"))
async def handle_add_favorite(callback: CallbackQuery):
    med_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    await add_favorite(user_id, med_id)
    await callback.answer("⭐ Sevimlilar ro'yxatiga qo'shildi!", show_alert=True)
    
    med = await get_medicine(med_id)
    if med:
        db_user = await get_user(user_id)
        db_user_dict = dict(db_user) if db_user else {}
        u_lat = db_user_dict.get('latitude')
        u_lon = db_user_dict.get('longitude')
        branches = await get_medicine_branches_info(med_id, u_lat, u_lon)
        await callback.message.edit_reply_markup(reply_markup=get_medicine_detail_keyboard(med_id, med['category_id'], branches, is_fav=True))

@router.callback_query(F.data.startswith("remfav_"))
async def handle_remove_favorite(callback: CallbackQuery):
    med_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    await remove_favorite(user_id, med_id)
    await callback.answer("Sevimlilardan olib tashlandi")
    
    med = await get_medicine(med_id)
    if med:
        db_user = await get_user(user_id)
        db_user_dict = dict(db_user) if db_user else {}
        u_lat = db_user_dict.get('latitude')
        u_lon = db_user_dict.get('longitude')
        branches = await get_medicine_branches_info(med_id, u_lat, u_lon)
        await callback.message.edit_reply_markup(reply_markup=get_medicine_detail_keyboard(med_id, med['category_id'], branches, is_fav=False))

@router.message(F.text == "🛒 Savat")
async def show_cart(message: Message):
    user_id = message.from_user.id
    cart_items = await get_user_cart(user_id)
    
    if not cart_items:
        await message.answer("🛒 Savatchangiz bo'sh. Katalogdan dori-darmonlarni tanlang.", reply_markup=get_main_keyboard(user_id))
        return

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    text = "🛒 **Sizning Savatchangiz:**\n\n"
    for idx, item in enumerate(cart_items, 1):
        prescription_badge = "⚠️ (Retseptli)" if item['requires_prescription'] else ""
        branch_badge = f"📍 _{item['branch_name']}_" if item.get('branch_name') else ""
        text += f"{idx}. **{item['name']}** {branch_badge} {prescription_badge}\n"
        text += f"   {item['quantity']} шт x {item['price']:,.0f} = **{item['quantity'] * item['price']:,.0f} so'm**\n\n"
    
    text += f"💰 **Jami summasi:** **{total:,.0f} so'm**"
    
    await message.answer(text, reply_markup=get_cart_keyboard(cart_items), parse_mode="Markdown")

@router.callback_query(F.data.startswith("removecart_"))
async def remove_cart_item(callback: CallbackQuery):
    cart_id = int(callback.data.split("_")[1])
    await remove_from_cart(cart_id)
    await callback.answer("Mahsulot savatdan o'chirildi")
    
    cart_items = await get_user_cart(callback.from_user.id)
    if not cart_items:
        await callback.message.edit_text("🛒 Savatchangiz bo'sh.")
    else:
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        text = "🛒 **Sizning Savatchangiz:**\n\n"
        for idx, item in enumerate(cart_items, 1):
            prescription_badge = "⚠️ (Retseptli)" if item['requires_prescription'] else ""
            branch_badge = f"📍 _{item['branch_name']}_" if item.get('branch_name') else ""
            text += f"{idx}. **{item['name']}** {branch_badge} {prescription_badge}\n"
            text += f"   {item['quantity']} шт x {item['price']:,.0f} = **{item['quantity'] * item['price']:,.0f} so'm**\n\n"
        text += f"💰 **Jami summasi:** **{total:,.0f} so'm**"
        await callback.message.edit_text(text, reply_markup=get_cart_keyboard(cart_items), parse_mode="Markdown")

@router.callback_query(F.data == "clear_cart")
async def handle_clear_cart(callback: CallbackQuery):
    await clear_cart(callback.from_user.id)
    await callback.answer("Savat tozalandi")
    await callback.message.edit_text("🛒 Savatchangiz tozalandi.")
