from aiogram.fsm.state import State, StatesGroup

class AIConsultantState(StatesGroup):
    waiting_for_query = State()
    waiting_for_prescription_photo = State()

class SearchState(StatesGroup):
    waiting_for_search_query = State()

class OrderState(StatesGroup):
    waiting_for_delivery_type = State()
    waiting_for_address = State()
    waiting_for_phone = State()

class AdminState(StatesGroup):
    waiting_for_med_name = State()
    waiting_for_med_category = State()
    waiting_for_med_desc = State()
    waiting_for_med_active = State()
    waiting_for_med_price = State()
    waiting_for_med_stock = State()
    waiting_for_med_prescription = State()
