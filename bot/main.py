import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:8000')

async def get_companies_with_bots():
    """Get all companies that have bot tokens configured"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{API_BASE_URL}/sales/companies/all',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    # Filter only companies with bot_token
                    return [c for c in companies if c.get('bot_token')]
                else:
                    logging.error(f"Failed to get companies: {resp.status}")
                    return []
    except Exception as e:
        logging.error(f"Error getting companies: {e}")
        return []

async def main():
    logging.info("🚀 Starting BizDNAi Multi-Tenant Bot System...")
    
    # Load companies from database
    companies = await get_companies_with_bots()
    
    if not companies:
        logging.error("❌ No companies with bot tokens found!")
        logging.info("💡 Add bot tokens via SuperAdmin bot")
        return
    
    logging.info(f"📋 Found {len(companies)} companies with bots")
    
    # Create Bot instances for each company
    bots = []
    for company in companies:
        try:
            bot = Bot(token=company['bot_token'])
            
            # Attach company metadata to bot instance
            bot.company_id = company['id']
            bot.company_name = company.get('name', f"Company {company['id']}")
            bot.manager_chat_id = company.get('manager_chat_id')
            
            bots.append(bot)
            logging.info(
                f"🤖 Bot #{company['id']}: {company['name']} "
                f"(Manager: {company.get('manager_chat_id', 'not set')})"
            )
        except Exception as e:
            logging.error(f"❌ Failed to create bot for company {company['id']}: {e}")
    
    if not bots:
        logging.error("❌ No valid bots created!")
        return
    
    # Create single dispatcher for all bots
    dp = Dispatcher()
    dp.include_router(router)
    
    logging.info(f"✅ Starting polling for {len(bots)} bot(s)...")
    
    try:
        # Start polling all bots simultaneously
        await dp.start_polling(*bots, drop_pending_updates=True)
    except Exception as e:
        logging.error(f"❌ Polling error: {e}")
    finally:
        # Cleanup
        for bot in bots:
            await bot.session.close()
        logging.info("Bot sessions closed")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
