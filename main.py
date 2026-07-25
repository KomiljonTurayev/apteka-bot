import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.db_manager import init_db

from handlers import user, ai_consultant, catalog, order, admin

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN sozlanmagan! Iltimos, .env faylida BOT_TOKEN ni o'rnating.")
        print("\nXATO: BOT_TOKEN topilmadi!")
        print("Iltimos, .env faylini oching va Telegram BotFather'dan olingan tokeningizni joylang.\n")
        return

    # Initialize SQLite DB
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Include routers in order
    dp.include_router(user.router)
    dp.include_router(ai_consultant.router)
    dp.include_router(catalog.router)
    dp.include_router(order.router)
    dp.include_router(admin.router)

    logger.info("Apteka AI Hodim Bot ishga tushmoqda...")
    
    # Skip old pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
