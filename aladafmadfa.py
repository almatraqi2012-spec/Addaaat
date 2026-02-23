import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import (SessionPasswordNeededError, FloodWaitError, 
                             UserPrivacyRestrictedError, PasswordHashInvalidError, 
                             PhoneCodeInvalidError)

# ================= [ 🛠️ إعدادات الصاروخ ] =================
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
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect('mega_bot.db')
    res = conn.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return round(float(res[0]), 2) if res else 0.0

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)")
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

# --- 🏠 الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي")
    markup.add("💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 **أهلاً بك في بوت دراجون للغزو**\n💰 رصيدك: `{get_balance(message.chat.id)}$`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"📊 **معلوماتك:**\n🆔 الآيدي: `{uid}`\n💰 الرصيد: `{bal}$`\n📱 جيش الحسابات: `{acc_count}`")

# --- 📱 إضافة الحسابات (شامل التحقق بخطوتين) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_acc_1(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل الرقم مع رمز الدولة (مثال: +213...):")
    bot.register_next_step_handler(msg, add_acc_2)

def add_acc_2(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(get_h())
        msg = bot.send_message(message.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, add_acc_3, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_acc_3(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try:
            await client.sign_in(phone, otp, phone_code_hash=h)
            return "OK", client.session.save()
        except SessionPasswordNeededError: return "2FA", client.session.save()
    try:
        status, fs = asyncio.run(sign())
        if status == "OK":
            conn = sqlite3.connect('mega_bot.db'); conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone)); conn.commit(); conn.close()
            bot.send_message(message.chat.id, "✅ تم ربط الحساب بنجاح!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 الحساب محمي بكلمة سر.. أرسلها الآن:")
            bot.register_next_step_handler(msg, add_acc_pwd, phone, fs)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_acc_pwd(message, phone, s):
    pwd = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def sign_p():
        await client.connect(); await client.sign_in(password=pwd); return client.session.save()
    try:
        fs = asyncio.run(sign_p())
        conn = sqlite3.connect('mega_bot.db'); conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone)); conn.commit(); conn.close()
        bot.send_message(message.chat.id, "✅ تم فك التشفير والربط!")
    except: bot.send_message(message.chat.id, "❌ كلمة سر خاطئة.")

# --- ⚔️ محرك النقل (يقرع قريع) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_start(message):
    uid = message.chat.id
    bal = get_balance(uid)
    if bal < PRICE_PER_MEMBER: return bot.send_message(uid, "❌ رصيدك 0.")
    msg = bot.send_message(uid, "📦 أرسل رابط المجموعة **المصدر**:")
    bot.register_next_step_handler(msg, get_target)

def get_target(message):
    source = message.text.strip()
    msg = bot.send_message(message.chat.id, "🎯 أرسل رابط مجموعتك (**الهدف**):")
    bot.register_next_step_handler(msg, get_count, source)

def get_count(message, source):
    target = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔢 العدد المطلوب؟")
    bot.register_next_step_handler(msg, run_war, source, target)

def run_war(message, source, target):
    try:
        req = int(message.text); uid = message.chat.id; bal = get_balance(uid)
        todo = min(req, int(bal / PRICE_PER_MEMBER))
        status = bot.send_message(uid, f"🚀 بدأنا نقل {todo} عضواً...")
        conn = sqlite3.connect('mega_bot.db'); sessions = [r[0] for r in conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (uid,)).fetchall()]; conn.close()
        added = 0
        async def work():
            nonlocal added
            for s in sessions:
                if added >= todo: break
                client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
                try:
                    await client.connect()
                    s_e = await client.get_entity(source); t_e = await client.get_entity(target)
                    await client(JoinChannelRequest(s_e)); await client(JoinChannelRequest(t_e))
                    users = set()
                    async for m in client.iter_messages(s_e, limit=400):
                        if m.sender_id and not m.sender.bot: users.add(m.sender_id)
                    for u in users:
                        if added >= todo: break
                        try:
                            await client(InviteToChannelRequest(t_e, [u])); added += 1
                            if added % 5 == 0: bot.edit_message_text(f"⏳ تم نقل {added} عضو...", uid, status.message_id)
                            await asyncio.sleep(2)
                        except FloodWaitError: break
                        except: continue
                except: continue
                finally: await client.disconnect()
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); loop.run_until_complete(work())
        if added > 0:
            update_balance(uid, -(added * PRICE_PER_MEMBER))
            bot.send_message(uid, f"✅ تمت العملية! المضاف: {added}\nالرصيد الحالي: {get_balance(uid)}$")
    except: bot.send_message(message.chat.id, "⚠️ خطأ في البيانات.")

# --- 💰 نظام الشحن (المُصلح والنهائي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ تلقائي", callback_data="p_auto"), types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="p_manual"))
    bot.send_message(message.chat.id, "اختر وسيلة الشحن:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    if call.data.startswith("confirm_"):
        _, amt, target = call.data.split("_")
        update_balance(int(target), float(amt))
        bot.send_message(int(target), f"✅ تم شحن {amt}$ برصيدك!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
    elif call.data == "p_manual":
        msg = bot.send_message(call.message.chat.id, f"💳 **شحن يدوي**\n`{MY_WALLET}`\nأرسل الصورة هنا 👇")
        bot.register_next_step_handler(msg, handle_proof)
    elif call.data == "p_auto":
        msg = bot.send_message(call.message.chat.id, "💰 أدخل المبلغ بالدولار:")
        bot.register_next_step_handler(msg, handle_auto)

def handle_proof(message):
    if message.content_type == 'photo':
        u = message.chat.id; markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"confirm_5_{u}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"confirm_10_{u}"))
        markup.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"confirm_20_{u}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"confirm_50_{u}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب من: `{u}`", reply_markup=markup)
        bot.send_message(u, "⏳ تم الإرسال للمراجعة.")

def handle_auto(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            bot.send_message(message.chat.id, "💳 اضغط للدفع:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("رابط الدفع", url=res['payLink'])))
    except: bot.send_message(message.chat.id, "⚠️ خطأ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def del_acc(message):
    conn = sqlite3.connect('mega_bot.db'); accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall(); conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا يوجد")
    markup = types.InlineKeyboardMarkup()
    for aid, ph in accs: markup.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(message.chat.id, "اختر لحذفه:", reply_markup=markup)

init_db()
bot.infinity_polling()
