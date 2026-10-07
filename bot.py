# -*- coding: utf-8 -*-

import logging
import os
import asyncio
import html
import aiosqlite

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)


# ============================================================
# SOZLAMALAR
# ============================================================

API_TOKEN = os.environ.get("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable topilmadi!")

ADMIN_ID = int(
    os.environ.get(
        "ADMIN_ID",
        "1151233619"
    )
)

DB_PATH = os.environ.get(
    "DB_PATH",
    "bot.db"
)

# Telegram kanal
CHANNEL_ID = -1003800297556

CHANNEL_INVITE_LINK = (
    "https://t.me/kunlikishchiroqchi"
)

# Toshkent vaqti
TASHKENT_TZ = ZoneInfo(
    "Asia/Tashkent"
)

# Log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=API_TOKEN
)

storage = MemoryStorage()

dp = Dispatcher(
    bot,
    storage=storage
)


# ============================================================
# ONLINE FOYDALANUVCHILAR
# ============================================================

MEN_ONLINE_DB = set()

WOMEN_ONLINE_DB = set()


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================

def current_datetime():
    """
    Toshkent vaqti:
    07.10.2026 19:45
    """
    return datetime.now(
        TASHKENT_TZ
    ).strftime(
        "%d.%m.%Y %H:%M"
    )


def current_date():
    """
    Faqat sana:
    07.10.2026
    """
    return datetime.now(
        TASHKENT_TZ
    ).strftime(
        "%d.%m.%Y"
    )


def esc(value):
    """
    Telegram HTML parse_mode uchun
    foydalanuvchi yozgan matnni xavfsiz qiladi.
    """
    if value is None:
        return ""

    return html.escape(
        str(value)
    )


# ============================================================
# DATABASE
# ============================================================

async def db_connect():
    """
    SQLite ulanishini sozlaydi.
    """
    db = await aiosqlite.connect(
        DB_PATH
    )

    await db.execute(
        "PRAGMA busy_timeout = 5000"
    )

    await db.execute(
        "PRAGMA journal_mode = WAL"
    )

    await db.execute(
        "PRAGMA foreign_keys = ON"
    )

    return db


async def ensure_column(
    db,
    table_name,
    column_name,
    column_type
):
    """
    Jadvalda ustun bo'lmasa avtomatik qo'shadi.
    """

    cursor = await db.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = await cursor.fetchall()

    column_names = [
        row[1]
        for row in columns
    ]

    if column_name not in column_names:

        await db.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_type}
            """
        )

        await db.execute(
            f"""
            UPDATE {table_name}
            SET {column_name}=?
            WHERE {column_name} IS NULL
               OR {column_name}=''
            """,
            (
                current_datetime(),
            )
        )


async def init_db():

    db = await db_connect()

    try:

        # ====================================================
        # UMUMIY E'LONLAR
        # ====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                phone TEXT
            )
            """
        )

        # ====================================================
        # AYOLLAR E'LONLARI
        # ====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS women_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                phone TEXT
            )
            """
        )

        # ====================================================
        # USTALAR
        # ====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                full_name TEXT,
                phone TEXT,
                description TEXT
            )
            """
        )

        # ====================================================
        # FOYDALANUVCHILAR
        # ====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT
            )
            """
        )

        # ====================================================
        # YUK MASHINASI EGALARI
        # ====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS truck_owners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                truck_type TEXT,
                phone TEXT,
                description TEXT,
                created_at TEXT
            )
            """
        )

        # ====================================================
        # YUK MASHINASI KERAK E'LONLARI
        # ====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS truck_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                truck_type TEXT,
                text TEXT,
                phone TEXT,
                created_at TEXT
            )
            """
        )

        # Eski jadvallarga sana qo'shish
        await ensure_column(
            db,
            "ads",
            "created_at",
            "TEXT"
        )

        await ensure_column(
            db,
            "women_ads",
            "created_at",
            "TEXT"
        )

        await ensure_column(
            db,
            "masters",
            "created_at",
            "TEXT"
        )

        await db.commit()

        logger.info(
            "Database muvaffaqiyatli tayyorlandi."
        )

    finally:

        await db.close()


# ============================================================
# FOYDALANUVCHILAR
# ============================================================

async def register_user(
    user_id,
    full_name,
    username
):

    db = await db_connect()

    try:

        await db.execute(
            """
            INSERT INTO users
            (
                user_id,
                full_name,
                username
            )
            VALUES (?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                full_name=excluded.full_name,
                username=excluded.username
            """,
            (
                user_id,
                full_name,
                username
            )
        )

        await db.commit()

    finally:

        await db.close()


async def get_all_user_ids():

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT user_id
            FROM users
            """
        )

        rows = await cursor.fetchall()

        return [
            row[0]
            for row in rows
        ]

    finally:

        await db.close()


async def get_users_count():

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM users
            """
        )

        row = await cursor.fetchone()

        return row[0] if row else 0

    finally:

        await db.close()


# ============================================================
# UMUMIY E'LONLAR
# ============================================================

async def add_ad(
    user_id,
    user_name,
    text,
    phone
):

    db = await db_connect()

    try:

        await db.execute(
            """
            INSERT INTO ads
            (
                user_id,
                user_name,
                text,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user_name,
                text,
                phone,
                current_datetime()
            )
        )

        await db.commit()

    finally:

        await db.close()


async def get_all_ads():

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                text,
                phone,
                created_at
            FROM ads
            ORDER BY id DESC
            """
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "text": row[3],
                "phone": row[4],
                "created_at": row[5]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def get_user_ads(user_id):

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                text,
                phone,
                created_at
            FROM ads
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (
                user_id,
            )
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "text": row[3],
                "phone": row[4],
                "created_at": row[5]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def delete_ad(ad_id):

    db = await db_connect()

    try:

        await db.execute(
            "DELETE FROM ads WHERE id=?",
            (
                ad_id,
            )
        )

        await db.commit()

    finally:

        await db.close()


# ============================================================
# AYOLLAR E'LONLARI
# ============================================================

async def add_women_ad(
    user_id,
    user_name,
    text,
    phone
):

    db = await db_connect()

    try:

        await db.execute(
            """
            INSERT INTO women_ads
            (
                user_id,
                user_name,
                text,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user_name,
                text,
                phone,
                current_datetime()
            )
        )

        await db.commit()

    finally:

        await db.close()


async def get_all_women_ads():

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                text,
                phone,
                created_at
            FROM women_ads
            ORDER BY id DESC
            """
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "text": row[3],
                "phone": row[4],
                "created_at": row[5]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def get_user_women_ads(user_id):

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                text,
                phone,
                created_at
            FROM women_ads
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (
                user_id,
            )
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "text": row[3],
                "phone": row[4],
                "created_at": row[5]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def delete_women_ad(ad_id):

    db = await db_connect()

    try:

        await db.execute(
            """
            DELETE FROM women_ads
            WHERE id=?
            """,
            (
                ad_id,
            )
        )

        await db.commit()

    finally:

        await db.close()


# ============================================================
# USTALAR
# ============================================================

async def add_master(
    category,
    full_name,
    phone,
    description
):

    db = await db_connect()

    try:

        await db.execute(
            """
            INSERT INTO masters
            (
                category,
                full_name,
                phone,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                category,
                full_name,
                phone,
                description,
                current_datetime()
            )
        )

        await db.commit()

    finally:

        await db.close()


async def get_masters_by_category(
    category
):

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                category,
                full_name,
                phone,
                description,
                created_at
            FROM masters
            WHERE LOWER(category) LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{category.lower()}%",
            )
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "category": row[1],
                "full_name": row[2],
                "phone": row[3],
                "description": row[4],
                "created_at": row[5]
            }
            for row in rows
        ]

    finally:

        await db.close()


# ============================================================
# YUK MASHINALARI EGALARI
# ============================================================

async def add_truck_owner(
    user_id,
    user_name,
    truck_type,
    phone,
    description
):

    db = await db_connect()

    try:

        # Bitta foydalanuvchi bir xil turdagi
        # mashinani ikki marta kiritmasin.
        cursor = await db.execute(
            """
            SELECT id
            FROM truck_owners
            WHERE user_id=?
              AND truck_type=?
            LIMIT 1
            """,
            (
                user_id,
                truck_type
            )
        )

        existing = await cursor.fetchone()

        if existing:

            await db.execute(
                """
                UPDATE truck_owners
                SET
                    user_name=?,
                    phone=?,
                    description=?,
                    created_at=?
                WHERE id=?
                """,
                (
                    user_name,
                    phone,
                    description,
                    current_datetime(),
                    existing[0]
                )
            )

        else:

            await db.execute(
                """
                INSERT INTO truck_owners
                (
                    user_id,
                    user_name,
                    truck_type,
                    phone,
                    description,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_name,
                    truck_type,
                    phone,
                    description,
                    current_datetime()
                )
            )

        await db.commit()

    finally:

        await db.close()


async def get_truck_owners(
    truck_type
):

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                truck_type,
                phone,
                description,
                created_at
            FROM truck_owners
            WHERE truck_type=?
            ORDER BY id DESC
            """,
            (
                truck_type,
            )
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "truck_type": row[3],
                "phone": row[4],
                "description": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def get_user_truck_owners(
    user_id
):

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                truck_type,
                phone,
                description,
                created_at
            FROM truck_owners
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (
                user_id,
            )
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "truck_type": row[3],
                "phone": row[4],
                "description": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def delete_truck_owner(
    owner_id
):

    db = await db_connect()

    try:

        await db.execute(
            """
            DELETE FROM truck_owners
            WHERE id=?
            """,
            (
                owner_id,
            )
        )

        await db.commit()

    finally:

        await db.close()


# ============================================================
# YUK MASHINASI KERAK
# ============================================================

async def add_truck_request(
    user_id,
    user_name,
    truck_type,
    text,
    phone
):

    db = await db_connect()

    try:

        await db.execute(
            """
            INSERT INTO truck_requests
            (
                user_id,
                user_name,
                truck_type,
                text,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user_name,
                truck_type,
                text,
                phone,
                current_datetime()
            )
        )

        await db.commit()

    finally:

        await db.close()


async def get_user_truck_requests(
    user_id
):

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT
                id,
                user_id,
                user_name,
                truck_type,
                text,
                phone,
                created_at
            FROM truck_requests
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (
                user_id,
            )
        )

        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "truck_type": row[3],
                "text": row[4],
                "phone": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]

    finally:

        await db.close()


async def delete_truck_request(
    request_id
):

    db = await db_connect()

    try:

        await db.execute(
            """
            DELETE FROM truck_requests
            WHERE id=?
            """,
            (
                request_id,
            )
        )

        await db.commit()

    finally:

        await db.close()


async def get_truck_requests_count():

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM truck_requests
            """
        )

        row = await cursor.fetchone()

        return row[0] if row else 0

    finally:

        await db.close()


async def get_truck_owners_count():

    db = await db_connect()

    try:

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM truck_owners
            """
        )

        row = await cursor.fetchone()

        return row[0] if row else 0

    finally:

        await db.close()


# ============================================================
# ASOSIY MENU
# ============================================================

def main_menu():

    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    kb.add(
        KeyboardButton(
            "👨‍💻 Erkaklar online"
        ),
        KeyboardButton(
            "👩‍💻 Ayollar online"
        ),
        KeyboardButton(
            "🔕 Xabarlarni to'xtatish"
        ),
        KeyboardButton(
            "🔍 Ish topish"
        ),
        KeyboardButton(
            "📢 E'lon berish"
        ),
        KeyboardButton(
            "🗑 Mening e'lonlarim"
        ),
        KeyboardButton(
            "👷‍♂️ Ustalar xizmati"
        ),
        KeyboardButton(
            "🚚 Yuk mashinalar"
        ),
        KeyboardButton(
            "🧵 Ayollar bo'limi"
        ),
        KeyboardButton(
            "ℹ️ Ma'lumot"
        )
    )

    return kb


# ============================================================
# USTALAR MENYUSI
# ============================================================

def masters_menu():

    kb = InlineKeyboardMarkup(
        row_width=1
    )

    kb.add(
        InlineKeyboardButton(
            "🏗 Qurilish ustalari",
            callback_data="master_build"
        ),
        InlineKeyboardButton(
            "🔌 Elektrik va Santexnik",
            callback_data="master_electric"
        ),
        InlineKeyboardButton(
            "🪚 Duradgor va Payvandchi",
            callback_data="master_welder"
        ),
        InlineKeyboardButton(
            "🎨 Malyar va Oboichi",
            callback_data="master_finish"
        ),
        InlineKeyboardButton(
            "🚗 Avto servis",
            callback_data="master_auto"
        ),
        InlineKeyboardButton(
            "🪟 Akfa romlar",
            callback_data="master_akfa"
        ),
        InlineKeyboardButton(
            "🛋 Mebelchi",
            callback_data="master_mebel"
        ),
        InlineKeyboardButton(
            "➕ O'z xizmatimni qo'shish",
            callback_data="add_master"
        )
    )

    return kb


# ============================================================
# AYOLLAR MENYUSI
# ============================================================

def women_menu():

    kb = InlineKeyboardMarkup(
        row_width=1
    )

    kb.add(
        InlineKeyboardButton(
            "🔍 Ish topish (Ayollar bo'limi)",
            callback_data="women_find"
        ),
        InlineKeyboardButton(
            "📢 E'lon berish (Ayollar bo'limi)",
            callback_data="women_post"
        )
    )

    return kb


# ============================================================
# USTA KATEGORIYALARI
# ============================================================

def categories_keyboard():

    kb = InlineKeyboardMarkup(
        row_width=1
    )

    categories = [
        (
            "🏗 Qurilish ustalari",
            "Qurilish ustalari"
        ),
        (
            "🔌 Elektrik va Santexnik",
            "Elektrik va Santexnik"
        ),
        (
            "🪚 Duradgor va Payvandchi",
            "Duradgor va Payvandchi"
        ),
        (
            "🎨 Malyar va Oboichi",
            "Malyar va Oboichi"
        ),
        (
            "🚗 Avto servis",
            "Avto servis"
        ),
        (
            "🪟 Akfa romlar",
            "Akfa romlar"
        ),
        (
            "🛋 Mebelchi",
            "Mebelchi"
        )
    ]

    for title, category in categories:

        kb.add(
            InlineKeyboardButton(
                title,
                callback_data=f"cat_{category}"
            )
        )

    return kb


# ============================================================
# YUK MASHINALAR MENYUSI
# ============================================================

def trucks_menu():

    kb = InlineKeyboardMarkup(
        row_width=1
    )

    kb.add(
        InlineKeyboardButton(
            "🔎 Yuk mashinasi kerak",
            callback_data="truck_need"
        ),
        InlineKeyboardButton(
            "🚛 Yuk mashinasi bor, xizmat ko'rsataman",
            callback_data="truck_have"
        )
    )

    return kb


def truck_type_keyboard(
    action
):

    kb = InlineKeyboardMarkup(
        row_width=1
    )

    kb.add(
        InlineKeyboardButton(
            "🚚 Kichik yuk mashinasi",
            callback_data=f"truck_{action}_small"
        ),
        InlineKeyboardButton(
            "🚛 Katta yuk mashinasi",
            callback_data=f"truck_{action}_large"
        )
    )

    return kb


# ============================================================
# FSM STATES
# ============================================================

class MasterState(StatesGroup):

    category = State()
    full_name = State()
    phone = State()
    description = State()


class AdState(StatesGroup):

    text = State()
    phone = State()


class WomenAdState(StatesGroup):

    text = State()
    phone = State()


class BroadcastState(StatesGroup):

    text = State()
    confirm = State()


class TruckRequestState(StatesGroup):

    truck_type = State()
    text = State()
    phone = State()


class TruckOwnerState(StatesGroup):

    truck_type = State()
    description = State()
    phone = State()


# ============================================================
# MAJBURIY OBUNA
# ============================================================

async def check_sub_channel(
    user_id
):

    try:

        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        return member.status in [
            "creator",
            "administrator",
            "member"
        ]

    except Exception as e:

        logger.error(
            f"Obuna tekshirish xatosi: {e}"
        )

        return False


# ============================================================
# START
# ============================================================

@dp.message_handler(
    commands=["start", "help"],
    state="*"
)
async def send_welcome(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    user_id = message.from_user.id

    await register_user(
        user_id,
        message.from_user.full_name,
        message.from_user.username
    )

    is_subscribed = await check_sub_channel(
        user_id
    )

    if not is_subscribed:

        keyboard = InlineKeyboardMarkup(
            row_width=1
        )

        keyboard.add(
            InlineKeyboardButton(
                text="📢 Kanalga a'zo bo'lish",
                url=CHANNEL_INVITE_LINK
            )
        )

        keyboard.add(
            InlineKeyboardButton(
                text="🔄 Tekshirish",
                callback_data="check_sub"
            )
        )

        await message.answer(
            "⚠️ Botdan foydalanish uchun avval "
            "kanalimizga a'zo bo'ling.\n\n"
            "A'zo bo'lgandan so'ng "
            "\"🔄 Tekshirish\" tugmasini bosing.",
            reply_markup=keyboard
        )

        return

    await message.answer(
        "👋 <b>Chiroqchi tumanida ish topish "
        "va ish berish botiga xush kelibsiz!</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ============================================================
# OBUNANI TEKSHIRISH
# ============================================================

@dp.callback_query_handler(
    text="check_sub"
)
async def process_check_sub(
    callback: types.CallbackQuery
):

    user_id = callback.from_user.id

    is_subscribed = await check_sub_channel(
        user_id
    )

    if is_subscribed:

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "✅ Rahmat! Obuna tasdiqlandi.\n\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=main_menu()
        )

        await callback.answer()

    else:

        await callback.answer(
            "Siz hali kanalga a'zo bo'lmagansiz!",
            show_alert=True
        )


# ============================================================
# ONLINE — ERKAKLAR
# ============================================================

@dp.message_handler(
    text="👨‍💻 Erkaklar online",
    state="*"
)
async def men_online_section(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    user_id = message.from_user.id

    MEN_ONLINE_DB.add(
        user_id
    )

    WOMEN_ONLINE_DB.discard(
        user_id
    )

    await message.answer(
        "✅ Siz <b>Erkaklar online</b> "
        "bo'limiga ulandingiz!",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ============================================================
# ONLINE — AYOLLAR
# ============================================================

@dp.message_handler(
    text="👩‍💻 Ayollar online",
    state="*"
)
async def women_online_section(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    user_id = message.from_user.id

    WOMEN_ONLINE_DB.add(
        user_id
    )

    MEN_ONLINE_DB.discard(
        user_id
    )

    await message.answer(
        "✅ Siz <b>Ayollar online</b> "
        "bo'limiga ulandingiz!",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ============================================================
# XABARLARNI TO'XTATISH
# ============================================================

@dp.message_handler(
    text="🔕 Xabarlarni to'xtatish",
    state="*"
)
async def stop_notifications(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    user_id = message.from_user.id

    removed = False

    if user_id in MEN_ONLINE_DB:

        MEN_ONLINE_DB.remove(
            user_id
        )

        removed = True

    if user_id in WOMEN_ONLINE_DB:

        WOMEN_ONLINE_DB.remove(
            user_id
        )

        removed = True

    if removed:

        await message.answer(
            "🔕 Barcha avtomatik xabarlar "
            "to'xtatildi.",
            reply_markup=main_menu()
        )

    else:

        await message.answer(
            "Sizda avtomatik xabarlar "
            "allaqachon o'chirilgan.",
            reply_markup=main_menu()
        )


# ============================================================
# USTALAR
# ============================================================

@dp.message_handler(
    text="👷‍♂️ Ustalar xizmati",
    state="*"
)
async def show_masters(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    await message.answer(
        "👷‍♂️ <b>Ustalar xizmati</b>\n\n"
        "Kerakli mutaxassislikni tanlang:",
        reply_markup=masters_menu(),
        parse_mode="HTML"
    )


# ============================================================
# USTA KATEGORIYASI
# ============================================================

@dp.callback_query_handler(
    lambda c: (
        c.data
        and c.data.startswith("master_")
    )
)
async def process_master_category(
    callback: types.CallbackQuery
):

    await callback.answer()

    cat_code = callback.data.split(
        "_",
        1
    )[1]

    cat_names = {
        "build": "Qurilish ustalari",
        "electric": "Elektrik va Santexnik",
        "welder": "Duradgor va Payvandchi",
        "finish": "Malyar va Oboichi",
        "auto": "Avto servis",
        "akfa": "Akfa romlar",
        "mebel": "Mebelchi"
    }

    target_cat = cat_names.get(
        cat_code
    )

    if not target_cat:

        await callback.message.answer(
            "⚠️ Kategoriya topilmadi."
        )

        return

    filtered = await get_masters_by_category(
        target_cat
    )

    if not filtered:

        await callback.message.answer(
            f"👷‍♂️ <b>{esc(target_cat)}</b>\n\n"
            "Hozircha bu yo'nalishda "
            "ustalar mavjud emas.",
            parse_mode="HTML"
        )

        return

    await callback.message.answer(
        f"👷‍♂️ <b>{esc(target_cat)}</b>\n\n"
        f"Mavjud ustalar: {len(filtered)} ta",
        parse_mode="HTML"
    )

    for idx, master in enumerate(
        filtered,
        1
    ):

        text = (
            f"👷‍♂️ <b>Usta #{idx}</b>\n\n"
            f"🔧 <b>Yo'nalish:</b> "
            f"{esc(master['category'])}\n"
            f"👤 <b>Ism:</b> "
            f"{esc(master['full_name'])}\n"
            f"📞 <b>Telefon:</b> "
            f"{esc(master['phone'])}\n"
            f"📝 <b>Xizmat:</b> "
            f"{esc(master['description'])}\n"
            f"📅 <b>Sana:</b> "
            f"{esc(master['created_at'])}"
        )

        await callback.message.answer(
            text,
            parse_mode="HTML"
        )


# ============================================================
# USTA QO'SHISH
# ============================================================

@dp.callback_query_handler(
    text="add_master"
)
async def add_master_start(
    callback: types.CallbackQuery
):

    await callback.answer()

    await callback.message.answer(
        "🔧 Yo'nalishni tanlang:",
        reply_markup=categories_keyboard()
    )

    await MasterState.category.set()


@dp.callback_query_handler(
    lambda c: (
        c.data
        and c.data.startswith("cat_")
    ),
    state=MasterState.category
)
async def process_category_choice(
    callback: types.CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    selected_category = callback.data.split(
        "_",
        1
    )[1]

    async with state.proxy() as data:

        data["category"] = selected_category

    await callback.message.answer(
        "👤 Ism va familiyangizni kiriting:"
    )

    await MasterState.full_name.set()


@dp.message_handler(
    state=MasterState.full_name
)
async def process_master_name(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["full_name"] = message.text

    await message.answer(
        "📞 Telefon raqamingizni kiriting:"
    )

    await MasterState.phone.set()


@dp.message_handler(
    state=MasterState.phone
)
async def process_master_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["phone"] = message.text

    await message.answer(
        "📝 Qisqacha tajribangiz yoki "
        "xizmatingiz haqida yozing:"
    )

    await MasterState.description.set()


@dp.message_handler(
    state=MasterState.description
)
async def process_master_description(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        category = data["category"]
        full_name = data["full_name"]
        phone = data["phone"]

    await add_master(
        category,
        full_name,
        phone,
        message.text
    )

    await message.answer(
        "✅ <b>Xizmatingiz muvaffaqiyatli saqlandi!</b>\n\n"
        f"🔧 Yo'nalish: {esc(category)}\n"
        f"👤 Ism: {esc(full_name)}\n"
        f"📞 Telefon: {esc(phone)}\n"
        f"📅 Sana: {current_datetime()}",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await state.finish()


# ============================================================
# AYOLLAR BO'LIMI
# ============================================================

@dp.message_handler(
    text="🧵 Ayollar bo'limi",
    state="*"
)
async def show_women_section(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    await message.answer(
        "🧵 <b>Ayollar bo'limi</b>\n\n"
        "Tikuvchilik, pazandachilik, uy xo'jaligi "
        "va boshqa xizmatlar.\n\n"
        "Kerakli tugmani tanlang:",
        reply_markup=women_menu(),
        parse_mode="HTML"
    )


# ============================================================
# AYOLLAR — ISH TOPISH
# ============================================================

@dp.callback_query_handler(
    text="women_find"
)
async def process_women_find(
    callback: types.CallbackQuery
):

    await callback.answer()

    women_ads = await get_all_women_ads()

    if not women_ads:

        await callback.message.answer(
            "🧵 <b>Ayollar bo'limi</b>\n\n"
            "Hozircha e'lonlar mavjud emas.",
            parse_mode="HTML"
        )

        return

    await callback.message.answer(
        f"🧵 <b>Ayollar bo'limidagi "
        f"mavjud e'lonlar: {len(women_ads)} ta</b>",
        parse_mode="HTML"
    )

    for idx, ad in enumerate(
        women_ads,
        1
    ):

        text = (
            f"🧵 <b>E'lon #{idx}</b>\n\n"
            f"📝 {esc(ad['text'])}\n\n"
            f"👤 <b>Muallif:</b> "
            f"{esc(ad['user_name'])}\n"
            f"📞 <b>Telefon:</b> "
            f"{esc(ad['phone'])}\n"
            f"📅 <b>Sana:</b> "
            f"{esc(ad['created_at'])}"
        )

        await callback.message.answer(
            text,
            parse_mode="HTML"
        )


# ============================================================
# AYOLLAR — E'LON BERISH
# ============================================================

@dp.callback_query_handler(
    text="women_post"
)
async def process_women_post(
    callback: types.CallbackQuery
):

    await callback.answer()

    await callback.message.answer(
        "🧵 Ayollar bo'limi uchun "
        "e'lon matnini kiriting:"
    )

    await WomenAdState.text.set()


@dp.message_handler(
    state=WomenAdState.text
)
async def process_women_ad_text(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["text"] = message.text

    await message.answer(
        "📞 Aloqa uchun telefon raqamingizni "
        "kiriting:"
    )

    await WomenAdState.phone.set()


@dp.message_handler(
    state=WomenAdState.phone
)
async def process_women_ad_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        ad_text = data["text"]

    await add_women_ad(
        message.from_user.id,
        message.from_user.full_name,
        ad_text,
        message.text
    )

    ad_message = (
        "<b>🧵 AYOLLAR ONLINE — YANGI E'LON!</b>\n\n"
        f"📝 {esc(ad_text)}\n\n"
        f"👤 <b>Muallif:</b> "
        f"{esc(message.from_user.full_name)}\n"
        f"📞 <b>Telefon:</b> "
        f"{esc(message.text)}\n"
        f"📅 <b>Sana:</b> "
        f"{current_datetime()}"
    )

    sent_count = 0

    for user_id in list(
        WOMEN_ONLINE_DB
    ):

        try:

            await bot.send_message(
                user_id,
                ad_message,
                parse_mode="HTML"
            )

            sent_count += 1

        except Exception:

            pass

    await message.answer(
        "✅ Ayollar bo'limiga e'loningiz qo'shildi!\n\n"
        f"📨 {sent_count} ta ayol foydalanuvchiga "
        "bildirishnoma yuborildi.",
        reply_markup=main_menu()
    )

    await state.finish()


# ============================================================
# UMUMIY ISH TOPISH
# ============================================================

@dp.message_handler(
    text="🔍 Ish topish",
    state="*"
)
async def find_work(
    message: types.Message,
    state: FSMContext
):

    # ENG MUHIM:
    # foydalanuvchi oldingi FSM jarayonida bo'lsa ham
    # Ish topish tugmasi ishlaydi.
    await state.finish()

    ads = await get_all_ads()

    if not ads:

        await message.answer(
            "🔍 <b>Mavjud ishlar</b>\n\n"
            "Hozircha hech qanday ish e'loni mavjud emas.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

        return

    await message.answer(
        f"🔍 <b>Mavjud ishlar: {len(ads)} ta</b>\n\n"
        "Quyida barcha mavjud e'lonlar:",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    # HAR BIR E'LON ALOHIDA XABARDA
    for idx, ad in enumerate(
        ads,
        1
    ):

        created_at = (
            ad["created_at"]
            or "Sana ko'rsatilmagan"
        )

        text = (
            f"📢 <b>Ish e'loni #{idx}</b>\n\n"
            f"📝 {esc(ad['text'])}\n\n"
            f"👤 <b>Muallif:</b> "
            f"{esc(ad['user_name'])}\n"
            f"📞 <b>Telefon:</b> "
            f"{esc(ad['phone'])}\n"
            f"📅 <b>Sana:</b> "
            f"{esc(created_at)}"
        )

        await message.answer(
            text,
            parse_mode="HTML"
        )


# ============================================================
# UMUMIY E'LON BERISH
# ============================================================

@dp.message_handler(
    text="📢 E'lon berish",
    state="*"
)
async def post_ad_start(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    await message.answer(
        "📢 E'lon matnini kiriting.\n\n"
        "Masalan:\n"
        "Sotuvchiga ishchi kerak. "
        "Chiroqchi markazida. "
        "Tajriba bo'lishi kerak."
    )

    await AdState.text.set()


@dp.message_handler(
    state=AdState.text
)
async def process_ad_text(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["text"] = message.text

    await message.answer(
        "📞 Aloqa uchun telefon raqamingizni "
        "kiriting:"
    )

    await AdState.phone.set()


@dp.message_handler(
    state=AdState.phone
)
async def process_ad_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        ad_text = data["text"]

    await add_ad(
        message.from_user.id,
        message.from_user.full_name,
        ad_text,
        message.text
    )

    ad_message = (
        "<b>📢 ERKAKLAR ONLINE — YANGI E'LON!</b>\n\n"
        f"📝 {esc(ad_text)}\n\n"
        f"👤 <b>Muallif:</b> "
        f"{esc(message.from_user.full_name)}\n"
        f"📞 <b>Telefon:</b> "
        f"{esc(message.text)}\n"
        f"📅 <b>Sana:</b> "
        f"{current_datetime()}"
    )

    sent_count = 0

    for user_id in list(
        MEN_ONLINE_DB
    ):

        try:

            await bot.send_message(
                user_id,
                ad_message,
                parse_mode="HTML"
            )

            sent_count += 1

        except Exception:

            pass

    await message.answer(
        "✅ <b>E'loningiz qabul qilindi!</b>\n\n"
        f"📅 Sana: {current_datetime()}\n"
        f"📨 {sent_count} ta foydalanuvchiga "
        "bildirishnoma yuborildi.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await state.finish()


# ============================================================
# YUK MASHINALAR
# ============================================================

@dp.message_handler(
    text="🚚 Yuk mashinalar",
    state="*"
)
async def truck_main_menu(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    await message.answer(
        "🚚 <b>Yuk mashinalar bo'limi</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=trucks_menu(),
        parse_mode="HTML"
    )


# ============================================================
# YUK MASHINASI KERAK
# ============================================================

@dp.callback_query_handler(
    text="truck_need"
)
async def truck_need_start(
    callback: types.CallbackQuery
):

    await callback.answer()

    await callback.message.answer(
        "🔎 Qanday yuk mashinasi kerak?",
        reply_markup=truck_type_keyboard(
            "need"
        )
    )

    await TruckRequestState.truck_type.set()


@dp.callback_query_handler(
    lambda c: (
        c.data
        and c.data.startswith("truck_need_")
    ),
    state=TruckRequestState.truck_type
)
async def truck_need_type(
    callback: types.CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    truck_code = callback.data.split(
        "_"
    )[-1]

    if truck_code == "small":

        truck_type = (
            "Kichik yuk mashinasi"
        )

    else:

        truck_type = (
            "Katta yuk mashinasi"
        )

    async with state.proxy() as data:

        data["truck_type"] = truck_type

    await callback.message.answer(
        f"🚛 <b>{esc(truck_type)}</b>\n\n"
        "Qayerdan qayerga yuk olib borish kerakligini "
        "va boshqa kerakli ma'lumotlarni yozing:",
        parse_mode="HTML"
    )

    await TruckRequestState.text.set()


@dp.message_handler(
    state=TruckRequestState.text
)
async def truck_need_text(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["text"] = message.text

    await message.answer(
        "📞 Aloqa uchun telefon raqamingizni "
        "kiriting:"
    )

    await TruckRequestState.phone.set()


@dp.message_handler(
    state=TruckRequestState.phone
)
async def truck_need_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        truck_type = data["truck_type"]
        truck_text = data["text"]

    await add_truck_request(
        message.from_user.id,
        message.from_user.full_name,
        truck_type,
        truck_text,
        message.text
    )

    # FAQAT MOS TURDAGI EGALAR
    owners = await get_truck_owners(
        truck_type
    )

    notification = (
        "🚨 <b>YANGI YUK BUYURTMASI!</b>\n\n"
        f"🚛 <b>Mashina turi:</b> "
        f"{esc(truck_type)}\n\n"
        f"📝 <b>Buyurtma:</b>\n"
        f"{esc(truck_text)}\n\n"
        f"👤 <b>Mijoz:</b> "
        f"{esc(message.from_user.full_name)}\n"
        f"📞 <b>Telefon:</b> "
        f"{esc(message.text)}\n"
        f"📅 <b>Sana:</b> "
        f"{current_datetime()}\n\n"
        f"⚡ Siz {esc(truck_type.lower())} "
        "egasi sifatida ro'yxatdan o'tgansiz."
    )

    sent_count = 0

    for owner in owners:

        try:

            await bot.send_message(
                owner["user_id"],
                notification,
                parse_mode="HTML"
            )

            sent_count += 1

        except Exception as e:

            logger.warning(
                f"Truck ownerga xabar yuborilmadi: {e}"
            )

    await message.answer(
        "✅ <b>Yuk mashinasi kerakligi "
        "haqidagi e'lon qabul qilindi!</b>\n\n"
        f"🚛 Mashina turi: "
        f"{esc(truck_type)}\n"
        f"📅 Sana: {current_datetime()}\n\n"
        f"📨 {sent_count} ta mos mashina egasiga "
        "xabar yuborildi.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await state.finish()


# ============================================================
# YUK MASHINASI BOR
# ============================================================

@dp.callback_query_handler(
    text="truck_have"
)
async def truck_have_start(
    callback: types.CallbackQuery
):

    await callback.answer()

    await callback.message.answer(
        "🚛 Qaysi turdagi yuk mashinangiz bor?",
        reply_markup=truck_type_keyboard(
            "have"
        )
    )

    await TruckOwnerState.truck_type.set()


@dp.callback_query_handler(
    lambda c: (
        c.data
        and c.data.startswith("truck_have_")
    ),
    state=TruckOwnerState.truck_type
)
async def truck_have_type(
    callback: types.CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    truck_code = callback.data.split(
        "_"
    )[-1]

    if truck_code == "small":

        truck_type = (
            "Kichik yuk mashinasi"
        )

    else:

        truck_type = (
            "Katta yuk mashinasi"
        )

    async with state.proxy() as data:

        data["truck_type"] = truck_type

    await callback.message.answer(
        f"🚛 <b>{esc(truck_type)}</b>\n\n"
        "Mashina va ko'rsatadigan xizmatingiz "
        "haqida qisqacha ma'lumot yozing:",
        parse_mode="HTML"
    )

    await TruckOwnerState.description.set()


@dp.message_handler(
    state=TruckOwnerState.description
)
async def truck_have_description(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["description"] = message.text

    await message.answer(
        "📞 Aloqa uchun telefon raqamingizni "
        "kiriting:"
    )

    await TruckOwnerState.phone.set()


@dp.message_handler(
    state=TruckOwnerState.phone
)
async def truck_have_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        truck_type = data["truck_type"]
        description = data["description"]

    await add_truck_owner(
        message.from_user.id,
        message.from_user.full_name,
        truck_type,
        message.text,
        description
    )

    await message.answer(
        "✅ <b>Yuk mashinasi egasi sifatida "
        "muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"🚛 Turi: {esc(truck_type)}\n"
        f"📞 Telefon: {esc(message.text)}\n"
        f"📅 Sana: {current_datetime()}\n\n"
        "Endi shu turdagi yuk mashinasi kerak "
        "bo'lganida sizga avtomatik xabar keladi.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await state.finish()


# ============================================================
# MENING E'LONLARIM
# ============================================================

@dp.message_handler(
    text="🗑 Mening e'lonlarim",
    state="*"
)
async def my_ads(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    user_id = message.from_user.id

    user_ads = await get_user_ads(
        user_id
    )

    user_women_ads = await get_user_women_ads(
        user_id
    )

    user_truck_owners = await get_user_truck_owners(
        user_id
    )

    user_truck_requests = await get_user_truck_requests(
        user_id
    )

    if not (
        user_ads
        or user_women_ads
        or user_truck_owners
        or user_truck_requests
    ):

        await message.answer(
            "🗑 Sizda hozircha faol e'lonlar yo'q.",
            reply_markup=main_menu()
        )

        return

    await message.answer(
        "🗑 <b>Sizning e'lonlaringiz:</b>",
        parse_mode="HTML"
    )

    # --------------------------------------------------------
    # UMUMIY E'LONLAR
    # --------------------------------------------------------

    for idx, ad in enumerate(
        user_ads,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ E'lonni o'chirish",
                callback_data=(
                    f"del_gen_{ad['id']}"
                )
            )
        )

        text = (
            f"📢 <b>Umumiy e'lon #{idx}</b>\n\n"
            f"📝 {esc(ad['text'])}\n"
            f"📞 {esc(ad['phone'])}\n"
            f"📅 {esc(ad['created_at'])}"
        )

        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    # --------------------------------------------------------
    # AYOLLAR E'LONLARI
    # --------------------------------------------------------

    for idx, ad in enumerate(
        user_women_ads,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ E'lonni o'chirish",
                callback_data=(
                    f"del_women_{ad['id']}"
                )
            )
        )

        text = (
            f"🧵 <b>Ayollar e'loni #{idx}</b>\n\n"
            f"📝 {esc(ad['text'])}\n"
            f"📞 {esc(ad['phone'])}\n"
            f"📅 {esc(ad['created_at'])}"
        )

        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    # --------------------------------------------------------
    # YUK MASHINASI EGASI
    # --------------------------------------------------------

    for idx, owner in enumerate(
        user_truck_owners,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ Xizmat e'lonini o'chirish",
                callback_data=(
                    f"del_truck_owner_{owner['id']}"
                )
            )
        )

        text = (
            f"🚛 <b>Yuk mashinasi xizmati #{idx}</b>\n\n"
            f"🚚 <b>Turi:</b> "
            f"{esc(owner['truck_type'])}\n"
            f"📝 {esc(owner['description'])}\n"
            f"📞 {esc(owner['phone'])}\n"
            f"📅 {esc(owner['created_at'])}"
        )

        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    # --------------------------------------------------------
    # YUK MASHINASI KERAK
    # --------------------------------------------------------

    for idx, req in enumerate(
        user_truck_requests,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ Buyurtmani o'chirish",
                callback_data=(
                    f"del_truck_request_{req['id']}"
                )
            )
        )

        text = (
            f"🔎 <b>Yuk mashinasi kerak #{idx}</b>\n\n"
            f"🚛 <b>Turi:</b> "
            f"{esc(req['truck_type'])}\n"
            f"📝 {esc(req['text'])}\n"
            f"📞 {esc(req['phone'])}\n"
            f"📅 {esc(req['created_at'])}"
        )

        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )


# ============================================================
# E'LON O'CHIRISH
# ============================================================

@dp.callback_query_handler(
    lambda c: (
        c.data
        and c.data.startswith("del_")
    )
)
async def delete_ad_callback(
    callback: types.CallbackQuery
):

    user_id = callback.from_user.id

    parts = callback.data.split(
        "_"
    )

    try:

        # ----------------------------------------------------
        # UMUMIY E'LON
        # del_gen_ID
        # ----------------------------------------------------

        if (
            len(parts) == 3
            and parts[1] == "gen"
        ):

            ad_id = int(
                parts[2]
            )

            # Faqat o'z e'lonini o'chira oladi
            db = await db_connect()

            try:

                cursor = await db.execute(
                    """
                    SELECT user_id
                    FROM ads
                    WHERE id=?
                    """,
                    (
                        ad_id,
                    )
                )

                row = await cursor.fetchone()

            finally:

                await db.close()

            if not row:

                await callback.answer(
                    "Bu e'lon topilmadi.",
                    show_alert=True
                )

                return

            if row[0] != user_id:

                await callback.answer(
                    "Bu e'lon sizniki emas.",
                    show_alert=True
                )

                return

            await delete_ad(
                ad_id
            )

        # ----------------------------------------------------
        # AYOLLAR E'LONI
        # del_women_ID
        # ----------------------------------------------------

        elif (
            len(parts) == 3
            and parts[1] == "women"
        ):

            ad_id = int(
                parts[2]
            )

            db = await db_connect()

            try:

                cursor = await db.execute(
                    """
                    SELECT user_id
                    FROM women_ads
                    WHERE id=?
                    """,
                    (
                        ad_id,
                    )
                )

                row = await cursor.fetchone()

            finally:

                await db.close()

            if not row:

                await callback.answer(
                    "Bu e'lon topilmadi.",
                    show_alert=True
                )

                return

            if row[0] != user_id:

                await callback.answer(
                    "Bu e'lon sizniki emas.",
                    show_alert=True
                )

                return

            await delete_women_ad(
                ad_id
            )

        # ----------------------------------------------------
        # TRUCK OWNER
        # del_truck_owner_ID
        # ----------------------------------------------------

        elif (
            len(parts) == 4
            and parts[1] == "truck"
            and parts[2] == "owner"
        ):

            owner_id = int(
                parts[3]
            )

            db = await db_connect()

            try:

                cursor = await db.execute(
                    """
                    SELECT user_id
                    FROM truck_owners
                    WHERE id=?
                    """,
                    (
                        owner_id,
                    )
                )

                row = await cursor.fetchone()

            finally:

                await db.close()

            if not row:

                await callback.answer(
                    "Bu xizmat topilmadi.",
                    show_alert=True
                )

                return

            if row[0] != user_id:

                await callback.answer(
                    "Bu xizmat sizniki emas.",
                    show_alert=True
                )

                return

            await delete_truck_owner(
                owner_id
            )

        # ----------------------------------------------------
        # TRUCK REQUEST
        # del_truck_request_ID
        # ----------------------------------------------------

        elif (
            len(parts) == 4
            and parts[1] == "truck"
            and parts[2] == "request"
        ):

            request_id = int(
                parts[3]
            )

            db = await db_connect()

            try:

                cursor = await db.execute(
                    """
                    SELECT user_id
                    FROM truck_requests
                    WHERE id=?
                    """,
                    (
                        request_id,
                    )
                )

                row = await cursor.fetchone()

            finally:

                await db.close()

            if not row:

                await callback.answer(
                    "Bu buyurtma topilmadi.",
                    show_alert=True
                )

                return

            if row[0] != user_id:

                await callback.answer(
                    "Bu buyurtma sizniki emas.",
                    show_alert=True
                )

                return

            await delete_truck_request(
                request_id
            )

        else:

            await callback.answer(
                "Noto'g'ri buyruq.",
                show_alert=True
            )

            return

        await callback.answer(
            "✅ O'chirildi."
        )

        try:

            await callback.message.edit_text(
                "✅ E'lon muvaffaqiyatli o'chirildi."
            )

        except Exception:

            pass

    except Exception as e:

        logger.error(
            f"E'lon o'chirish xatosi: {e}"
        )

        await callback.answer(
            "⚠️ O'chirishda xatolik yuz berdi.",
            show_alert=True
        )


# ============================================================
# ADMIN PANEL
# ============================================================

@dp.message_handler(
    commands=["admin"],
    state="*"
)
async def admin_panel(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Sizda admin huquqi yo'q."
        )

        return

    ads = await get_all_ads()

    women_ads = await get_all_women_ads()

    if not ads and not women_ads:

        await message.answer(
            "📭 Hozircha umumiy yoki ayollar "
            "bo'limida e'lonlar mavjud emas."
        )

        return

    await message.answer(
        "🛠 <b>ADMIN PANEL</b>\n\n"
        "Barcha umumiy va ayollar e'lonlari:",
        parse_mode="HTML"
    )

    # Umumiy
    for ad in ads:

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ Admin: o'chirish",
                callback_data=(
                    f"adm_gen_{ad['id']}"
                )
            )
        )

        text = (
            f"📢 <b>[Umumiy] #{ad['id']}</b>\n\n"
            f"👤 Muallif: "
            f"{esc(ad['user_name'])}\n"
            f"📝 {esc(ad['text'])}\n"
            f"📞 {esc(ad['phone'])}\n"
            f"📅 {esc(ad['created_at'])}"
        )

        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )

    # Ayollar
    for ad in women_ads:

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ Admin: o'chirish",
                callback_data=(
                    f"adm_women_{ad['id']}"
                )
            )
        )

        text = (
            f"🧵 <b>[Ayollar] #{ad['id']}</b>\n\n"
            f"👤 Muallif: "
            f"{esc(ad['user_name'])}\n"
            f"📝 {esc(ad['text'])}\n"
            f"📞 {esc(ad['phone'])}\n"
            f"📅 {esc(ad['created_at'])}"
        )

        await message.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML"
        )


# ============================================================
# ADMIN E'LON O'CHIRISH
# ============================================================

@dp.callback_query_handler(
    lambda c: (
        c.data
        and c.data.startswith("adm_")
    )
)
async def admin_delete_callback(
    callback: types.CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "⛔ Siz admin emassiz!",
            show_alert=True
        )

        return

    parts = callback.data.split(
        "_"
    )

    try:

        ad_type = parts[1]

        ad_id = int(
            parts[2]
        )

        if ad_type == "gen":

            await delete_ad(
                ad_id
            )

        elif ad_type == "women":

            await delete_women_ad(
                ad_id
            )

        else:

            await callback.answer(
                "Noto'g'ri e'lon turi.",
                show_alert=True
            )

            return

        await callback.answer(
            "✅ E'lon o'chirildi."
        )

        await callback.message.edit_text(
            "✅ E'lon admin tomonidan o'chirildi."
        )

    except Exception as e:

        logger.error(
            f"Admin delete xatosi: {e}"
        )

        await callback.answer(
            "⚠️ E'lonni o'chirishda xatolik.",
            show_alert=True
        )


# ============================================================
# STATISTIKA
# ============================================================

@dp.message_handler(
    commands=["statistika"],
    state="*"
)
async def show_statistics(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Sizda bu buyruqdan foydalanish "
            "huquqi yo'q."
        )

        return

    users_count = await get_users_count()

    ads = await get_all_ads()

    women_ads = await get_all_women_ads()

    truck_owners = await get_truck_owners_count()

    truck_requests = await get_truck_requests_count()

    await message.answer(
        "📊 <b>BOT STATISTIKASI</b>\n\n"
        f"👥 Jami foydalanuvchilar: "
        f"{users_count}\n"
        f"📢 Umumiy e'lonlar: "
        f"{len(ads)}\n"
        f"🧵 Ayollar e'lonlari: "
        f"{len(women_ads)}\n"
        f"🚛 Yuk mashinasi egalari: "
        f"{truck_owners}\n"
        f"🔎 Yuk mashinasi kerak e'lonlari: "
        f"{truck_requests}",
        parse_mode="HTML"
    )


# ============================================================
# BARCHAGA XABAR
# ============================================================

@dp.message_handler(
    commands=["xabar"],
    state="*"
)
async def broadcast_start(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ Sizda bu buyruqdan foydalanish "
            "huquqi yo'q."
        )

        return

    count = await get_users_count()

    await message.answer(
        f"👥 Botda jami <b>{count}</b> ta "
        "foydalanuvchi mavjud.\n\n"
        "📢 Barchaga yuboriladigan xabar "
        "matnini kiriting:",
        parse_mode="HTML"
    )

    await BroadcastState.text.set()


@dp.message_handler(
    state=BroadcastState.text
)
async def broadcast_preview(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        data["text"] = message.text

    kb = InlineKeyboardMarkup(
        row_width=2
    )

    kb.add(
        InlineKeyboardButton(
            "✅ Ha, yuborish",
            callback_data="broadcast_confirm"
        ),
        InlineKeyboardButton(
            "❌ Bekor qilish",
            callback_data="broadcast_cancel"
        )
    )

    await message.answer(
        "📢 <b>Xabar ko'rinishi:</b>\n\n"
        f"{esc(message.text)}\n\n"
        "Yuborishni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await BroadcastState.confirm.set()


@dp.callback_query_handler(
    text="broadcast_cancel",
    state=BroadcastState.confirm
)
async def broadcast_cancel(
    callback: types.CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await callback.message.edit_text(
        "❌ Xabar yuborish bekor qilindi."
    )

    await state.finish()


@dp.callback_query_handler(
    text="broadcast_confirm",
    state=BroadcastState.confirm
)
async def broadcast_confirm(
    callback: types.CallbackQuery,
    state: FSMContext
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "⛔ Siz admin emassiz!",
            show_alert=True
        )

        return

    async with state.proxy() as data:

        text = data.get(
            "text",
            ""
        )

    await state.finish()

    await callback.answer()

    await callback.message.edit_text(
        "⏳ Xabar yuborilmoqda..."
    )

    user_ids = await get_all_user_ids()

    success = 0
    failed = 0

    for user_id in user_ids:

        try:

            await bot.send_message(
                user_id,
                text
            )

            success += 1

        except Exception as e:

            failed += 1

            logger.warning(
                f"Xabar yuborilmadi {user_id}: {e}"
            )

        # Telegram limitiga tushib qolmaslik
        await asyncio.sleep(
            0.08
        )

    await bot.send_message(
        callback.from_user.id,
        "✅ <b>Xabar yuborish tugadi!</b>\n\n"
        f"📨 Yuborildi: {success} ta\n"
        f"🚫 Yuborilmadi: {failed} ta",
        parse_mode="HTML"
    )


# ============================================================
# INFO
# ============================================================

@dp.message_handler(
    text="ℹ️ Ma'lumot",
    state="*"
)
async def info_text(
    message: types.Message,
    state: FSMContext
):

    await state.finish()

    await message.answer(
        "ℹ️ <b>Chiroqchi ish boti</b>\n\n"
        "🔍 Ish topish — mavjud ishlarni ko'rish.\n"
        "📢 E'lon berish — ishchi yoki xodim izlash.\n"
        "👷‍♂️ Ustalar xizmati — ustalarni topish.\n"
        "🚚 Yuk mashinalar — yuk mashinasi kerak "
        "bo'lganlar va mashina egalari uchun.\n"
        "🧵 Ayollar bo'limi — ayollar uchun ish "
        "va xizmatlar.\n\n"
        "🤖 @KunlikIsh_chiroqchi_bot\n"
        "📢 @kunlikishchiroqchi",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ============================================================
# XATOLARNI USHLASH
# ============================================================

@dp.errors_handler()
async def global_error_handler(
    update,
    exception
):

    logger.error(
        f"Global bot xatosi: {exception}"
    )

    return True


# ============================================================
# STARTUP
# ============================================================

async def on_startup(
    dispatcher
):

    await init_db()

    logger.info(
        "===================================="
    )

    logger.info(
        "BOT ISHGA TUSHDI"
    )

    logger.info(
        f"Database: {DB_PATH}"
    )

    logger.info(
        f"Admin ID: {ADMIN_ID}"
    )

    logger.info(
        "===================================="
    )


# ============================================================
# BOTNI ISHGA TUSHIRISH
# ============================================================

if __name__ == "__main__":

    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup
    )
