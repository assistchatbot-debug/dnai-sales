"""
Professional Inline Calendar for Telegram Bot
Inspired by aiogram-calendar but custom built
"""

from datetime import datetime, date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import calendar

# Локализация
MONTHS_RU = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
DAYS_RU = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

# Callback prefixes
CB_IGNORE = "cal_ignore"
CB_DAY = "cal_day"
CB_NAV_MONTH = "cal_m"
CB_NAV_YEAR = "cal_y"
CB_HOUR = "cal_h"
CB_HOUR_OK = "cal_hok"
CB_MIN = "cal_min"
CB_MIN_OK = "cal_minok"


class InlineCalendar:
    """Professional inline calendar widget"""
    
    @staticmethod
    def create_month(year: int, month: int) -> InlineKeyboardMarkup:
        """Create calendar for specific month"""
        kb = []
        today = date.today()
        
        # Row 1: Year navigation
        kb.append([
            InlineKeyboardButton(text="◀️", callback_data=f"{CB_NAV_YEAR}:{year-1}:{month}"),
            InlineKeyboardButton(text=str(year), callback_data=CB_IGNORE),
            InlineKeyboardButton(text="▶️", callback_data=f"{CB_NAV_YEAR}:{year+1}:{month}")
        ])
        
        # Row 2: Month navigation  
        prev_m = 12 if month == 1 else month - 1
        prev_y = year - 1 if month == 1 else year
        next_m = 1 if month == 12 else month + 1
        next_y = year + 1 if month == 12 else year
        
        kb.append([
            InlineKeyboardButton(text="◀️", callback_data=f"{CB_NAV_MONTH}:{prev_y}:{prev_m}"),
            InlineKeyboardButton(text=MONTHS_RU[month], callback_data=CB_IGNORE),
            InlineKeyboardButton(text="▶️", callback_data=f"{CB_NAV_MONTH}:{next_y}:{next_m}")
        ])
        
        # Row 3: Days of week
        kb.append([InlineKeyboardButton(text=d, callback_data=CB_IGNORE) for d in DAYS_RU])
        
        # Rows 4-9: Days grid
        month_cal = calendar.monthcalendar(year, month)
        for week in month_cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(text=" ", callback_data=CB_IGNORE))
                else:
                    day_date = date(year, month, day)
                    
                    if day_date < today:
                        # Past - not clickable
                        row.append(InlineKeyboardButton(text="·", callback_data=CB_IGNORE))
                    elif day_date == today:
                        # Today - highlight
                        row.append(InlineKeyboardButton(
                            text=f"•{day}",
                            callback_data=f"{CB_DAY}:{year}-{month:02d}-{day:02d}"
                        ))
                    else:
                        # Future
                        row.append(InlineKeyboardButton(
                            text=str(day),
                            callback_data=f"{CB_DAY}:{year}-{month:02d}-{day:02d}"
                        ))
            kb.append(row)
        
        return InlineKeyboardMarkup(inline_keyboard=kb)
    
    @staticmethod
    def create_hour_picker(hour: int = 10) -> InlineKeyboardMarkup:
        """Create hour picker with scroll"""
        prev_h = 23 if hour == 0 else hour - 1
        next_h = 0 if hour == 23 else hour + 1
        
        kb = [
            [InlineKeyboardButton(text="⏰ Выберите час:", callback_data=CB_IGNORE)],
            [
                InlineKeyboardButton(text="◀️", callback_data=f"{CB_HOUR}:{prev_h}"),
                InlineKeyboardButton(text=f"{hour:02d}", callback_data=CB_IGNORE),
                InlineKeyboardButton(text="▶️", callback_data=f"{CB_HOUR}:{next_h}")
            ],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{CB_HOUR_OK}:{hour}")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=kb)
    
    @staticmethod
    def create_minute_picker(minute: int = 0, step: int = 5) -> InlineKeyboardMarkup:
        """Create minute picker with scroll (step 5 by default)"""
        prev_min = (minute - step) % 60
        next_min = (minute + step) % 60
        
        kb = [
            [InlineKeyboardButton(text="⏰ Выберите минуты:", callback_data=CB_IGNORE)],
            [
                InlineKeyboardButton(text="◀️", callback_data=f"{CB_MIN}:{prev_min}"),
                InlineKeyboardButton(text=f"{minute:02d}", callback_data=CB_IGNORE),
                InlineKeyboardButton(text="▶️", callback_data=f"{CB_MIN}:{next_min}")
            ],
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"{CB_MIN_OK}:{minute}")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=kb)


# Shortcut functions
def get_calendar(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """Get calendar for current or specified month"""
    now = datetime.now()
    return InlineCalendar.create_month(year or now.year, month or now.month)

def get_hour_picker(hour: int = 10) -> InlineKeyboardMarkup:
    return InlineCalendar.create_hour_picker(hour)

def get_minute_picker(minute: int = 0) -> InlineKeyboardMarkup:
    return InlineCalendar.create_minute_picker(minute)
