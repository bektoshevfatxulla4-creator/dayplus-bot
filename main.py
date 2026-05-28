import asyncio async def keep_alive():
    """Render uyquga ketmasligi uchun har 10 daqiqada ping"""
    import aiohttp
    url = os.getenv("RENDER_EXTERNAL_URL", "")
    while True:
        await asyncio.sleep(600)
        if url:
            try:
                async with aiohttp.ClientSession() as s:
                    await s.get(url)
            except Exception:
                passsssss
import logging
import os
from datetime import datetime, date, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.types import FSInputFile
from dotenv import load_dotenv

from database import (
    init_db, add_product, get_products, search_products,
    get_product, update_product, delete_product, add_discount,
    get_expiring_today_tomorrow, get_weekly_stats, get_loss_stats,
    save_template, get_templates, get_template, delete_template,
    get_shop_name, set_shop_name, mark_notified
)
from image_gen import generate_discount_image
from scheduler import start_scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

CATEGORIES = ["🥛 Sut mahsulotlari", "🥩 Go'sht", "🍞 Non va xamirli",
              "🥤 Ichimliklar", "🥫 Konservalar", "🧁 Shirinliklar", "🛒 Boshqa"]


# ──────────────────────────────────────────
# FSM States
# ──────────────────────────────────────────

class AddProduct(StatesGroup):
    photo        = State()
    name         = State()
    category     = State()
    manufactured = State()
    expires      = State()
    arrived      = State()
    remind_days  = State()
    quantity     = State()
    batch_number = State()


class QuickAdd(StatesGroup):
    name        = State()
    category    = State()
    expires     = State()
    remind_days = State()


class TemplateAdd(StatesGroup):
    expires     = State()
    remind_days = State()
    quantity    = State()


class EditProduct(StatesGroup):
    field  = State()
    value  = State()


class Discount(StatesGroup):
    old_price = State()
    new_price = State()
    reason    = State()


class SearchState(StatesGroup):
    query = State()


class ShopSetting(StatesGroup):
    name = State()


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

def parse_date(text: str):
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Qo'shish"),
             KeyboardButton(text="⚡ Tezkor qo'shish")],
            [KeyboardButton(text="📦 Ro'yxat"),
             KeyboardButton(text="🔍 Qidirish")],
            [KeyboardButton(text="📊 Hisobot"),
             KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True
    )


def category_keyboard():
    buttons = [[KeyboardButton(text=c)] for c in CATEGORIES]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def products_inline(products):
    from notifications import days_left, urgency_emoji
    buttons = []
    for p in products:
        days = days_left(p["expires_at"])
        emoji = urgency_emoji(days)
        label = f"{emoji} {p['name']} ({days} kun)"
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"product:{p['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_inline(product_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash",
                              callback_data=f"edit:{product_id}"),
         InlineKeyboardButton(text="🎨 Chegirma rasmi",
                              callback_data=f"discount:{product_id}")],
        [InlineKeyboardButton(text="🗑 O'chirish",
                              callback_data=f"delete:{product_id}")],
        [InlineKeyboardButton(text="◀️ Orqaga",
                              callback_data="list")]
    ])


# ──────────────────────────────────────────
# /start
# ──────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "👋 <b>Day+</b> ga xush kelibsiz!\n\n"
        "Mahsulotlarning muddat sanasini kuzataman va vaqtida eslataman.\n\n"
        "⚡ <b>Tezkor qo'shish</b> — 3 ta savol (tez)\n"
        "➕ <b>Qo'shish</b> — to'liq ma'lumot bilan",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ──────────────────────────────────────────
# TO'LIQ QO'SHISH
# ──────────────────────────────────────────

@dp.message(F.text == "➕ Qo'shish")
async def start_add(msg: Message, state: FSMContext):
    await state.set_state(AddProduct.photo)
    await msg.answer(
        "📸 Mahsulot rasmini yuboring yoki /skip bosing",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(AddProduct.photo, F.photo)
async def got_photo(msg: Message, state: FSMContext):
    await state.update_data(photo_id=msg.photo[-1].file_id)
    await state.set_state(AddProduct.name)
    await msg.answer("✏️ Mahsulot nomini kiriting:")


@dp.message(AddProduct.photo, Command("skip"))
@dp.message(AddProduct.photo, F.text)
async def skip_photo(msg: Message, state: FSMContext):
    await state.update_data(photo_id=None)
    await state.set_state(AddProduct.name)
    await msg.answer("✏️ Mahsulot nomini kiriting:")


@dp.message(AddProduct.name)
async def got_name_full(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(AddProduct.category)
    await msg.answer("📋 Kategoriyani tanlang:", reply_markup=category_keyboard())


@dp.message(AddProduct.category)
async def got_category_full(msg: Message, state: FSMContext):
    await state.update_data(category=msg.text.strip())
    await state.set_state(AddProduct.manufactured)
    await msg.answer("📅 Ishlab chiqarilgan sana?\n<i>Format: 15.05.2025</i>",
                     parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@dp.message(AddProduct.manufactured)
async def got_manufactured(msg: Message, state: FSMContext):
    d = parse_date(msg.text)
    if not d:
        return await msg.answer("❌ Format: <b>15.05.2025</b>", parse_mode="HTML")
    await state.update_data(manufactured_at=d)
    await state.set_state(AddProduct.expires)
    await msg.answer("⏰ Tugash muddati?\n<i>Format: 15.06.2025</i>", parse_mode="HTML")


@dp.message(AddProduct.expires)
async def got_expires_full(msg: Message, state: FSMContext):
    d = parse_date(msg.text)
    if not d:
        return await msg.answer("❌ Format: <b>15.06.2025</b>", parse_mode="HTML")
    data = await state.get_data()
    if d <= data.get("manufactured_at", ""):
        return await msg.answer("❌ Tugash sanasi ishlab chiqarilgan sanadan keyin bo'lishi kerak!")
    await state.update_data(expires_at=d)
    await state.set_state(AddProduct.arrived)
    await msg.answer("🏪 Do'konga kelgan sana?\n<i>Format: 20.05.2025</i>", parse_mode="HTML")


@dp.message(AddProduct.arrived)
async def got_arrived(msg: Message, state: FSMContext):
    d = parse_date(msg.text)
    if not d:
        return await msg.answer("❌ Format: <b>20.05.2025</b>", parse_mode="HTML")
    await state.update_data(arrived_at=d)
    await state.set_state(AddProduct.remind_days)
    await msg.answer("🔔 Necha kun oldin eslatay?\n<i>Masalan: 3</i>", parse_mode="HTML")


@dp.message(AddProduct.remind_days)
async def got_remind_full(msg: Message, state: FSMContext):
    try:
        days = int(msg.text.strip())
        if not 1 <= days <= 30:
            raise ValueError
    except ValueError:
        return await msg.answer("❌ 1 dan 30 gacha son kiriting.")
    await state.update_data(remind_days=days)
    await state.set_state(AddProduct.quantity)
    await msg.answer("📦 Miqdori (dona)?\n<i>Masalan: 10 yoki /skip</i>", parse_mode="HTML")


@dp.message(AddProduct.quantity)
async def got_quantity(msg: Message, state: FSMContext):
    if msg.text == "/skip":
        await state.update_data(quantity=1)
    else:
        try:
            qty = int(msg.text.strip())
        except ValueError:
            return await msg.answer("❌ Faqat raqam kiriting.")
        await state.update_data(quantity=qty)
    await state.set_state(AddProduct.batch_number)
    await msg.answer("🔢 Partiya raqami?\n<i>Masalan: P-2025-001 yoki /skip</i>", parse_mode="HTML")


@dp.message(AddProduct.batch_number)
async def got_batch(msg: Message, state: FSMContext):
    batch = None if msg.text == "/skip" else msg.text.strip()
    await state.update_data(batch_number=batch)
    data = await state.get_data()

    product_id = add_product(
        user_id=msg.from_user.id,
        name=data["name"],
        category=data.get("category", "Boshqa"),
        photo_id=data.get("photo_id"),
        manufactured_at=data["manufactured_at"],
        expires_at=data["expires_at"],
        arrived_at=data["arrived_at"],
        remind_days=data["remind_days"],
        quantity=data.get("quantity", 1),
        batch_number=batch
    )

    # Shablon sifatida saqlash
    save_template(msg.from_user.id, data["name"],
                  data.get("category", "Boshqa"), data["remind_days"])

    await state.clear()
    await msg.answer(
        f"✅ <b>{data['name']}</b> saqlandi!\n"
        f"📋 Kategoriya: {data.get('category', 'Boshqa')}\n"
        f"🔔 {data['remind_days']} kun oldin eslataman.\n"
        f"⭐ Shablon sifatida ham saqlandi!",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ──────────────────────────────────────────
# TEZKOR QO'SHISH
# ──────────────────────────────────────────

@dp.message(F.text == "⚡ Tezkor qo'shish")
async def quick_add_start(msg: Message, state: FSMContext):
    templates = get_templates(msg.from_user.id)
    if templates:
        buttons = [[InlineKeyboardButton(
            text=f"⭐ {t['name']}",
            callback_data=f"use_template:{t['id']}"
        )] for t in templates[:8]]
        buttons.append([InlineKeyboardButton(
            text="➕ Yangi mahsulot", callback_data="quick_new"
        )])
        await msg.answer(
            "⚡ <b>Tezkor qo'shish</b>\n\nShablon tanlang yoki yangi kiriting:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await state.set_state(QuickAdd.name)
        await msg.answer("✏️ Mahsulot nomini kiriting:",
                         reply_markup=ReplyKeyboardRemove())


@dp.callback_query(F.data == "quick_new")
async def quick_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(QuickAdd.name)
    await cb.message.answer("✏️ Mahsulot nomini kiriting:",
                             reply_markup=ReplyKeyboardRemove())
    await cb.answer()


@dp.callback_query(F.data.startswith("use_template:"))
async def use_template(cb: CallbackQuery, state: FSMContext):
    tid = int(cb.data.split(":")[1])
    t = get_template(tid)
    if not t:
        return await cb.answer("Shablon topilmadi.")
    await state.update_data(
        name=t["name"], category=t["category"], remind_days=t["remind_days"]
    )
    await state.set_state(TemplateAdd.expires)
    await cb.message.answer(
        f"⭐ <b>{t['name']}</b> shabloni tanlandi!\n\n"
        f"⏰ Tugash muddatini kiriting:\n<i>Format: 15.06.2025</i>",
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
    )
    await cb.answer()


@dp.message(TemplateAdd.expires)
async def template_expires(msg: Message, state: FSMContext):
    d = parse_date(msg.text)
    if not d:
        return await msg.answer("❌ Format: <b>15.06.2025</b>", parse_mode="HTML")
    await state.update_data(expires_at=d)
    await state.set_state(TemplateAdd.quantity)
    await msg.answer("📦 Miqdori (dona)?\n<i>Masalan: 10 yoki /skip</i>", parse_mode="HTML")


@dp.message(TemplateAdd.quantity)
async def template_quantity(msg: Message, state: FSMContext):
    qty = 1
    if msg.text != "/skip":
        try:
            qty = int(msg.text.strip())
        except ValueError:
            return await msg.answer("❌ Faqat raqam kiriting.")
    data = await state.get_data()
    today = date.today().strftime("%Y-%m-%d")
    add_product(
        user_id=msg.from_user.id,
        name=data["name"],
        category=data["category"],
        photo_id=None,
        manufactured_at=today,
        expires_at=data["expires_at"],
        arrived_at=today,
        remind_days=data["remind_days"],
        quantity=qty
    )
    await state.clear()
    await msg.answer(
        f"✅ <b>{data['name']}</b> tezkor saqlandi!\n"
        f"⏰ Tugash: {data['expires_at']}\n"
        f"📦 Miqdor: {qty} dona",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


@dp.message(QuickAdd.name)
async def quick_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(QuickAdd.category)
    await msg.answer("📋 Kategoriyani tanlang:", reply_markup=category_keyboard())


@dp.message(QuickAdd.category)
async def quick_category(msg: Message, state: FSMContext):
    await state.update_data(category=msg.text.strip())
    await state.set_state(QuickAdd.expires)
    await msg.answer("⏰ Tugash muddati?\n<i>Format: 15.06.2025</i>",
                     parse_mode="HTML", reply_markup=ReplyKeyboardRemove())


@dp.message(QuickAdd.expires)
async def quick_expires(msg: Message, state: FSMContext):
    d = parse_date(msg.text)
    if not d:
        return await msg.answer("❌ Format: <b>15.06.2025</b>", parse_mode="HTML")
    await state.update_data(expires_at=d)
    await state.set_state(QuickAdd.remind_days)
    await msg.answer("🔔 Necha kun oldin eslatay?\n<i>Masalan: 3</i>", parse_mode="HTML")


@dp.message(QuickAdd.remind_days)
async def quick_remind(msg: Message, state: FSMContext):
    try:
        days = int(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ Faqat raqam kiriting.")
    data = await state.get_data()
    today = date.today().strftime("%Y-%m-%d")
    add_product(
        user_id=msg.from_user.id,
        name=data["name"],
        category=data["category"],
        photo_id=None,
        manufactured_at=today,
        expires_at=data["expires_at"],
        arrived_at=today,
        remind_days=days
    )
    save_template(msg.from_user.id, data["name"], data["category"], days)
    await state.clear()
    await msg.answer(
        f"✅ <b>{data['name']}</b> saqlandi!\n⭐ Shablon sifatida ham saqlandi!",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ──────────────────────────────────────────
# RO'YXAT
# ──────────────────────────────────────────

@dp.message(F.text == "📦 Ro'yxat")
async def list_products(msg: Message):
    products = get_products(msg.from_user.id)
    if not products:
        return await msg.answer(
            "📭 Hali mahsulot qo'shilmagan.",
            reply_markup=main_keyboard()
        )

    # Kategoriya filtri
    cats = list(set(p["category"] for p in products))
    buttons = [[InlineKeyboardButton(text="📦 Hammasi",
                                     callback_data="filter:all")]]
    for c in cats:
        buttons.append([InlineKeyboardButton(
            text=c, callback_data=f"filter:{c}"
        )])
    await msg.answer(
        f"📦 Jami <b>{len(products)}</b> ta mahsulot.\nKategoriya tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("filter:"))
async def filter_products(cb: CallbackQuery):
    cat = cb.data.split(":", 1)[1]
    if cat == "all":
        products = get_products(cb.from_user.id)
    else:
        products = get_products(cb.from_user.id, category=cat)
    if not products:
        return await cb.message.edit_text("📭 Bu kategoriyada mahsulot yo'q.")
    await cb.message.edit_text(
        f"📦 <b>{len(products)}</b> ta mahsulot:",
        parse_mode="HTML",
        reply_markup=products_inline(products)
    )


@dp.callback_query(F.data == "list")
async def cb_list(cb: CallbackQuery):
    products = get_products(cb.from_user.id)
    if not products:
        return await cb.message.edit_text("📭 Mahsulotlar yo'q.")
    await cb.message.edit_text(
        f"📦 <b>{len(products)}</b> ta mahsulot:",
        parse_mode="HTML",
        reply_markup=products_inline(products)
    )


@dp.callback_query(F.data.startswith("product:"))
async def cb_product(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = get_product(pid)
    if not p:
        return await cb.answer("Topilmadi.")
    from notifications import days_left, urgency_emoji, format_date
    days = days_left(p["expires_at"])
    emoji = urgency_emoji(days)
    batch = f"\n🔢 Partiya: {p['batch_number']}" if p.get("batch_number") else ""
    text = (
        f"{emoji} <b>{p['name']}</b>\n\n"
        f"📋 Kategoriya: {p['category']}\n"
        f"📅 Ishlab chiqarilgan: {format_date(p['manufactured_at'])}\n"
        f"⏰ Tugash muddati: {format_date(p['expires_at'])}\n"
        f"🏪 Do'konga kelgan: {format_date(p['arrived_at'])}\n"
        f"📦 Miqdor: {p.get('quantity', 1)} dona\n"
        f"🔔 Eslatma: {p['remind_days']} kun oldin{batch}\n\n"
        f"<b>⏳ Qolgan: {days} kun</b>"
    )
    await cb.message.edit_text(text, parse_mode="HTML",
                                reply_markup=product_detail_inline(pid))


# ──────────────────────────────────────────
# QIDIRISH
# ──────────────────────────────────────────

@dp.message(F.text == "🔍 Qidirish")
async def search_start(msg: Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await msg.answer("🔍 Mahsulot nomini kiriting:",
                     reply_markup=ReplyKeyboardRemove())


@dp.message(SearchState.query)
async def search_execute(msg: Message, state: FSMContext):
    await state.clear()
    results = search_products(msg.from_user.id, msg.text.strip())
    if not results:
        return await msg.answer("❌ Topilmadi.", reply_markup=main_keyboard())
    await msg.answer(
        f"🔍 <b>{len(results)}</b> ta topildi:",
        parse_mode="HTML",
        reply_markup=products_inline(results)
    )
    await msg.answer(".", reply_markup=main_keyboard())


# ──────────────────────────────────────────
# TAHRIRLASH
# ──────────────────────────────────────────

@dp.callback_query(F.data.startswith("edit:"))
async def edit_start(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split(":")[1])
    await state.update_data(edit_product_id=pid)
    await state.set_state(EditProduct.field)
    buttons = [
        [InlineKeyboardButton(text="📝 Nom", callback_data="editfield:name"),
         InlineKeyboardButton(text="📋 Kategoriya", callback_data="editfield:category")],
        [InlineKeyboardButton(text="⏰ Tugash sanasi", callback_data="editfield:expires_at"),
         InlineKeyboardButton(text="🔔 Eslatma kuni", callback_data="editfield:remind_days")],
        [InlineKeyboardButton(text="📦 Miqdor", callback_data="editfield:quantity"),
         InlineKeyboardButton(text="🔢 Partiya", callback_data="editfield:batch_number")],
    ]
    await cb.message.edit_text(
        "✏️ Qaysi maydonni tahrirlaysiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("editfield:"))
async def edit_field(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":")[1]
    await state.update_data(edit_field=field)
    await state.set_state(EditProduct.value)
    hints = {
        "name": "Yangi nomni kiriting:",
        "category": "Yangi kategoriyani kiriting:",
        "expires_at": "Yangi tugash sanasi:\n<i>Format: 15.06.2025</i>",
        "remind_days": "Necha kun oldin eslatay? (1-30):",
        "quantity": "Yangi miqdori (dona):",
        "batch_number": "Yangi partiya raqami:"
    }
    await cb.message.answer(hints.get(field, "Yangi qiymatni kiriting:"),
                             parse_mode="HTML")
    await cb.answer()


@dp.message(EditProduct.value)
async def edit_value(msg: Message, state: FSMContext):
    data = await state.get_data()
    field = data["edit_field"]
    pid = data["edit_product_id"]
    value = msg.text.strip()

    if field == "expires_at":
        value = parse_date(value)
        if not value:
            return await msg.answer("❌ Format: <b>15.06.2025</b>", parse_mode="HTML")
    elif field == "remind_days":
        try:
            value = int(value)
        except ValueError:
            return await msg.answer("❌ Faqat raqam kiriting.")
    elif field == "quantity":
        try:
            value = int(value)
        except ValueError:
            return await msg.answer("❌ Faqat raqam kiriting.")

    update_product(pid, **{field: value})
    await state.clear()
    await msg.answer("✅ Yangilandi!", reply_markup=main_keyboard())


# ──────────────────────────────────────────
# O'CHIRISH
# ──────────────────────────────────────────

@dp.callback_query(F.data.startswith("delete:"))
async def cb_delete(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    delete_product(pid, cb.from_user.id)
    await cb.message.edit_text("🗑 Mahsulot o'chirildi.")
    await cb.answer("O'chirildi!")


# ──────────────────────────────────────────
# HISOBOT
# ──────────────────────────────────────────

@dp.message(F.text == "📊 Hisobot")
async def report_menu(msg: Message):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Bugun/ertaga tugaydigan",
                              callback_data="report:today")],
        [InlineKeyboardButton(text="📈 Haftalik hisobot",
                              callback_data="report:weekly")],
        [InlineKeyboardButton(text="💸 Zarar hisobi",
                              callback_data="report:loss")],
    ])
    await msg.answer("📊 Qaysi hisobotni ko'rmoqchisiz?",
                     reply_markup=buttons)


@dp.callback_query(F.data == "report:today")
async def report_today(cb: CallbackQuery):
    products = get_expiring_today_tomorrow(cb.from_user.id)
    if not products:
        return await cb.message.edit_text("✅ Bugun va ertaga tugaydigan mahsulot yo'q!")
    from notifications import days_left, urgency_emoji, format_date
    text = "📊 <b>Bugun/ertaga tugaydigan:</b>\n\n"
    for p in products:
        days = days_left(p["expires_at"])
        emoji = urgency_emoji(days)
        text += f"{emoji} {p['name']} — {format_date(p['expires_at'])} ({days} kun)\n"
    await cb.message.edit_text(text, parse_mode="HTML")


@dp.callback_query(F.data == "report:weekly")
async def report_weekly(cb: CallbackQuery):
    stats = get_weekly_stats(cb.from_user.id)
    text = (
        "📈 <b>Haftalik hisobot:</b>\n\n"
        f"📦 Jami mahsulotlar: <b>{stats['total']}</b> ta\n"
        f"⏳ Keyingi 7 kunda tugaydi: <b>{stats['expiring']}</b> ta\n"
        f"❌ Muddati o'tgan: <b>{stats['expired']}</b> ta\n"
    )
    await cb.message.edit_text(text, parse_mode="HTML")


@dp.callback_query(F.data == "report:loss")
async def report_loss(cb: CallbackQuery):
    rows = get_loss_stats(cb.from_user.id)
    if not rows:
        return await cb.message.edit_text("✅ Muddati o'tgan mahsulot yo'q!")
    text = "💸 <b>Muddati o'tgan mahsulotlar:</b>\n\n"
    for r in rows:
        text += f"❌ {r['name']}"
        if r.get("quantity"):
            text += f" x{r['quantity']}"
        if r.get("old_price"):
            loss = (r["old_price"] - (r.get("new_price") or 0)) * (r.get("quantity") or 1)
            text += f" — zarar: ~{loss:,} so'm".replace(",", " ")
        text += "\n"
    await cb.message.edit_text(text, parse_mode="HTML")


# ──────────────────────────────────────────
# SOZLAMALAR
# ──────────────────────────────────────────

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(msg: Message):
    shop = get_shop_name(msg.from_user.id)
    templates = get_templates(msg.from_user.id)
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏪 Do'kon nomi: {shop}",
                              callback_data="set:shopname")],
        [InlineKeyboardButton(text=f"⭐ Shablonlar ({len(templates)} ta)",
                              callback_data="set:templates")],
    ])
    await msg.answer("⚙️ Sozlamalar:", reply_markup=buttons)


@dp.callback_query(F.data == "set:shopname")
async def set_shopname_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ShopSetting.name)
    await cb.message.answer("🏪 Do'kon nomini kiriting:")
    await cb.answer()


@dp.message(ShopSetting.name)
async def set_shopname_done(msg: Message, state: FSMContext):
    set_shop_name(msg.from_user.id, msg.text.strip())
    await state.clear()
    await msg.answer(
        f"✅ Do'kon nomi <b>{msg.text.strip()}</b> sifatida saqlandi!\n"
        f"Chegirma rasmlarida shu nom chiqadi.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


@dp.callback_query(F.data == "set:templates")
async def show_templates(cb: CallbackQuery):
    templates = get_templates(cb.from_user.id)
    if not templates:
        return await cb.message.edit_text("⭐ Hali shablon yo'q. Mahsulot qo'shganingizda avtomatik saqlanadi.")
    buttons = [[
        InlineKeyboardButton(text=f"⭐ {t['name']}", callback_data=f"noop"),
        InlineKeyboardButton(text="🗑", callback_data=f"del_template:{t['id']}")
    ] for t in templates]
    await cb.message.edit_text(
        "⭐ <b>Shablonlar:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("del_template:"))
async def del_template(cb: CallbackQuery):
    tid = int(cb.data.split(":")[1])
    delete_template(tid, cb.from_user.id)
    await cb.answer("O'chirildi!")
    templates = get_templates(cb.from_user.id)
    if not templates:
        return await cb.message.edit_text("⭐ Shablonlar bo'sh.")
    buttons = [[
        InlineKeyboardButton(text=f"⭐ {t['name']}", callback_data="noop"),
        InlineKeyboardButton(text="🗑", callback_data=f"del_template:{t['id']}")
    ] for t in templates]
    await cb.message.edit_text(
        "⭐ <b>Shablonlar:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()


# ──────────────────────────────────────────
# CHEGIRMA RASMI
# ──────────────────────────────────────────

@dp.callback_query(F.data.startswith("discount:"))
async def cb_discount_start(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split(":")[1])
    await state.update_data(discount_product_id=pid)
    await state.set_state(Discount.old_price)
    await cb.message.answer("💰 Avvalgi narx (so'm):\n<i>Masalan: 21900</i>",
                             parse_mode="HTML")
    await cb.answer()


@dp.message(Discount.old_price)
async def got_old_price(msg: Message, state: FSMContext):
    try:
        price = int(msg.text.strip().replace(" ", ""))
    except ValueError:
        return await msg.answer("❌ Faqat raqam kiriting.")
    await state.update_data(old_price=price)
    await state.set_state(Discount.new_price)
    await msg.answer("💸 Yangi chegirma narxi:")


@dp.message(Discount.new_price)
async def got_new_price(msg: Message, state: FSMContext):
    try:
        price = int(msg.text.strip().replace(" ", ""))
    except ValueError:
        return await msg.answer("❌ Faqat raqam kiriting.")
    data = await state.get_data()
    if price >= data["old_price"]:
        return await msg.answer("❌ Yangi narx avvalgidan kam bo'lishi kerak!")
    await state.update_data(new_price=price)
    await state.set_state(Discount.reason)
    await msg.answer("📝 Chegirma sababi? (yoki /skip)")


@dp.message(Discount.reason)
async def got_reason(msg: Message, state: FSMContext):
    reason = "Muddat yaqinlashdi" if msg.text == "/skip" else msg.text.strip()
    data = await state.get_data()
    await state.clear()
    p = get_product(data["discount_product_id"])
    if not p:
        return await msg.answer("❌ Mahsulot topilmadi.")
    shop = get_shop_name(msg.from_user.id)
    await msg.answer("⏳ Rasm tayyorlanmoqda...")
    try:
        path = generate_discount_image(
            product_name=p["name"],
            old_price=data["old_price"],
            new_price=data["new_price"],
            reason=reason,
            shop_name=shop,
            output_name=f"discount_{p['id']}.png"
        )
        add_discount(p["id"], data["old_price"], data["new_price"], reason, path)
        pct = round((data["old_price"] - data["new_price"]) / data["old_price"] * 100)
        await msg.answer_photo(
            photo=FSInputFile(path),
            caption=(
                f"🎨 <b>{p['name']}</b> chegirma rasmi tayyor!\n\n"
                f"💰 {data['old_price']:,} → {data['new_price']:,} so'm\n"
                f"📉 Chegirma: {pct}%"
            ).replace(",", " "),
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        logger.error(f"Rasm xatosi: {e}")
        await msg.answer("❌ Rasm yaratishda xato.", reply_markup=main_keyboard())


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

async def main():
    init_db()
    start_scheduler(bot)
    logger.info("🚀 Day+ bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
