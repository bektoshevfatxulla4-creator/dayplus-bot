from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def check_expiring(bot):
    """Har kuni ertalab ishga tushadigan tekshirish."""
    from database import get_expiring_products, mark_notified
    from notifications import send_expiry_alert

    products = get_expiring_products()
    logger.info(f"[Scheduler] Tekshirildi: {len(products)} ta mahsulot topildi")

    for product in products:
        try:
            await send_expiry_alert(bot, product)
            mark_notified(product["id"])
            logger.info(f"[Scheduler] Eslatma yuborildi: {product['name']} (id={product['id']})")
        except Exception as e:
            logger.error(f"[Scheduler] Xato: {product['id']} — {e}")


def start_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(
        check_expiring,
        trigger="cron",
        hour=9,
        minute=0,
        args=[bot],
        id="daily_check",
        replace_existing=True
    )
    scheduler.start()
    logger.info("✅ Scheduler ishga tushdi (har kuni 09:00 Toshkent)")
    return scheduler
