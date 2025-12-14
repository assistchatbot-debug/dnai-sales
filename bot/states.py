from aiogram.fsm.state import State, StatesGroup

class SalesFlow(StatesGroup):
    qualifying = State()
    collecting_phone = State()
    waiting_manager_message = State()  # NEW: waiting for message to manager
