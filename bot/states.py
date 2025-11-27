from aiogram.fsm.state import State, StatesGroup
class SalesFlow(StatesGroup):
    waiting_for_start = State()
    qualifying = State()
    processing_voice = State()
    viewing_recommendations = State()
    handoff_to_manager = State()
