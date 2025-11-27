import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set. Exiting.")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    # Graceful shutdown
    async def shutdown(dispatcher: Dispatcher, bot: Bot):
        await bot.session.close()
        await dispatcher.storage.close()
        logging.info("Bot stopped. Data saved.")

    dp.shutdown.register(shutdown)

    try:
        print("🤖 Sales Agent Bot is running...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot polling error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
