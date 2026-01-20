from aiogram.fsm.state import State, StatesGroup

class SalesFlow(StatesGroup):
    qualifying = State()
    collecting_phone = State()
    waiting_manager_message = State()

class ManagerFlow(StatesGroup):
    adding_note = State()
    entering_channel_name = State()
    selecting_widget_type = State()
    entering_greeting = State()
    entering_widget_domain = State()
    entering_widget_greeting = State()
    editing_widget_greeting = State()
    editing_widget_domain = State()
    editing_social_greeting = State()
    editing_social_name = State()
    editing_status_coins = State()

class EventStates(StatesGroup):
    selecting_type = State()
    selecting_date = State()
    selecting_hour = State()
    selecting_minute = State()
    entering_description = State()
    selecting_reminder = State()
    editing_datetime = State()
    editing_description = State()
    selecting_recurring = State()  # For recurring events
