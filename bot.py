# -*- coding: utf-8 -*-
import logging
import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = os.environ.get('API_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '1151233619'))  # O'zingizning Telegram ID raqamingiz

# Ma'lumotlar bazasi fayli. Render'da Persistent Disk ulangan bo'lsa,
# DB_PATH environment variable orqali doimiy joyni ko'rsating (masalan /var/data/bot.db)
DB_PATH = os.environ.get('DB_PATH', 'bot.db')

# Kanal ma'lumotlari (Majburiy obuna uchun)
CHANNEL_ID = -1003800297556
CHANNEL_INVITE_LINK = "https://t.me/kunlikishchiroqchi"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Online holat hozircha xotirada qoladi (bu doimiy saqlanishi shart emas)
MEN_ONLINE_DB = set()
WOMEN_ONLINE_DB = set()


# ============== MA'LUMOTLAR BAZASI FUNKSIYALARI ==============

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                phone TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS women_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                text TEXT,
                phone TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                full_name TEXT,
                phone TEXT,
                description TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT
            )
        ''')
        await db.commit()
    logging.info(f"Ma'lumotlar bazasi tayyor: {DB_PATH}")


async def register_user(user_id, full_name, username):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
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


async def add_ad(user_id, user_name, text, phone):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ads (user_id, user_name, text, phone) VALUES (?, ?, ?, ?)",
            (user_id, user_name, text, phone)
        )
        await db.commit()


async def get_all_ads():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, user_id, user_name, text, phone FROM ads")
        rows = await cursor.fetchall()
        return [{'id': r[0], 'user_id': r[1], 'user_name': r[2], 'text': r[3], 'phone': r[4]} for r in rows]


async def get_user_ads(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, user_id, user_name, text, phone FROM ads WHERE user_id=?", (user_id,))
        rows = await cursor.fetchall()
        return [{'id': r[0], 'user_id': r[1], 'user_name': r[2], 'text': r[3], 'phone': r[4]} for r in rows]


async def delete_ad(ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ads WHERE id=?", (ad_id,))
        await db.commit()


async def add_women_ad(user_id, user_name, text, phone):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO women_ads (user_id, user_name, text, phone) VALUES (?, ?, ?, ?)",
            (user_id, user_name, text, phone)
        )
        await db.commit()


async def get_all_women_ads():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, user_id, user_name, text, phone FROM women_ads")
        rows = await cursor.fetchall()
        return [{'id': r[0], 'user_id': r[1], 'user_name': r[2], 'text': r[3], 'phone': r[4]} for r in rows]


async def get_user_women_ads(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, user_id, user_name, text, phone FROM women_ads WHERE user_id=?", (user_id,))
        rows = await cursor.fetchall()
        return [{'id': r[0], 'user_id': r[1], 'user_name': r[2], 'text': r[3], 'phone': r[4]} for r in rows]


async def delete_women_ad(ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM women_ads WHERE id=?", (ad_id,))
        await db.commit()


async def add_master(category, full_name, phone, description):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO masters (category, full_name, phone, description) VALUES (?, ?, ?, ?)",
            (category, full_name, phone, description)
        )
        await db.commit()


async def get_masters_by_category(category):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, category, full_name, phone, description FROM masters WHERE LOWER(category) LIKE ?",
            (f"%{category.lower()}%",)
        )
        rows = await cursor.fetchall()
        return [{'id': r[0], 'category': r[1], 'full_name': r[2], 'phone': r[3], 'description': r[4]} for r in rows]


# ============== KLAVIATURALAR ==============

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton('👨‍💻 Erkaklar online'),
        KeyboardButton('👩‍💻 Ayollar online'),
        KeyboardButton('🔕 Xabarlarni to\'xtatish'),
        KeyboardButton('🔍 Ish topish'),
        KeyboardButton('📢 E\'lon berish'),
        KeyboardButton('🗑 Mening e\'lonlarim'),
        KeyboardButton('👷‍♂️ Ustalar xizmati'),
        KeyboardButton('🧵 Ayollar bo\'limi'),
        KeyboardButton('ℹ️ Ma\'lumot')
    )
    return kb

def masters_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('🏗 Qurilish ustalari', callback_data='master_build'),
        InlineKeyboardButton('🔌 Elektrik va Santexnik', callback_data='master_electric'),
        InlineKeyboardButton('🪚 Duradgor va Payvandchi', callback_data='master_welder'),
        InlineKeyboardButton('🎨 Malyar va Oboichi', callback_data='master_finish'),
        InlineKeyboardButton('➕ O\'z xizmatimni qo\'shish', callback_data='add_master')
    )
    return kb

def women_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('🔍 Ish topish (Ayollar bo\'limi)', callback_data='women_find'),
        InlineKeyboardButton('📢 E\'lon berish (Ayollar bo\'limi)', callback_data='women_post')
    )
    return kb

def categories_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('🏗 Qurilish ustalari', callback_data='cat_Qurilish ustalari'),
        InlineKeyboardButton('🔌 Elektrik va Santexnik', callback_data='cat_Elektrik va Santexnik'),
        InlineKeyboardButton('🪚 Duradgor va Payvandchi', callback_data='cat_Duradgor va Payvandchi'),
        InlineKeyboardButton('🎨 Malyar va Oboichi', callback_data='cat_Malyar va Oboichi')
    )
    return kb


# Majburiy obunani tekshiruvchi funksiya
async def check_sub_channel(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        print(f"Obunani tekshirishda xatolik: {e}")
        return False


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


@dp.message_handler(commands=['start', 'help'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id

    await register_user(user_id, message.from_user.full_name, message.from_user.username)

    is_subscribed = await check_sub_channel(user_id)

    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=CHANNEL_INVITE_LINK))
        keyboard.add(InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub"))

        await message.answer(
            "⚠️ Botimizdan foydalanish uchun avval quyidagi kanalimizga a'zo bo'ling va so'ng 'Tekshirish' tugmasini bosing:",
            reply_markup=keyboard
        )
        return

    await message.answer('Chiroqchi tumanida ish topish yoki ish berish botiga xush kelibsiz! 👋\n\nKerakli bo\'limni tanlang:', reply_markup=main_menu())


@dp.callback_query_handler(text="check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_sub_channel(user_id)

    if is_subscribed:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer('Rahmat! Obuna tasdiqlandi. Kerakli bo\'limni tanlang:', reply_markup=main_menu())
    else:
        await callback.answer("Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)


# --- ADMIN BUYRUG'I ---
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer('Sizda bu bo\'limga kirish huquqi yo\'q.')
        return

    await message.answer('🛠 <b>Admin panel: Barcha e\'lonlarni boshqarish</b>', parse_mode='HTML')

    ads = await get_all_ads()
    women_ads = await get_all_women_ads()

    if not ads and not women_ads:
        await message.answer('Hozircha botda hech qanday e\'lon mavjud emas.')
        return

    for ad in ads:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton('❌ E\'lonni o\'chirish (Admin)', callback_data=f"adm_gen_{ad['id']}"))
        await message.answer(f"<b>[Umumiy] #{ad['id']}</b>\nMuallif: {ad['user_name']}\n{ad['text']}\n📞 {ad['phone']}", reply_markup=kb, parse_mode='HTML')

    for ad in women_ads:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton('❌ E\'lonni o\'chirish (Admin)', callback_data=f"adm_women_{ad['id']}"))
        await message.answer(f"<b>[Ayollar] #{ad['id']}</b>\nMuallif: {ad['user_name']}\n{ad['text']}\n📞 {ad['phone']}", reply_markup=kb, parse_mode='HTML')


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('adm_'))
async def admin_delete_callback(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await bot.answer_callback_query(callback_query.id, "Siz admin emassiz!", show_alert=True)
        return

    await bot.answer_callback_query(callback_query.id)
    parts = callback_query.data.split('_')
    ad_type = parts[1]
    ad_id = int(parts[2])

    try:
        if ad_type == 'gen':
            await delete_ad(ad_id)
        elif ad_type == 'women':
            await delete_women_ad(ad_id)
        await callback_query.message.edit_text('✅ E\'lon admin tomonidan o\'chirildi!')
    except Exception:
        await callback_query.message.edit_text('⚠️ Bu e\'lon allaqachon o\'chirilgan.')


# --- STATISTIKA (faqat admin) ---
@dp.message_handler(commands=['statistika'])
async def show_statistics(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer('Sizda bu buyruqdan foydalanish huquqi yo\'q.')
        return
    users_count = await get_users_count()
    ads = await get_all_ads()
    women_ads = await get_all_women_ads()
    await message.answer(
        f"📊 <b>Bot statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: {users_count}\n"
        f"📢 Faol umumiy e'lonlar: {len(ads)}\n"
        f"🧵 Faol ayollar bo'limi e'lonlari: {len(women_ads)}",
        parse_mode='HTML'
    )


# --- BARCHA FOYDALANUVCHILARGA XABAR YUBORISH (faqat admin) ---
@dp.message_handler(commands=['xabar'])
async def broadcast_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer('Sizda bu buyruqdan foydalanish huquqi yo\'q.')
        return
    count = await get_users_count()
    await message.answer(f'👥 Botda jami {count} ta foydalanuvchi ro\'yxatga olingan.\n\nBarchaga yubormoqchi bo\'lgan xabar matnini kiriting:')
    await BroadcastState.text.set()

@dp.message_handler(state=BroadcastState.text)
async def broadcast_preview(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('✅ Ha, yuborish', callback_data='broadcast_confirm'),
        InlineKeyboardButton('❌ Bekor qilish', callback_data='broadcast_cancel')
    )
    await message.answer(f"<b>Xabar shunday ko'rinadi:</b>\n\n{message.text}\n\nYuborishni tasdiqlaysizmi?", reply_markup=kb, parse_mode='HTML')
    await BroadcastState.confirm.set()

@dp.callback_query_handler(text='broadcast_cancel', state=BroadcastState.confirm)
async def broadcast_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.edit_text('❌ Xabar yuborish bekor qilindi.')
    await state.finish()

@dp.callback_query_handler(text='broadcast_confirm', state=BroadcastState.confirm)
async def broadcast_confirm(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    async with state.proxy() as data:
        text = data['text']
    await state.finish()

    await callback_query.message.edit_text('⏳ Xabar yuborilmoqda, biroz kuting...')

    user_ids = await get_all_user_ids()
    success = 0
    failed = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text)
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # Telegram cheklovidan chiqib ketmaslik uchun

    await bot.send_message(
        callback_query.from_user.id,
        f"✅ Xabar yuborish tugadi!\n\n📨 Yuborildi: {success} ta\n🚫 Yuborilmadi (bloklangan/o'chirilgan): {failed} ta"
    )


@dp.message_handler(text='👨‍💻 Erkaklar online')
async def men_online_section(message: types.Message):
    MEN_ONLINE_DB.add(message.from_user.id)
    if message.from_user.id in WOMEN_ONLINE_DB:
        WOMEN_ONLINE_DB.remove(message.from_user.id)
    await message.answer('✅ Siz **"Erkaklar online"** bo\'limiga ulandingiz!', reply_markup=main_menu())

@dp.message_handler(text='👩‍💻 Ayollar online')
async def women_online_section(message: types.Message):
    WOMEN_ONLINE_DB.add(message.from_user.id)
    if message.from_user.id in MEN_ONLINE_DB:
        MEN_ONLINE_DB.remove(message.from_user.id)
    await message.answer('✅ Siz **"👩‍💻 Ayollar online"** bo\'limiga ulandingiz!', reply_markup=main_menu())

@dp.message_handler(text='🔕 Xabarlarni to\'xtatish')
async def stop_notifications(message: types.Message):
    user_id = message.from_user.id
    removed = False
    if user_id in MEN_ONLINE_DB:
        MEN_ONLINE_DB.remove(user_id)
        removed = True
    if user_id in WOMEN_ONLINE_DB:
        WOMEN_ONLINE_DB.remove(user_id)
        removed = True

    if removed:
        await message.answer('🔕 Barcha avtomatik xabarlar to\'xtatildi.', reply_markup=main_menu())
    else:
        await message.answer('Siz allaqachon bildirishnomalarni o\'chirgansiz.', reply_markup=main_menu())

@dp.message_handler(text='👷‍♂️ Ustalar xizmati')
async def show_masters(message: types.Message):
    await message.answer('Kerakli mutaxassislik turini tanlang yoki o\'z xizmatingizni qo\'shing:', reply_markup=masters_menu())

@dp.message_handler(text='🧵 Ayollar bo\'limi')
async def show_women_section(message: types.Message):
    await message.answer(
        '🧵 **Ayollar bo\'limi** (tikuvchilik, pazandachilik, uy xo\'jaligi va boshqa xizmatlar).\n\n'
        'Kerakli tugmani tanlang:',
        reply_markup=women_menu(),
        parse_mode='Markdown'
    )

@dp.message_handler(text='🔍 Ish topish')
async def find_work(message: types.Message):
    ads = await get_all_ads()
    if not ads:
        await message.answer('Hozircha umumiy faol e\'lonlar yo\'q.')
    else:
        text = '<b>📋 Mavjud umumiy e\'lonlar va ishlar:</b>\n\n'
        for idx, ad in enumerate(ads, 1):
            text += f"{idx}. {ad['text']}\n👤 <b>Muallif:</b> {ad['user_name']}\n📞 <b>Tel:</b> {ad['phone']}\n-----\n"
        await message.answer(text, parse_mode='HTML')

@dp.message_handler(text='🗑 Mening e\'lonlarim')
async def my_ads(message: types.Message):
    user_id = message.from_user.id
    user_ads = await get_user_ads(user_id)
    user_women_ads = await get_user_women_ads(user_id)

    if not user_ads and not user_women_ads:
        await message.answer('Sizda hozircha faol e\'lonlar yo\'q.')
        return

    await message.answer('<b>Sizning faol e\'lonlaringiz:</b> (O\'chirish uchun tegishli tugmani bosing)', parse_mode='HTML')

    for idx, ad in enumerate(user_ads, 1):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton('❌ E\'lonni o\'chirish', callback_data=f"del_gen_{ad['id']}"))
        await message.answer(f"<b>Umumiy e'lon #{idx}:</b>\n{ad['text']}\n📞 {ad['phone']}", reply_markup=kb, parse_mode='HTML')

    for idx, ad in enumerate(user_women_ads, 1):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton('❌ E\'lonni o\'chirish', callback_data=f"del_women_{ad['id']}"))
        await message.answer(f"<b>Ayollar bo'limi e'lon #{idx}:</b>\n{ad['text']}\n📞 {ad['phone']}", reply_markup=kb, parse_mode='HTML')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('del_'))
async def delete_ad_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    parts = callback_query.data.split('_')
    ad_type = parts[1]
    ad_id = int(parts[2])

    try:
        if ad_type == 'gen':
            await delete_ad(ad_id)
        elif ad_type == 'women':
            await delete_women_ad(ad_id)
        await callback_query.message.edit_text('✅ E\'lon muvaffaqiyatli o\'chirildi!')
    except Exception:
        await callback_query.message.edit_text('⚠️ Bu e\'lon allaqachon o\'chirilgan.')

@dp.message_handler(text='📢 E\'lon berish')
async def post_ad_start(message: types.Message):
    await message.answer('E\'lon matnini kiriting (ish turi, manzil va talablar):')
    await AdState.text.set()

@dp.message_handler(state=AdState.text)
async def process_ad_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    await message.answer('Aloqa uchun telefon raqamingizni kiriting (masalan: +998901234567):')
    await AdState.next()

@dp.message_handler(state=AdState.phone)
async def process_ad_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        ad_text = data['text']

    await add_ad(message.from_user.id, message.from_user.full_name, ad_text, message.text)

    ad_message = f"<b>📢 ERKAKLAR BO'LIMI - YANGI E'LON!</b>\n\n{ad_text}\n👤 <b>Muallif:</b> {message.from_user.full_name}\n📞 <b>Tel:</b> {message.text}"
    for user_id in MEN_ONLINE_DB:
        try:
            await bot.send_message(user_id, ad_message, parse_mode='HTML')
        except Exception:
            pass

    await message.answer('✅ E\'loningiz qabul qilindi va tarqatildi!', reply_markup=main_menu())
    await state.finish()

@dp.callback_query_handler(text='women_find')
async def process_women_find(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    women_ads = await get_all_women_ads()
    if not women_ads:
        text = "<b>Hozircha Ayollar bo'limida e'lonlar yo'q.</b>"
    else:
        text = "<b>🧵 Ayollar bo'limidagi mavjud e'lonlar:</b>\n\n"
        for idx, ad in enumerate(women_ads, 1):
            text += f"{idx}. {ad['text']}\n👤 <b>Muallif:</b> {ad['user_name']}\n📞 <b>Tel:</b> {ad['phone']}\n-----\n"
    await bot.send_message(callback_query.from_user.id, text, parse_mode='HTML')

@dp.callback_query_handler(text='women_post')
async def process_women_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer('🧵 Ayollar bo\'limi uchun e\'lon matnini kiriting:')
    await WomenAdState.text.set()

@dp.message_handler(state=WomenAdState.text)
async def process_women_ad_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    await message.answer('Aloqa uchun telefon raqamingizni kiriting (masalan: +998901234567):')
    await WomenAdState.next()

@dp.message_handler(state=WomenAdState.phone)
async def process_women_ad_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        ad_text = data['text']

    await add_women_ad(message.from_user.id, message.from_user.full_name, ad_text, message.text)

    ad_message = f"<b>🧵 AYOLLAR ONLINE - YANGI E'LON!</b>\n\n{ad_text}\n👤 <b>Muallif:</b> {message.from_user.full_name}\n📞 <b>Tel:</b> {message.text}"
    for user_id in WOMEN_ONLINE_DB:
        try:
            await bot.send_message(user_id, ad_message, parse_mode='HTML')
        except Exception:
            pass

    await message.answer('✅ E\'loningiz Ayollar bo\'limiga qo\'shildi!', reply_markup=main_menu())
    await state.finish()

@dp.message_handler(text='ℹ️ Ma\'lumot')
async def info_text(message: types.Message):
    await message.answer('Chiroqchi tumanida tezkor ish topish boti: @KunlikIsh_chiroqchi_bot')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('master_'))
async def process_master_category(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    cat_code = callback_query.data.split('_')[1]
    cat_names = {'build': 'Qurilish ustalari', 'electric': 'Elektrik va Santexnik', 'welder': 'Duradgor va Payvandchi', 'finish': 'Malyar va Oboichi'}
    target_cat = cat_names.get(cat_code, '')
    filtered = await get_masters_by_category(target_cat)
    if not filtered:
        text = f"<b>{target_cat} yo'nalishi bo'yicha hozircha ustalar yo'q.</b>"
    else:
        text = f"<b>{target_cat} yo'nalishi bo'yicha ustalar:</b>\n\n"
        for idx, m in enumerate(filtered, 1):
            text += f"{idx}. <b>{m['category']}</b>\n👤 {m['full_name']}\n📞 {m['phone']}\n📝 {m['description']}\n-----\n"
    await bot.send_message(callback_query.from_user.id, text, parse_mode='HTML')

@dp.callback_query_handler(text='add_master')
async def add_master_start(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer('Yo\'nalishni tanlang:', reply_markup=categories_keyboard())
    await MasterState.category.set()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('cat_'), state=MasterState.category)
async def process_category_choice(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    selected_category = callback_query.data.split('_', 1)[1]
    async with state.proxy() as data:
        data['category'] = selected_category
    await callback_query.message.answer('Ism va familiyangizni kiriting:')
    await MasterState.next()

@dp.message_handler(state=MasterState.full_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['full_name'] = message.text
    await message.answer('Telefon raqamingizni kiriting (masalan: +998901234567):')
    await MasterState.next()

@dp.message_handler(state=MasterState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
    await message.answer('Qisqacha tajribangiz haqida yozing:')
    await MasterState.next()

@dp.message_handler(state=MasterState.description)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        category = data['category']
        full_name = data['full_name']
        phone = data['phone']

    await add_master(category, full_name, phone, message.text)
    await message.answer('✅ Muvaffaqiyatli saqlandi!', reply_markup=main_menu())
    await state.finish()


async def on_startup(dispatcher):
    await init_db()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
