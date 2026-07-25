from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from states.states import OrderState
from database.db_manager import get_user_cart, create_order, get_order_items, add_or_update_user
from keyboards.inline import get_delivery_type_keyboard, get_admin_order_keyboard
from keyboards.reply import get_location_keyboard, get_contact_keyboard, get_main_keyboard
from config import ADMIN_IDS

router = Router()

@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    cart_items = await get_user_cart(callback.from_user.id)
    if not cart_items:
        await callback.answer("Savatchangiz bo'sh!", show_alert=True)
        return

    await state.set_state(OrderState.waiting_for_delivery_type)
    await callback.message.edit_text("🚚 **Buyurtma berish turini tanlang:**", reply_markup=get_delivery_type_keyboard(), parse_mode="Markdown")

@router.callback_query(OrderState.waiting_for_delivery_type, F.data.in_(["delivery_courier", "delivery_pickup"]))
async def select_delivery_type(callback: CallbackQuery, state: FSMContext):
    delivery_type = "Yetkazib berish (Kuryer)" if callback.data == "delivery_courier" else "Olib ketish (Samovivoz)"
    await state.update_data(delivery_type=delivery_type)
    
    if callback.data == "delivery_courier":
        await state.set_state(OrderState.waiting_for_address)
        await callback.message.delete()
        await callback.message.answer("📍 Iltimos, yetkazib berish manzilini yozing yoki pastdagi **'📍 Lokatsiyani yuborish'** tugmasini bosing:", reply_markup=get_location_keyboard(), parse_mode="Markdown")
    else:
        await state.update_data(address_or_location="Markaziy Apteka 24/7 (Samovivoz)")
        await state.set_state(OrderState.waiting_for_phone)
        await callback.message.delete()
        await callback.message.answer("📱 Aloqa uchun telefon raqamingizni yozing yoki **'📱 Telefon raqamni yuborish'** tugmasini bosing:", reply_markup=get_contact_keyboard(), parse_mode="Markdown")

@router.message(OrderState.waiting_for_address, F.location | F.text)
async def process_address(message: Message, state: FSMContext):
    if message.location:
        loc = f"Geo-location: {message.location.latitude}, {message.location.longitude}"
        await state.update_data(address_or_location=loc)
    elif message.text and message.text != "❌ Bekor qilish":
        await state.update_data(address_or_location=message.text)
    else:
        return

    await state.set_state(OrderState.waiting_for_phone)
    await message.answer("📱 Aloqa uchun telefon raqamingizni yozing yoki **'📱 Telefon raqamni yuborish'** tugmasini bosing:", reply_markup=get_contact_keyboard(), parse_mode="Markdown")

@router.message(OrderState.waiting_for_phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    phone = message.contact.phone_number if message.contact else message.text
    if phone == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=get_main_keyboard(message.from_user.id))
        return

    data = await state.get_data()
    user_id = message.from_user.id
    
    cart_items = await get_user_cart(user_id)
    if not cart_items:
        await message.answer("Savatchangiz bo'shab qolgan.", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        return

    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
    
    order_id = await create_order(
        user_id=user_id,
        total_amount=total_amount,
        delivery_type=data['delivery_type'],
        address_or_location=data['address_or_location'],
        phone=phone
    )
    
    await add_or_update_user(user_id, message.from_user.full_name, phone)
    await state.clear()

    # User confirmation message
    await message.answer(
        f"🎉 **Buyurtmangiz qabul qilindi!**\n\n"
        f"🆔 Buyurtma raqami: **#{order_id}**\n"
        f"💰 Jami summa: **{total_amount:,.0f} so'm**\n"
        f"🚚 Tur: {data['delivery_type']}\n"
        f"📱 Telefon: {phone}\n\n"
        f"Operatorlarimiz tez orada siz bilan bog'lanishadi. Rahmat!",
        reply_markup=get_main_keyboard(user_id),
        parse_mode="Markdown"
    )

    # Notify Admins
    order_items = await get_order_items(order_id)
    admin_text = f"🚨 **YANGI BUYURTMA #{order_id}!**\n\n"
    admin_text += f"👤 Mijoz: {message.from_user.full_name} (ID: `{user_id}`)\n"
    admin_text += f"📱 Tel: `{phone}`\n"
    admin_text += f"🚚 Tur: {data['delivery_type']}\n"
    admin_text += f"📍 Manzil: {data['address_or_location']}\n\n"
    admin_text += "📦 **Tarkibi:**\n"
    for item in order_items:
        admin_text += f"- {item['name']} x {item['quantity']} шт ({item['price_per_unit']:,.0f} so'm)\n"
    admin_text += f"\n💰 **Jami:** {total_amount:,.0f} so'm"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=get_admin_order_keyboard(order_id), parse_mode="Markdown")
        except Exception as e:
            pass
