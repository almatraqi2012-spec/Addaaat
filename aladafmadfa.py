import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import threading
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import (SessionPasswordNeededError, FloodWaitError, 
                             PasswordHashInvalidError)

# ================= [ 🛠️ إعدادات الصاروخ ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

# تفعيل نظام threaded لضمان استجابة أزرار المالك فوراً مهما كان الضغط
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# --- 🗄️ نظام إدارة البيانات ---
def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)")
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect('mega_bot.db')
    res = conn.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return round(float(res[0]), 2) if res else 0.0

# --- 🎯 محرك الاستجابة للأزرار (الموافقات) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    bot.answer_callback_query(call.id) # فتح الزر فوراً
    uid = call.message.chat.id
    
    # موافقة المالك على الشحن (إصلاح الاستجابة)
    if call.data.startswith("add_"):
        _, amt, target_uid = call.data.split("_")
        update_balance(int(target_uid), float(amt))
        bot.send_message(int(target_uid), f"✅ تم شحن {amt}$ في حسابك بنجاح!")
        bot.edit_message_caption(f"✅ تم تأكيد الشحن لـ {target_uid}\nالمبلغ: {amt}$", call.message.chat.id, call.message.message_id)

    elif call.data == "p_manual":
        msg = bot.send_message(uid, f"💳 **شحن USDT (TRC20)**\n`{MY_WALLET}`\nأرسل صورة الإيصال 👇")
        bot.register_next_step_handler(msg, receive_photo)
    
    elif call.data == "p_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار:")
        bot.register_next_step_handler(msg, oxapay_invoice)

    elif call.data.startswith("del_"):
        aid = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db'); conn.execute("DELETE FROM user_accounts WHERE id=?", (aid,)); conn.commit(); conn.close()
        bot.delete_message(uid, call.message.message_id)

# --- 📸 استقبال صور الشحن ---
def receive_photo(message):
    if message.content_type == 'photo':
        u = message.chat.id
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"add_5_{u}"), 
                   types.InlineKeyboardButton("✅ 10$", callback_data=f"add_10_{u}"))
        markup.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"add_20_{u}"), 
                   types.InlineKeyboardButton("✅ 50$", callback_data=f"add_50_{u}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب شحن من: `{u}`", reply_markup=markup)
        bot.send_message(u, "⏳ تم إرسال الإثبات للمالك..")

# --- ⚔️ محرك النقل والنبش (النسخة المدمرة) ---
def transfer_logic(uid, source, target, count, mid):
    async def run():
        conn = sqlite3.connect('mega_bot.db')
        sessions = [r[0] for r in conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (uid,)).fetchall()]
        conn.close()
        added = 0
        for s in sessions:
            if added >= count: break
            client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
            try:
                await client.connect()
                s_e = await client.get_entity(source); t_e = await client.get_entity(target)
                await client(JoinChannelRequest(s_e)); await client(JoinChannelRequest(t_e))
                # نبش الأعضاء من الرسائل لتخطى الإخفاء
                users = set()
                async for m in client.iter_messages(s_e, limit=300):
                    if m.sender_id and not m.sender.bot: users.add(m.sender_id)
                for u_id in users:
                    if added >= count: break
                    try:
                        await client(InviteToChannelRequest(t_e, [u_id])); added += 1
                        if added % 5 == 0: bot.edit_message_text(f"⏳ جاري النقل... تم إضافة {added} عضو.", uid, mid)
                        await asyncio.sleep(2)
                    except: continue
            except: continue
            finally: await client.disconnect()
        if added > 0:
            update_balance(uid, -(added * PRICE_PER_MEMBER))
            bot.send_message(uid, f"✅ اكتمل الغزو! تم إضافة {added} عضو.")
    asyncio.run(run())

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_start(message):
    uid = message.chat.id
    if get_balance(uid) < PRICE_PER_MEMBER: return bot.send_message(uid, "❌ رصيدك 0.")
    msg = bot.send_message(uid, "📦 أرسل رابط المصدر:")
    bot.register_next_step_handler(msg, lambda m: bot.register_next_step_handler(bot.send_message(uid, "🎯 أرسل رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(uid, "🔢 كم العدد؟"), start_transfer_thread, m.text, m2.text)))

def start_transfer_thread(message, src, trg):
    try:
        req = int(message.text); uid = message.chat.id
        todo = min(req, int(get_balance(uid)/PRICE_PER_MEMBER))
        status = bot.send_message(uid, "🚀 بدأ التنين بالتحرك...")
        threading.Thread(target=transfer_logic, args=(uid, src, trg, todo, status.message_id)).start()
    except: bot.send_message(message.chat.id, "⚠️ خطأ بيانات.")

# --- 📱 إضافة الحسابات (شامل التحقق بخطوتين) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_phone(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل الرقم (مثال: +966...):")
    bot.register_next_step_handler(msg, add_code)

def add_code(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h():
        await client.connect(); res = await client.send_code_request(phone); return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(get_h())
        msg = bot.send_message(message.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(msg, verify_all, phone, h, s)
    except: bot.send_message(message.chat.id, "❌ خطأ بالرقم.")

def verify_all(message, phone, h, s):
    otp = message.text.strip(); client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log():
        await client.connect()
        try: await client.sign_in(phone, otp, phone_code_hash=h); return "OK", client.session.save()
        except SessionPasswordNeededError: return "2FA", client.session.save()
    try:
        st, fs = asyncio.run(log())
        if st == "OK":
            conn = sqlite3.connect('mega_bot.db'); conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone)); conn.commit(); conn.close()
            bot.send_message(message.chat.id, "✅ تم الربط!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:")
            bot.register_next_step_handler(msg, login_pwd, phone, fs)
    except: bot.send_message(message.chat.id, "❌ خطأ بالكود.")

def login_pwd(message, phone, s):
    pwd = message.text.strip(); client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def lp(): await client.connect(); await client.sign_in(password=pwd); return client.session.save()
    try:
        fs = asyncio.run(lp())
        conn = sqlite3.connect('mega_bot.db'); conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone)); conn.commit(); conn.close()
        bot.send_message(message.chat.id, "✅ تم فك القفل والربط!")
    except: bot.send_message(message.chat.id, "❌ كلمة سر خاطئة.")

# --- 🚀 الأوامر الثابتة ---
@bot.message_handler(commands=['start'])
def welcome(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي", "💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 رصيدك: {get_balance(message.chat.id)}$", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ تلقائي", callback_data="p_auto"), types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="p_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

def oxapay_invoice(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            bot.send_message(message.chat.id, f"💳 فاتورة {amt}$:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ادفع الآن", url=res['payLink'])))
    except: bot.send_message(message.chat.id, "⚠️ خطأ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def delete_list(message):
    conn = sqlite3.connect('mega_bot.db'); accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall(); conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا يوجد.")
    markup = types.InlineKeyboardMarkup()
    for aid, ph in accs: markup.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(message.chat.id, "اختر لحذفه:", reply_markup=markup)

init_db()
print("🔥 القريع بدأ.. التنين كامل مكمل وجاهز!")
bot.infinity_polling()
