from datetime import datetime, date
from aiogram.types import FSInputFile
import os


def days_left(expires_at: str) -> int:
    exp = datetime.strptime(expires_at, "%Y-%m-%d").date()
    return (exp - date.today()).days


def urgency_emoji(days: int) -> str:
    if days <= 1:  return "🔴"
    if days <= 3:  return "🟠"
    if days <= 7:  return "🟡"
    return "🟢"


def format_date(d: str) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return d


async def send_expiry_alert(bot, product: dict):
    days = days_left(product["expires_at"])
    emoji = urgency_emoji(days)

    if days < 0:
        time_text = f"⛔️ {abs(days)} kun oldin o'tib ketgan!"
    elif days == 0:
        time_text = "⚠️ Bugun tugaydi!"
    elif days == 1:
        time_text = "⚠️ Ertaga tugaydi!"
    else:
        time_text = f"⏳ {days} kun qoldi"

    text = (
        f"{emoji} <b>MUDDAT YAQINLASHMOQDA</b>\n\n"
        f"🏷  <b>Mahsulot:</b> {product['name']}\n"
        f"📅 <b>Ishlab chiqarilgan:</b> {format_date(product['manufactured_at'])}\n"
        f"⏰ <b>Tugash muddati:</b> {format_date(product['expires_at'])}\n"
        f"🏪 <b>Do'konga kelgan:</b> {format_date(product['arrived_at'])}\n\n"
        f"<b>{time_text}</b>\n\n"
        f"💡 <i>Chegirma qo'yib kanalga e'lon qilasizmi?</i>"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎨 Chegirma qo'yish",
                             callback_data=f"discount:{product['id']}")
    ]])

    if product.get("photo_id"):
        await bot.send_photo(
            chat_id=product["user_id"],
            photo=product["photo_id"],
            caption=text,
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await bot.send_message(
            chat_id=product["user_id"],
            text=text,
            parse_mode="HTML",
            reply_markup=kb
        )
