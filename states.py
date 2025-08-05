from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_birth_date = State()
    waiting_for_phone = State()