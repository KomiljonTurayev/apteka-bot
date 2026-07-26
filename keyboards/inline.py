from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"📁 {cat['name']}", callback_data=f"cat_{cat['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_medicines_keyboard(medicines: list, prefix: str = "med") -> InlineKeyboardMarkup:
    buttons = []
    for med in medicines:
        prescription_badge = "🔴 (Retseptli)" if med['requires_prescription'] else "🟢"
        buttons.append([
            InlineKeyboardButton(
                text=f"{med['name']} — {med['price']:,.0f} so'm {prescription_badge}",
                callback_data=f"{prefix}_{med['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Kategoriyalarga qaytish", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_medicine_detail_keyboard(medicine_id: int, category_id: int, branches: list, is_fav: bool = False) -> InlineKeyboardMarkup:
    fav_text = "🌟 Sevimlilardan o'chirish" if is_fav else "⭐ Sevimlilarga qo'shish"
    fav_action = f"remfav_{medicine_id}" if is_fav else f"addfav_{medicine_id}"
    
    buttons = []
    
    # Add buttons for each branch with branch-specific price and location button
    for b in branches[:8]:
        b_dict = dict(b) if hasattr(b, 'keys') else b
        dist_str = f" ({b_dict['distance_km']}km)" if b_dict.get('distance_km') else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"🛒 {b_dict['name']}{dist_str} — {b_dict['branch_price']:,.0f} so'm",
                callback_data=f"addcartb_{medicine_id}_{b_dict['id']}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text=f"📍 {b_dict['name']} xaritasi (Lokatsiya)",
                callback_data=f"sendmap_{b_dict['id']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text=fav_text, callback_data=fav_action)])
    buttons.append([InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data=f"cat_{category_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cart_keyboard(cart_items: list) -> InlineKeyboardMarkup:
    buttons = []
    for item in cart_items:
        item_dict = dict(item) if hasattr(item, 'keys') else item
        branch_str = f" ({item_dict['branch_name']})" if item_dict.get('branch_name') else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {item_dict['name']}{branch_str} ({item_dict['quantity']} шт)",
                callback_data=f"removecart_{item_dict['cart_id']}"
            )
        ])
    
    if cart_items:
        buttons.append([InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="checkout")])
        buttons.append([InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_delivery_type_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🚚 Yetkazib berish (Kuryer)", callback_data="delivery_courier")],
        [InlineKeyboardButton(text="🏃 Olib ketish (Samovivoz)", callback_data="delivery_pickup")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Qabul qilindi", callback_data=f"status_{order_id}_Accepted"),
            InlineKeyboardButton(text="🚚 Yo'lda", callback_data=f"status_{order_id}_Delivering")
        ],
        [
            InlineKeyboardButton(text="🎉 Yakunlandi", callback_data=f"status_{order_id}_Completed"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"status_{order_id}_Cancelled")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
