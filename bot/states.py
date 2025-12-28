from aiogram.fsm.state import State, StatesGroup

class SalesFlow(StatesGroup):
    qualifying = State()
    collecting_phone = State()
    waiting_manager_message = State()


class ManagerFlow(StatesGroup):
    entering_channel_name = State()
    entering_greeting = State()
    entering_widget_domain = State()
    entering_widget_greeting = State()
    editing_widget_greeting = State()
    editing_widget_domain = State()
