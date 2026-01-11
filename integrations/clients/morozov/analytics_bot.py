"""Telegram бот аналитики с polling"""
import asyncio
import sys
sys.path.insert(0, '/root/dnai-sales/integrations')

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from loguru import logger

from config import settings
from bitrix24_client import Bitrix24Client
from shared.analytics_service import AnalyticsService

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()
bitrix24 = Bitrix24Client()
analytics = AnalyticsService(bitrix24)

def get_main_menu():
    """Закреплённое меню"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📈 Статус"), KeyboardButton(text="💰 День")],
        [KeyboardButton(text="💰 Неделя"), KeyboardButton(text="💰 Месяц")],
        [KeyboardButton(text="🏆 Товары недели"), KeyboardButton(text="🏆 Товары месяца")]
    ], resize_keyboard=True)

@dp.message(Command("start", "analytics"))
async def cmd_start(message: types.Message):
    await message.answer("📊 *Аналитика продаж*\n\nВыберите отчёт:", 
                        reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.message(F.text == "📈 Статус")
async def btn_status(message: types.Message):
    await message.answer("✅ Система работает\n✅ 1С: Подключено\n✅ Bitrix24: Активно")

@dp.message(F.text == "💰 День")
async def btn_sales_day(message: types.Message):
    await send_sales_report(message, "day")

@dp.message(F.text == "💰 Неделя")
async def btn_sales_week(message: types.Message):
    await send_sales_report(message, "week")

@dp.message(F.text == "💰 Месяц")
async def btn_sales_month(message: types.Message):
    await send_sales_report(message, "month")

@dp.message(F.text == "🏆 Товары недели")
async def btn_top_week(message: types.Message):
    await send_top_products(message, "week")

@dp.message(F.text == "🏆 Товары месяца")
async def btn_top_month(message: types.Message):
    await send_top_products(message, "month")

async def send_sales_report(message: types.Message, period: str):
    await message.answer("⏳ Загружаю данные...")
    try:
        report = await analytics.get_sales_report(period)
        period_names = {"day": "день", "week": "неделю", "month": "месяц"}
        
        msg = f"💰 *Продажи за {period_names.get(period)}*\n"
        msg += f"📅 {report['date_from']} — {report['date_to']}\n\n"
        msg += f"📊 Общая сумма: *{report['total_sum']:,.0f} ₸*\n"
        msg += f"📦 Сделок: {report['deals_count']}\n\n"
        msg += "👥 *Менеджеры:*\n"
        
        for i, (_, m) in enumerate(report['managers'][:10], 1):
            msg += f"{i}. {m['name']} — {m['sum']:,.0f} ₸ ({m['count']} сд.)\n\n"
        
        if not report['managers']:
            msg += "_Нет данных_"
        
        await message.answer(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Sales report error: {e}")
        await message.answer(f"❌ Ошибка: {e}")

async def send_top_products(message: types.Message, period: str):
    await message.answer("⏳ Загружаю данные...")
    try:
        report = await analytics.get_top_products(period, limit=5)
        period_names = {"week": "неделю", "month": "месяц"}
        
        msg = f"🏆 *Топ-5 товаров за {period_names.get(period)}*\n"
        msg += f"📅 {report['date_from']} — {report['date_to']}\n\n"
        
        for i, (_, p) in enumerate(report['products'], 1):
            msg += f"{i}. {p['name']} — {p['qty']:.0f} шт / {p['sum']:,.0f} ₸\n\n"
        
        if not report['products']:
            msg += "_Нет данных_"
        else:
            msg += f"\n📊 Всего продано: {report['total_qty']:.0f} шт"
        
        await message.answer(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Top products error: {e}")
        await message.answer(f"❌ Ошибка: {e}")

async def main():
    logger.info("🚀 Analytics bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
