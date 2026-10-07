# -*- coding: utf-8 -*-
import logging
import os
import asyncio
import aiosqlite
from datetime import datetime

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

API_TOKEN = os.environ.get('API_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '1151233619'))

DB_PATH = os.environ.get('DB_PATH', 'bot.db')

# Kanal
CHANNEL_ID = -1003800297556
CHANNEL_INVITE_LINK = "https://t.me/kunlikishchiroqchi"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Online foydalanuvchilar
MEN_ONLINE_DB = set()
WOMEN_ONLINE_DB = set()


# ============================================================
# SANA
# ============================================================

def current_date():
    return datetime.now().strftime("%d.%m.%Y")


def current_datetime():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


# ============================================================
# MA'LUMOTLAR BAZASI
# ============================================================

async def ensure_column(db, table_name, column_name, column_type):
    """
    Jadvalda ustun bo'lmasa avtomatik qo'shadi.
    Eski ma'lumotlarni buzmaydi.
    """
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    columns = await cursor.fetchall()

    column_names = [row[1] for row in columns]

    if column_name not in column_names:
        await db.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )

        # Eski yozuvlarga hozirgi sanani beradi
        await db.execute(
            f"UPDATE {table_name} SET {column_name}=? WHERE {column_name} IS NULL",
            (current_datetime(),)
        )


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:

        # Umumiy e'lonlar
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                phone TEXT
            )
        ''')

        # Ayollar e'lonlari
        await db.execute('''
            CREATE TABLE IF NOT EXISTS women_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                phone TEXT
            )
        ''')

        # Ustalar
        await db.execute('''
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                full_name TEXT,
                phone TEXT,
                description TEXT
            )
        ''')

        # Foydalanuvchilar
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT
            )
        ''')

        # ====================================================
        # YUK MASHINALARI EGALARI
        # ====================================================

        await db.execute('''
            CREATE TABLE IF NOT EXISTS truck_owners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                truck_type TEXT,
                phone TEXT,
                description TEXT,
                created_at TEXT
            )
        ''')

        # ====================================================
        # YUK MASHINASI KERAK E'LONLARI
        # ====================================================

        await db.execute('''
            CREATE TABLE IF NOT EXISTS truck_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                truck_type TEXT,
                text TEXT,
                phone TEXT,
                created_at TEXT
            )
        ''')

        # ====================================================
        # ESKI JADVALLARGA SANA QO'SHISH
        # ====================================================

        await ensure_column(
            db,
            'ads',
            'created_at',
            'TEXT'
        )

        await ensure_column(
            db,
            'women_ads',
            'created_at',
            'TEXT'
        )

        await ensure_column(
            db,
            'masters',
            'created_at',
            'TEXT'
        )

        await db.commit()

    logging.info(f"Ma'lumotlar bazasi tayyor: {DB_PATH}")


# ============================================================
# USERLAR
# ============================================================

async def register_user(user_id, full_name, username):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users
            (user_id, full_name, username)
            VALUES (?, ?, ?)
            """,
            (user_id, full_name, username)
        )
        await db.commit()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0


# ============================================================
# UMUMIY E'LONLAR
# ============================================================

async def add_ad(user_id, user_name, text, phone):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO ads
            (user_id, user_name, text, phone, created_at)
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


async def get_all_ads():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, user_name, text, phone, created_at
            FROM ads
            ORDER BY id DESC
            """
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'text': r[3],
                'phone': r[4],
                'created_at': r[5]
            }
            for r in rows
        ]


async def get_user_ads(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, user_name, text, phone, created_at
            FROM ads
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (user_id,)
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'text': r[3],
                'phone': r[4],
                'created_at': r[5]
            }
            for r in rows
        ]


async def delete_ad(ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM ads WHERE id=?",
            (ad_id,)
        )
        await db.commit()


# ============================================================
# AYOLLAR E'LONLARI
# ============================================================

async def add_women_ad(user_id, user_name, text, phone):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO women_ads
            (user_id, user_name, text, phone, created_at)
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


async def get_all_women_ads():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, user_name, text, phone, created_at
            FROM women_ads
            ORDER BY id DESC
            """
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'text': r[3],
                'phone': r[4],
                'created_at': r[5]
            }
            for r in rows
        ]


async def get_user_women_ads(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, user_name, text, phone, created_at
            FROM women_ads
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (user_id,)
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'text': r[3],
                'phone': r[4],
                'created_at': r[5]
            }
            for r in rows
        ]


async def delete_women_ad(ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM women_ads WHERE id=?",
            (ad_id,)
        )
        await db.commit()


# ============================================================
# USTALAR
# ============================================================

async def add_master(category, full_name, phone, description):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO masters
            (category, full_name, phone, description, created_at)
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


async def get_masters_by_category(category):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, category, full_name, phone,
                   description, created_at
            FROM masters
            WHERE LOWER(category) LIKE ?
            ORDER BY id DESC
            """,
            (f"%{category.lower()}%",)
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'category': r[1],
                'full_name': r[2],
                'phone': r[3],
                'description': r[4],
                'created_at': r[5]
            }
            for r in rows
        ]


# ============================================================
# YUK MASHINALARI
# ============================================================

async def add_truck_owner(
    user_id,
    user_name,
    truck_type,
    phone,
    description
):
    async with aiosqlite.connect(DB_PATH) as db:
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


async def get_truck_owners(truck_type):
    async with aiosqlite.connect(DB_PATH) as db:
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
            (truck_type,)
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'truck_type': r[3],
                'phone': r[4],
                'description': r[5],
                'created_at': r[6]
            }
            for r in rows
        ]


async def get_user_truck_owners(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
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
            (user_id,)
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'truck_type': r[3],
                'phone': r[4],
                'description': r[5],
                'created_at': r[6]
            }
            for r in rows
        ]


async def delete_truck_owner(owner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM truck_owners WHERE id=?",
            (owner_id,)
        )
        await db.commit()


async def add_truck_request(
    user_id,
    user_name,
    truck_type,
    text,
    phone
):
    async with aiosqlite.connect(DB_PATH) as db:
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


async def get_user_truck_requests(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
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
            (user_id,)
        )

        rows = await cursor.fetchall()

        return [
            {
                'id': r[0],
                'user_id': r[1],
                'user_name': r[2],
                'truck_type': r[3],
                'text': r[4],
                'phone': r[5],
                'created_at': r[6]
            }
            for r in rows
        ]


async def delete_truck_request(request_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM truck_requests WHERE id=?",
            (request_id,)
        )
        await db.commit()


async def get_truck_requests_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM truck_requests"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_truck_owners_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM truck_owners"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ============================================================
# KLAVIATURALAR
# ============================================================

def main_menu():
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=2
    )

    kb.add(
        KeyboardButton('👨‍💻 Erkaklar online'),
        KeyboardButton('👩‍💻 Ayollar online'),
        KeyboardButton('🔕 Xabarlarni to\'xtatish'),
        KeyboardButton('🔍 Ish topish'),
        KeyboardButton('📢 E\'lon berish'),
        KeyboardButton('🗑 Mening e\'lonlarim'),
        KeyboardButton('👷‍♂️ Ustalar xizmati'),
        KeyboardButton('🚚 Yuk mashinalar'),
        KeyboardButton('🧵 Ayollar bo\'limi'),
        KeyboardButton('ℹ️ Ma\'lumot')
    )

    return kb


def masters_menu():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            '🏗 Qurilish ustalari',
            callback_data='master_build'
        ),
        InlineKeyboardButton(
            '🔌 Elektrik va Santexnik',
            callback_data='master_electric'
        ),
        InlineKeyboardButton(
            '🪚 Duradgor va Payvandchi',
            callback_data='master_welder'
        ),
        InlineKeyboardButton(
            '🎨 Malyar va Oboichi',
            callback_data='master_finish'
        ),
        InlineKeyboardButton(
            '🚗 Avto servis',
            callback_data='master_auto'
        ),
        InlineKeyboardButton(
            '🪟 Akfa romlar',
            callback_data='master_akfa'
        ),
        InlineKeyboardButton(
            '🛋 Mebelchi',
            callback_data='master_mebel'
        ),
        InlineKeyboardButton(
            '➕ O\'z xizmatimni qo\'shish',
            callback_data='add_master'
        )
    )

    return kb


def women_menu():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            '🔍 Ish topish (Ayollar bo\'limi)',
            callback_data='women_find'
        ),
        InlineKeyboardButton(
            '📢 E\'lon berish (Ayollar bo\'limi)',
            callback_data='women_post'
        )
    )

    return kb


def categories_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            '🏗 Qurilish ustalari',
            callback_data='cat_Qurilish ustalari'
        ),
        InlineKeyboardButton(
            '🔌 Elektrik va Santexnik',
            callback_data='cat_Elektrik va Santexnik'
        ),
        InlineKeyboardButton(
            '🪚 Duradgor va Payvandchi',
            callback_data='cat_Duradgor va Payvandchi'
        ),
        InlineKeyboardButton(
            '🎨 Malyar va Oboichi',
            callback_data='cat_Malyar va Oboichi'
        ),
        InlineKeyboardButton(
            '🚗 Avto servis',
            callback_data='cat_Avto servis'
        ),
        InlineKeyboardButton(
            '🪟 Akfa romlar',
            callback_data='cat_Akfa romlar'
        ),
        InlineKeyboardButton(
            '🛋 Mebelchi',
            callback_data='cat_Mebelchi'
        )
    )

    return kb


# ============================================================
# YUK MASHINALARI MENYULARI
# ============================================================

def trucks_menu():
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            '🔎 Yuk mashinasi kerak',
            callback_data='truck_need'
        ),
        InlineKeyboardButton(
            '🚛 Yuk mashinasi bor, xizmat ko\'rsataman',
            callback_data='truck_have'
        )
    )

    return kb


def truck_type_keyboard(action):
    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton(
            '🚚 Kichik yuk mashinasi',
            callback_data=f'truck_{action}_small'
        ),
        InlineKeyboardButton(
            '🚛 Katta yuk mashinasi',
            callback_data=f'truck_{action}_large'
        )
    )

    return kb


# ============================================================
# STATE LAR
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

async def check_sub_channel(user_id):
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        if member.status in [
            'creator',
            'administrator',
            'member'
        ]:
            return True

        return False

    except Exception as e:
        print(f"Obunani tekshirishda xatolik: {e}")
        return False


# ============================================================
# START
# ============================================================

@dp.message_handler(
    commands=['start', 'help'],
    state='*'
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

    is_subscribed = await check_sub_channel(user_id)

    if not is_subscribed:

        keyboard = InlineKeyboardMarkup(row_width=1)

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
            "⚠️ Botimizdan foydalanish uchun avval "
            "quyidagi kanalimizga a'zo bo'ling va "
            "so'ng 'Tekshirish' tugmasini bosing:",
            reply_markup=keyboard
        )

        return

    await message.answer(
        "Chiroqchi tumanida ish topish yoki ish berish "
        "botiga xush kelibsiz! 👋\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_menu()
    )


# ============================================================
# OBUNANI TEKSHIRISH
# ============================================================

@dp.callback_query_handler(text="check_sub")
async def process_check_sub(
    callback: types.CallbackQuery
):

    user_id = callback.from_user.id

    is_subscribed = await check_sub_channel(user_id)

    if is_subscribed:

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "Rahmat! Obuna tasdiqlandi. "
            "Kerakli bo'limni tanlang:",
            reply_markup=main_menu()
        )

    else:

        await callback.answer(
            "Siz hali kanalga a'zo bo'lmadingiz!",
            show_alert=True
        )


# ============================================================
# ADMIN
# ============================================================

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "Sizda bu bo'limga kirish huquqi yo'q."
        )
        return

    await message.answer(
        "🛠 <b>Admin panel: Barcha e'lonlarni boshqarish</b>",
        parse_mode='HTML'
    )

    ads = await get_all_ads()
    women_ads = await get_all_women_ads()

    if not ads and not women_ads:
        await message.answer(
            "Hozircha botda hech qanday e'lon mavjud emas."
        )
        return

    for ad in ads:

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                '❌ E\'lonni o\'chirish (Admin)',
                callback_data=f"adm_gen_{ad['id']}"
            )
        )

        await message.answer(
            f"<b>[Umumiy] #{ad['id']}</b>\n"
            f"Muallif: {ad['user_name']}\n"
            f"{ad['text']}\n"
            f"📞 {ad['phone']}\n"
            f"📅 {ad['created_at']}",
            reply_markup=kb,
            parse_mode='HTML'
        )

    for ad in women_ads:

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                '❌ E\'lonni o\'chirish (Admin)',
                callback_data=f"adm_women_{ad['id']}"
            )
        )

        await message.answer(
            f"<b>[Ayollar] #{ad['id']}</b>\n"
            f"Muallif: {ad['user_name']}\n"
            f"{ad['text']}\n"
            f"📞 {ad['phone']}\n"
            f"📅 {ad['created_at']}",
            reply_markup=kb,
            parse_mode='HTML'
        )


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith('adm_')
)
async def admin_delete_callback(
    callback_query: types.CallbackQuery
):

    if callback_query.from_user.id != ADMIN_ID:

        await bot.answer_callback_query(
            callback_query.id,
            "Siz admin emassiz!",
            show_alert=True
        )

        return

    await bot.answer_callback_query(
        callback_query.id
    )

    parts = callback_query.data.split('_')

    ad_type = parts[1]
    ad_id = int(parts[2])

    try:

        if ad_type == 'gen':
            await delete_ad(ad_id)

        elif ad_type == 'women':
            await delete_women_ad(ad_id)

        await callback_query.message.edit_text(
            "✅ E'lon admin tomonidan o'chirildi!"
        )

    except Exception:

        await callback_query.message.edit_text(
            "⚠️ Bu e'lon allaqachon o'chirilgan."
        )


# ============================================================
# STATISTIKA
# ============================================================

@dp.message_handler(commands=['statistika'])
async def show_statistics(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "Sizda bu buyruqdan foydalanish huquqi yo'q."
        )
        return

    users_count = await get_users_count()
    ads = await get_all_ads()
    women_ads = await get_all_women_ads()

    truck_owners = await get_truck_owners_count()
    truck_requests = await get_truck_requests_count()

    await message.answer(
        f"📊 <b>Bot statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: {users_count}\n"
        f"📢 Faol umumiy e'lonlar: {len(ads)}\n"
        f"🧵 Faol ayollar bo'limi e'lonlari: {len(women_ads)}\n"
        f"🚛 Yuk mashinasi egalari: {truck_owners}\n"
        f"🔎 Yuk mashinasi kerak e'lonlari: {truck_requests}",
        parse_mode='HTML'
    )


# ============================================================
# BARCHAGA XABAR
# ============================================================

@dp.message_handler(commands=['xabar'])
async def broadcast_start(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "Sizda bu buyruqdan foydalanish huquqi yo'q."
        )
        return

    count = await get_users_count()

    await message.answer(
        f"👥 Botda jami {count} ta foydalanuvchi "
        f"ro'yxatga olingan.\n\n"
        f"Barchaga yubormoqchi bo'lgan xabar "
        f"matnini kiriting:"
    )

    await BroadcastState.text.set()


@dp.message_handler(state=BroadcastState.text)
async def broadcast_preview(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:
        data['text'] = message.text

    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton(
            '✅ Ha, yuborish',
            callback_data='broadcast_confirm'
        ),
        InlineKeyboardButton(
            '❌ Bekor qilish',
            callback_data='broadcast_cancel'
        )
    )

    await message.answer(
        f"<b>Xabar shunday ko'rinadi:</b>\n\n"
        f"{message.text}\n\n"
        f"Yuborishni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode='HTML'
    )

    await BroadcastState.confirm.set()


@dp.callback_query_handler(
    text='broadcast_cancel',
    state=BroadcastState.confirm
)
async def broadcast_cancel(
    callback_query: types.CallbackQuery,
    state: FSMContext
):

    await bot.answer_callback_query(
        callback_query.id
    )

    await callback_query.message.edit_text(
        "❌ Xabar yuborish bekor qilindi."
    )

    await state.finish()


@dp.callback_query_handler(
    text='broadcast_confirm',
    state=BroadcastState.confirm
)
async def broadcast_confirm(
    callback_query: types.CallbackQuery,
    state: FSMContext
):

    await bot.answer_callback_query(
        callback_query.id
    )

    async with state.proxy() as data:
        text = data['text']

    await state.finish()

    await callback_query.message.edit_text(
        "⏳ Xabar yuborilmoqda, biroz kuting..."
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

        except Exception:
            failed += 1

        await asyncio.sleep(0.05)

    await bot.send_message(
        callback_query.from_user.id,
        f"✅ Xabar yuborish tugadi!\n\n"
        f"📨 Yuborildi: {success} ta\n"
        f"🚫 Yuborilmadi: {failed} ta"
    )


# ============================================================
# ONLINE
# ============================================================

@dp.message_handler(text='👨‍💻 Erkaklar online')
async def men_online_section(
    message: types.Message
):

    MEN_ONLINE_DB.add(
        message.from_user.id
    )

    if message.from_user.id in WOMEN_ONLINE_DB:
        WOMEN_ONLINE_DB.remove(
            message.from_user.id
        )

    await message.answer(
        '✅ Siz "Erkaklar online" bo\'limiga ulandingiz!',
        reply_markup=main_menu()
    )


@dp.message_handler(text='👩‍💻 Ayollar online')
async def women_online_section(
    message: types.Message
):

    WOMEN_ONLINE_DB.add(
        message.from_user.id
    )

    if message.from_user.id in MEN_ONLINE_DB:
        MEN_ONLINE_DB.remove(
            message.from_user.id
        )

    await message.answer(
        '✅ Siz "Ayollar online" bo\'limiga ulandingiz!',
        reply_markup=main_menu()
    )


@dp.message_handler(text='🔕 Xabarlarni to\'xtatish')
async def stop_notifications(
    message: types.Message
):

    user_id = message.from_user.id
    removed = False

    if user_id in MEN_ONLINE_DB:
        MEN_ONLINE_DB.remove(user_id)
        removed = True

    if user_id in WOMEN_ONLINE_DB:
        WOMEN_ONLINE_DB.remove(user_id)
        removed = True

    if removed:

        await message.answer(
            "🔕 Barcha avtomatik xabarlar to'xtatildi.",
            reply_markup=main_menu()
        )

    else:

        await message.answer(
            "Siz allaqachon bildirishnomalarni "
            "o'chirgansiz.",
            reply_markup=main_menu()
        )


# ============================================================
# USTALAR
# ============================================================

@dp.message_handler(text='👷‍♂️ Ustalar xizmati')
async def show_masters(
    message: types.Message
):

    await message.answer(
        "Kerakli mutaxassislik turini tanlang "
        "yoki o'z xizmatingizni qo'shing:",
        reply_markup=masters_menu()
    )


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith('master_')
)
async def process_master_category(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    cat_code = callback_query.data.split('_')[1]

    cat_names = {
        'build': 'Qurilish ustalari',
        'electric': 'Elektrik va Santexnik',
        'welder': 'Duradgor va Payvandchi',
        'finish': 'Malyar va Oboichi',
        'auto': 'Avto servis',
        'akfa': 'Akfa romlar',
        'mebel': 'Mebelchi'
    }

    target_cat = cat_names.get(
        cat_code,
        ''
    )

    filtered = await get_masters_by_category(
        target_cat
    )

    if not filtered:

        text = (
            f"<b>{target_cat}</b> yo'nalishi "
            f"bo'yicha hozircha ustalar yo'q."
        )

    else:

        text = (
            f"<b>{target_cat}</b> yo'nalishi "
            f"bo'yicha ustalar:\n\n"
        )

        for idx, m in enumerate(
            filtered,
            1
        ):

            text += (
                f"{idx}. <b>{m['category']}</b>\n"
                f"👤 {m['full_name']}\n"
                f"📞 {m['phone']}\n"
                f"📝 {m['description']}\n"
                f"📅 {m['created_at']}\n"
                f"-----\n"
            )

    await bot.send_message(
        callback_query.from_user.id,
        text,
        parse_mode='HTML'
    )


# ============================================================
# USTA QO'SHISH
# ============================================================

@dp.callback_query_handler(
    text='add_master'
)
async def add_master_start(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    await callback_query.message.answer(
        "Yo'nalishni tanlang:",
        reply_markup=categories_keyboard()
    )

    await MasterState.category.set()


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith('cat_'),
    state=MasterState.category
)
async def process_category_choice(
    callback_query: types.CallbackQuery,
    state: FSMContext
):

    await bot.answer_callback_query(
        callback_query.id
    )

    selected_category = callback_query.data.split(
        '_',
        1
    )[1]

    async with state.proxy() as data:
        data['category'] = selected_category

    await callback_query.message.answer(
        "Ism va familiyangizni kiriting:"
    )

    await MasterState.next()


@dp.message_handler(
    state=MasterState.full_name
)
async def process_name(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:
        data['full_name'] = message.text

    await message.answer(
        "Telefon raqamingizni kiriting "
        "(masalan: +998901234567):"
    )

    await MasterState.next()


@dp.message_handler(
    state=MasterState.phone
)
async def process_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:
        data['phone'] = message.text

    await message.answer(
        "Qisqacha tajribangiz yoki "
        "xizmatingiz haqida yozing:"
    )

    await MasterState.next()


@dp.message_handler(
    state=MasterState.description
)
async def process_description(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:

        category = data['category']
        full_name = data['full_name']
        phone = data['phone']

    await add_master(
        category,
        full_name,
        phone,
        message.text
    )

    await message.answer(
        "✅ Xizmatingiz muvaffaqiyatli saqlandi!\n"
        f"📅 Sana: {current_date()}",
        reply_markup=main_menu()
    )

    await state.finish()


# ============================================================
# AYOLLAR BO'LIMI
# ============================================================

@dp.message_handler(text='🧵 Ayollar bo\'limi')
async def show_women_section(
    message: types.Message
):

    await message.answer(
        "🧵 <b>Ayollar bo'limi</b>\n\n"
        "Tikuvchilik, pazandachilik, uy xo'jaligi "
        "va boshqa xizmatlar.\n\n"
        "Kerakli tugmani tanlang:",
        reply_markup=women_menu(),
        parse_mode='HTML'
    )


@dp.callback_query_handler(
    text='women_find'
)
async def process_women_find(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    women_ads = await get_all_women_ads()

    if not women_ads:

        text = (
            "<b>Hozircha Ayollar bo'limida "
            "e'lonlar yo'q.</b>"
        )

    else:

        text = (
            "<b>🧵 Ayollar bo'limidagi "
            "mavjud e'lonlar:</b>\n\n"
        )

        for idx, ad in enumerate(
            women_ads,
            1
        ):

            text += (
                f"{idx}. {ad['text']}\n"
                f"👤 <b>Muallif:</b> "
                f"{ad['user_name']}\n"
                f"📞 <b>Tel:</b> "
                f"{ad['phone']}\n"
                f"📅 <b>Sana:</b> "
                f"{ad['created_at']}\n"
                f"-----\n"
            )

    await bot.send_message(
        callback_query.from_user.id,
        text,
        parse_mode='HTML'
    )


@dp.callback_query_handler(
    text='women_post'
)
async def process_women_post(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    await callback_query.message.answer(
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
        data['text'] = message.text

    await message.answer(
        "Aloqa uchun telefon raqamingizni "
        "kiriting (masalan: +998901234567):"
    )

    await WomenAdState.next()


@dp.message_handler(
    state=WomenAdState.phone
)
async def process_women_ad_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:
        ad_text = data['text']

    await add_women_ad(
        message.from_user.id,
        message.from_user.full_name,
        ad_text,
        message.text
    )

    ad_message = (
        "<b>🧵 AYOLLAR ONLINE - YANGI E'LON!</b>\n\n"
        f"{ad_text}\n"
        f"👤 <b>Muallif:</b> "
        f"{message.from_user.full_name}\n"
        f"📞 <b>Tel:</b> {message.text}\n"
        f"📅 <b>Sana:</b> {current_datetime()}"
    )

    for user_id in WOMEN_ONLINE_DB:

        try:
            await bot.send_message(
                user_id,
                ad_message,
                parse_mode='HTML'
            )

        except Exception:
            pass

    await message.answer(
        "✅ E'loningiz Ayollar bo'limiga qo'shildi!",
        reply_markup=main_menu()
    )

    await state.finish()


# ============================================================
# UMUMIY ISH TOPISH
# ============================================================

@dp.message_handler(text='🔍 Ish topish')
async def find_work(
    message: types.Message
):

    ads = await get_all_ads()

    if not ads:

        await message.answer(
            "Hozircha umumiy faol e'lonlar yo'q."
        )

    else:

        text = (
            "<b>📋 Mavjud umumiy e'lonlar va ishlar:</b>\n\n"
        )

        for idx, ad in enumerate(
            ads,
            1
        ):

            text += (
                f"{idx}. {ad['text']}\n"
                f"👤 <b>Muallif:</b> "
                f"{ad['user_name']}\n"
                f"📞 <b>Tel:</b> {ad['phone']}\n"
                f"📅 <b>Sana:</b> "
                f"{ad['created_at']}\n"
                f"-----\n"
            )

        await message.answer(
            text,
            parse_mode='HTML'
        )


# ============================================================
# UMUMIY E'LON BERISH
# ============================================================

@dp.message_handler(text='📢 E\'lon berish')
async def post_ad_start(
    message: types.Message
):

    await message.answer(
        "E'lon matnini kiriting "
        "(ish turi, manzil va talablar):"
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
        data['text'] = message.text

    await message.answer(
        "Aloqa uchun telefon raqamingizni "
        "kiriting (masalan: +998901234567):"
    )

    await AdState.next()


@dp.message_handler(
    state=AdState.phone
)
async def process_ad_phone(
    message: types.Message,
    state: FSMContext
):

    async with state.proxy() as data:
        ad_text = data['text']

    await add_ad(
        message.from_user.id,
        message.from_user.full_name,
        ad_text,
        message.text
    )

    ad_message = (
        "<b>📢 ERKAKLAR BO'LIMI - YANGI E'LON!</b>\n\n"
        f"{ad_text}\n"
        f"👤 <b>Muallif:</b> "
        f"{message.from_user.full_name}\n"
        f"📞 <b>Tel:</b> {message.text}\n"
        f"📅 <b>Sana:</b> {current_datetime()}"
    )

    for user_id in MEN_ONLINE_DB:

        try:
            await bot.send_message(
                user_id,
                ad_message,
                parse_mode='HTML'
            )

        except Exception:
            pass

    await message.answer(
        "✅ E'loningiz qabul qilindi va tarqatildi!",
        reply_markup=main_menu()
    )

    await state.finish()


# ============================================================
# YUK MASHINALAR BO'LIMI
# ============================================================

@dp.message_handler(text='🚚 Yuk mashinalar')
async def truck_main_menu(
    message: types.Message
):

    await message.answer(
        "🚚 <b>Yuk mashinalar bo'limi</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=trucks_menu(),
        parse_mode='HTML'
    )


# ============================================================
# YUK MASHINASI KERAK
# ============================================================

@dp.callback_query_handler(
    text='truck_need'
)
async def truck_need_start(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    await callback_query.message.answer(
        "🔎 Qanday yuk mashinasi kerak?",
        reply_markup=truck_type_keyboard('need')
    )

    await TruckRequestState.truck_type.set()


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith('truck_need_'),
    state=TruckRequestState.truck_type
)
async def truck_need_type(
    callback_query: types.CallbackQuery,
    state: FSMContext
):

    await bot.answer_callback_query(
        callback_query.id
    )

    truck_code = callback_query.data.split('_')[-1]

    if truck_code == 'small':
        truck_type = 'Kichik yuk mashinasi'
    else:
        truck_type = 'Katta yuk mashinasi'

    async with state.proxy() as data:
        data['truck_type'] = truck_type

    await callback_query.message.answer(
        f"🚚 <b>{truck_type}</b>\n\n"
        "Qayerdan qayerga yuk olib borish kerakligini "
        "va boshqa kerakli ma'lumotlarni yozing:",
        parse_mode='HTML'
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
        data['text'] = message.text

    await message.answer(
        "📞 Aloqa uchun telefon raqamingizni kiriting:"
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

        truck_type = data['truck_type']
        truck_text = data['text']

    await add_truck_request(
        message.from_user.id,
        message.from_user.full_name,
        truck_type,
        truck_text,
        message.text
    )

    # ========================================================
    # FAQAT SHU TURDAGI MASHINA EGALARIGA XABAR
    # ========================================================

    owners = await get_truck_owners(
        truck_type
    )

    notification = (
        "🚨 <b>YANGI YUK BUYURTMASI!</b>\n\n"
        f"🚛 <b>Mashina turi:</b> {truck_type}\n\n"
        f"📝 <b>Buyurtma:</b>\n"
        f"{truck_text}\n\n"
        f"👤 <b>Mijoz:</b> "
        f"{message.from_user.full_name}\n"
        f"📞 <b>Telefon:</b> {message.text}\n"
        f"📅 <b>Sana:</b> {current_datetime()}\n\n"
        f"⚡ <i>Bu xabar siz {truck_type.lower()} "
        f"egasi sifatida ro'yxatdan o'tganingiz uchun yuborildi.</i>"
    )

    sent_count = 0

    for owner in owners:

        try:

            await bot.send_message(
                owner['user_id'],
                notification,
                parse_mode='HTML'
            )

            sent_count += 1

        except Exception:
            pass

    await message.answer(
        "✅ Yuk mashinasi kerakligi haqidagi "
        "e'loningiz qabul qilindi!\n\n"
        f"🚛 Mashina turi: {truck_type}\n"
        f"📅 Sana: {current_datetime()}\n\n"
        f"📨 Hozirda {sent_count} ta "
        f"{truck_type.lower()} egasiga xabar yuborildi.",
        reply_markup=main_menu()
    )

    await state.finish()


# ============================================================
# YUK MASHINASI BOR
# ============================================================

@dp.callback_query_handler(
    text='truck_have'
)
async def truck_have_start(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    await callback_query.message.answer(
        "🚛 Qaysi turdagi yuk mashinangiz bor?",
        reply_markup=truck_type_keyboard('have')
    )

    await TruckOwnerState.truck_type.set()


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith('truck_have_'),
    state=TruckOwnerState.truck_type
)
async def truck_have_type(
    callback_query: types.CallbackQuery,
    state: FSMContext
):

    await bot.answer_callback_query(
        callback_query.id
    )

    truck_code = callback_query.data.split('_')[-1]

    if truck_code == 'small':
        truck_type = 'Kichik yuk mashinasi'
    else:
        truck_type = 'Katta yuk mashinasi'

    async with state.proxy() as data:
        data['truck_type'] = truck_type

    await callback_query.message.answer(
        f"🚛 <b>{truck_type}</b>\n\n"
        "Mashina va ko'rsatadigan xizmatingiz "
        "haqida qisqacha ma'lumot yozing:",
        parse_mode='HTML'
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
        data['description'] = message.text

    await message.answer(
        "📞 Aloqa uchun telefon raqamingizni kiriting:"
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

        truck_type = data['truck_type']
        description = data['description']

    await add_truck_owner(
        message.from_user.id,
        message.from_user.full_name,
        truck_type,
        message.text,
        description
    )

    await message.answer(
        "✅ Siz yuk mashinasi egasi sifatida "
        "muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"🚛 Turi: {truck_type}\n"
        f"📞 Telefon: {message.text}\n"
        f"📅 Sana: {current_datetime()}\n\n"
        "Endi shu turdagi yuk mashinasi kerak "
        "bo'lganida sizga avtomatik xabar keladi.",
        reply_markup=main_menu()
    )

    await state.finish()


# ============================================================
# MENING E'LONLARIM
# ============================================================

@dp.message_handler(text='🗑 Mening e\'lonlarim')
async def my_ads(
    message: types.Message
):

    user_id = message.from_user.id

    user_ads = await get_user_ads(user_id)
    user_women_ads = await get_user_women_ads(user_id)

    user_truck_owners = await get_user_truck_owners(
        user_id
    )

    user_truck_requests = await get_user_truck_requests(
        user_id
    )

    if (
        not user_ads
        and not user_women_ads
        and not user_truck_owners
        and not user_truck_requests
    ):

        await message.answer(
            "Sizda hozircha faol e'lonlar yo'q."
        )

        return

    await message.answer(
        "<b>🗑 Sizning e'lonlaringiz:</b>",
        parse_mode='HTML'
    )

    # Umumiy
    for idx, ad in enumerate(
        user_ads,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ E'lonni o'chirish",
                callback_data=f"del_gen_{ad['id']}"
            )
        )

        await message.answer(
            f"<b>📢 Umumiy e'lon #{idx}</b>\n"
            f"{ad['text']}\n"
            f"📞 {ad['phone']}\n"
            f"📅 {ad['created_at']}",
            reply_markup=kb,
            parse_mode='HTML'
        )

    # Ayollar
    for idx, ad in enumerate(
        user_women_ads,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ E'lonni o'chirish",
                callback_data=f"del_women_{ad['id']}"
            )
        )

        await message.answer(
            f"<b>🧵 Ayollar e'loni #{idx}</b>\n"
            f"{ad['text']}\n"
            f"📞 {ad['phone']}\n"
            f"📅 {ad['created_at']}",
            reply_markup=kb,
            parse_mode='HTML'
        )

    # Yuk mashinasi egasi
    for idx, owner in enumerate(
        user_truck_owners,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ Xizmat e'lonini o'chirish",
                callback_data=f"del_truck_owner_{owner['id']}"
            )
        )

        await message.answer(
            f"<b>🚛 Yuk mashinasi xizmati #{idx}</b>\n"
            f"🚚 {owner['truck_type']}\n"
            f"📝 {owner['description']}\n"
            f"📞 {owner['phone']}\n"
            f"📅 {owner['created_at']}",
            reply_markup=kb,
            parse_mode='HTML'
        )

    # Yuk mashinasi kerak
    for idx, req in enumerate(
        user_truck_requests,
        1
    ):

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "❌ Buyurtmani o'chirish",
                callback_data=f"del_truck_request_{req['id']}"
            )
        )

        await message.answer(
            f"<b>🔎 Yuk mashinasi kerak #{idx}</b>\n"
            f"🚛 {req['truck_type']}\n"
            f"📝 {req['text']}\n"
            f"📞 {req['phone']}\n"
            f"📅 {req['created_at']}",
            reply_markup=kb,
            parse_mode='HTML'
        )


# ============================================================
# E'LON O'CHIRISH
# ============================================================

@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith('del_')
)
async def delete_ad_callback(
    callback_query: types.CallbackQuery
):

    await bot.answer_callback_query(
        callback_query.id
    )

    parts = callback_query.data.split('_')

    try:

        # Umumiy
        if parts[1] == 'gen':

            ad_id = int(parts[2])

            await delete_ad(ad_id)

        # Ayollar
        elif parts[1] == 'women':

            ad_id = int(parts[2])

            await delete_women_ad(ad_id)

        # Yuk egasi
        elif (
            parts[1] == 'truck'
            and parts[2] == 'owner'
        ):

            owner_id = int(parts[3])

            await delete_truck_owner(
                owner_id
            )

        # Yuk buyurtma
        elif (
            parts[1] == 'truck'
            and parts[2] == 'request'
        ):

            request_id = int(parts[3])

            await delete_truck_request(
                request_id
            )

        await callback_query.message.edit_text(
            "✅ E'lon muvaffaqiyatli o'chirildi!"
        )

    except Exception:

        await callback_query.message.edit_text(
            "⚠️ Bu e'lon allaqachon o'chirilgan."
        )


# ============================================================
# INFO
# ============================================================

@dp.message_handler(text='ℹ️ Ma\'lumot')
async def info_text(
    message: types.Message
):

    await message.answer(
        "Chiroqchi tumanida tezkor ish topish boti:\n\n"
        "🤖 @KunlikIsh_chiroqchi_bot\n\n"
        "🚚 Yuk mashinalari bo'limida "
        "mashina egalariga buyurtmalar avtomatik "
        "yuboriladi."
    )


# ============================================================
# STARTUP
# ============================================================

async def on_startup(dispatcher):
    await init_db()


# ============================================================
# BOTNI ISHGA TUSHIRISH
# ============================================================

if __name__ == '__main__':

    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup
    )
