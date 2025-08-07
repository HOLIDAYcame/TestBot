from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_birth_date = State()
    waiting_for_phone = State()


class RequestForm(StatesGroup):
    choosing_type = State()
    attaching_screenshot = State()
    choosing_options = State()
    confirming = State()


class AdminPanel(StatesGroup):
    waiting_for_broadcast_message = State()
    confirming_broadcast = State()
