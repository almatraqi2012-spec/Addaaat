import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetMessagesRequest
from telethon.errors import (SessionPasswordNeededError, FloodWaitError, 
                             UserPrivacyRestrictedError, PasswordHashInvalidError)

# ================= [ 🛠️ إعدادات البوت ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- 🗄️ إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect('mega_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    conn.close()
    if res: return round(float(res[0]), 2)
    return 0.0

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)")
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

# --- 🏠 الأزرار الرئيسية ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي")
    markup.add("💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 **أهلاً بك في بوت دراجون لزيادة الأعضاء**\n💰 رصيدك الحالي: `{get_balance(message.chat.id)}$`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"📊 **معلومات حسابك:**\n\n🆔 الآيدي: `{uid}`\n💰 الرصيد: `{bal}$`\n📱 الحسابات المضافة: `{acc_count}`", parse_mode="Markdown")

# --- ⚔️ محرك النقل والنبش الخارق ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_start(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()

    if acc_count == 0: return bot.send_message(uid, "⚠️ أضف حسابات أولاً عبر زر (➕ إضافة حسابات للنقل).")
    if bal < PRICE_PER_MEMBER: return bot.send_message(uid, "❌ رصيدك غير كافٍ، يرجى الشحن.")

    max_m = int(bal / PRICE_PER_MEMBER)
    msg = bot.send_message(uid, f"✅ رصيدك يسمح بنقل {max_m} عضو.\n📦 أرسل رابط المجموعة **المصدر**:")
    bot.register_next_step_handler(msg, step_2)

def step_2(message):
    source = message.text.strip()
    msg = bot.send_message(message.chat.id, "🎯 أرسل رابط مجموعتك (**الهدف**):")
    bot.register_next_step_handler(msg, step_3, source)

def step_3(message, source):
    target = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔢 كم العدد المطلوب نقله؟")
    bot.register_next_step_handler(msg, run_transfer, source, target)

def run_transfer(message, source, target):
    try:
        req_count = int(message.text.strip())
        uid = message.chat.id
        bal = get_balance(uid)
        final_count = min(req_count, int(bal / PRICE_PER_MEMBER))

        status_msg = bot.send_message(uid, "🚀 **بدأ التنين بالتحرك.. جاري النبش والإضافة...**")

        conn = sqlite3.connect('mega_bot.db')
        sessions = [r[0] for r in conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (uid,)).fetchall()]
        conn.close()

        added = 0
        async def main_logic():
            nonlocal added
            for s in sessions:
                if added >= final_count: break
                client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
                try:
                    await client.connect()
                    s_ent = await client.get_entity(source)
                    t_ent = await client.get_entity(target)
                    await client(JoinChannelRequest(s_ent))
                    await client(JoinChannelRequest(t_ent))
                    
                    users = set()
                    async for m in client.iter_messages(s_ent, limit=500):
                        if m.sender_id and not m.sender.bot: users.add(m.sender_id)
                    
                    for u_id in users:
                        if added >= final_count: break
                        try:
                            await client(InviteToChannelRequest(t_ent, [u_id]))
                            added += 1
                            if added % 5 == 0:
                                try: bot.edit_message_text(f"⏳ جاري النقل... تم إضافة {added} عضو حتى الآن.", uid, status_msg.message_id)
                                except: pass
                            await asyncio.sleep(2)
                        except FloodWaitError: break
                        except: continue
                except: continue
                finally: await client.disconnect()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_logic())

        if added > 0:
            cost = round(added * PRICE_PER_MEMBER, 2)
            update_balance(uid, -cost)
            bot.send_message(uid, f"✅ **تمت المهمة بنجاح!**\n➕ تم إضافة: {added} عضو\n💸 المخصوم: {cost}$\n💰 رصيدك الحالي: {get_balance(uid)}$")
        else:
            bot.send_message(uid, "❌ فشل النقل، تأكد من الروابط وصلاحية الحسابات.")
    except: bot.send_message(message.chat.id, "⚠️ خطأ في البيانات.")

# --- 📱 إدارة الحسابات (مع فك تشفير كلمة السر) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_phone_start(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل رقم الهاتف (مثال: +966...):")
    bot.register_next_step_handler(msg, send_otp)

def send_otp(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def run():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(run())
        msg = bot.send_message(message.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, login_otp, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def login_otp(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def run():
        await client.connect()
        try:
            await client.sign_in(phone, otp, phone_code_hash=h)
            return "OK", client.session.save()
        except SessionPasswordNeededError:
            return "PWD", client.session.save()
    try:
        status, fs = asyncio.run(run())
        if status == "OK":
            save_acc(message.chat.id, fs, phone)
            bot.send_message(message.chat.id, "✅ تم ربط الحساب بنجاح!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 الحساب محمي بكلمة سر.. أرسلها الآن:")
            bot.register_next_step_handler(msg, login_pwd, phone, fs)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def login_pwd(message, phone, s):
    pwd = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def run():
        await client.connect()
        await client.sign_in(password=pwd)
        return client.session.save()
    try:
        fs = asyncio.run(run())
        save_acc(message.chat.id, fs, phone)
        bot.send_message(message.chat.id, "✅ تم فك القفل وربط الحساب!")
    except: bot.send_message(message.chat.id, "❌ كلمة سر خاطئة.")

def save_acc(uid, s, p):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (uid, s, p))
    conn.commit()
    conn.close()

# --- 💰 نظام الشحن (تلقائي ويدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="p_auto"), types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="p_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    uid = call.message.chat.id
    if call.data == "p_auto":
        bot.register_next_step_handler(bot.send_message(uid, "💰 أدخل المبلغ ($):"), create_inv)
    elif call.data == "p_manual":
        bot.send_message(uid, f"💳 **شحن USDT (TRC20)**\n`{MY_WALLET}`\nأرسل صورة التحويل 👇")
        bot.register_next_step_handler(call.message, receive_p)
    elif call.data.startswith("adm_ok"):
        _, _, amt, t_id = call.data.split("_")
        update_balance(int(t_id), float(amt))
        bot.send_message(int(t_id), f"✅ تم تأكيد شحن {amt}$ في حسابك.")
        bot.edit_message_caption(f"✅ تم الشحن لآيدي {t_id}", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("del_"):
        aid = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("DELETE FROM user_accounts WHERE id=?", (aid,))
        conn.commit()
        conn.close()
        bot.delete_message(uid, call.message.message_id)

def create_inv(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط للدفع", url=res['payLink']))
            bot.send_message(message.chat.id, f"✅ فاتورة بقيمة {amt}$", reply_markup=markup)
    except: bot.send_message(message.chat.id, "⚠️ أدخل رقماً صحيحاً.")

def receive_p(message):
    if message.content_type == 'photo':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ شحن 5$", callback_data=f"adm_ok_5_{message.chat.id}"), 
                   types.InlineKeyboardButton("✅ شحن 10$", callback_data=f"adm_ok_10_{message.chat.id}"),
                   types.InlineKeyboardButton("✅ شحن 20$", callback_data=f"adm_ok_20_{message.chat.id}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب شحن من: {message.chat.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ جاري مراجعة طلبك...")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def del_acc(message):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall()
    conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا توجد حسابات.")
    markup = types.InlineKeyboardMarkup()
    for aid, ph in accs: markup.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(message.chat.id, "اختر الحساب لحذفه:", reply_markup=markup)

# --- 🚀 التشغيل ---
init_db()
print("🐲 دراجون النهائي انطلق الآن...")
bot.infinity_polling()
