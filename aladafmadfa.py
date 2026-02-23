import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import threading
import time
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import (SessionPasswordNeededError, FloodWaitError, 
                             UserPrivacyRestrictedError, PasswordHashInvalidError, RPCError)

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

# --- 🗄️ قاعدة البيانات (إصلاح الربط) ---
def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    # التأكد من وجود المستخدم أولاً
    conn.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (uid,))
    # تحديث الرصيد بدقة مع تمرير البارامترات كـ Tuple
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(amount), int(uid)))
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect('mega_bot.db')
    res = conn.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return round(float(res[0]), 2) if res else 0.0

# --- 🎯 معالج الأزرار (حل مشكلة عدم الاستجابة والخطأ) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try: bot.answer_callback_query(call.id)
    except: pass
    
    uid = call.message.chat.id

    # تم إصلاح هذا الجزء تحديداً (Confirm Charge)
    if call.data.startswith("confirm_charge_"):
        try:
            # البيانات تأتي هكذا: confirm_charge_المبلغ_الآيدي
            data_parts = call.data.split("_")
            amt = float(data_parts[2])
            target_id = int(data_parts[3])
            
            update_balance(target_id, amt)
            
            bot.send_message(target_id, f"✅ **تم الشحن بنجاح!**\nتم إضافة {amt}$ إلى رصيدك.")
            bot.edit_message_caption(f"✅ تم تأكيد الشحن لـ {target_id}\nالمبلغ: {amt}$", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ خطأ فني: {e}")

    elif call.data == "method_manual":
        msg = bot.send_message(uid, f"💳 **شحن يدوي**\nالعنوان: `{MY_WALLET}`\nأرسل صورة الإيصال:")
        bot.register_next_step_handler(msg, process_photo)

    elif call.data == "method_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار:")
        bot.register_next_step_handler(msg, process_auto)

    elif call.data.startswith("terminate_"):
        aid = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db'); conn.execute("DELETE FROM user_accounts WHERE id=?", (aid,)); conn.commit(); conn.close()
        bot.delete_message(uid, call.message.message_id)

# --- 📸 معالجة الصور ---
def process_photo(message):
    if message.content_type == 'photo':
        u = message.chat.id
        markup = types.InlineKeyboardMarkup()
        # تأكد من أن الـ callback_data تطابق التقسيم في المعالج فوق
        markup.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"confirm_charge_5_{u}"),
                   types.InlineKeyboardButton("✅ 10$", callback_data=f"confirm_charge_10_{u}"))
        markup.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"confirm_charge_20_{u}"),
                   types.InlineKeyboardButton("✅ 50$", callback_data=f"confirm_charge_50_{u}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب من: `{u}`", reply_markup=markup)
        bot.send_message(u, "⏳ تم الإرسال للمالك..")
    else: bot.send_message(message.chat.id, "⚠️ أرسل صورة فقط.")

# --- ⚔️ محرك النقل (كامل وشامل) ---
async def transfer_worker(uid, src, trg, count, mid):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (uid,)).fetchall()
    conn.close()
    if not accs: return
    
    added = 0
    active = []
    for s in accs:
        c = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await c.connect()
        if await c.is_user_authorized(): active.append(c)

    if not active: 
        bot.send_message(uid, "❌ لا توجد حسابات شغالة.")
        return

    try:
        leader = active[0]
        s_e = await leader.get_entity(src); t_e = await leader.get_entity(trg)
        await leader(JoinChannelRequest(s_e)); await leader(JoinChannelRequest(t_e))
        
        users = set()
        async for p in leader.iter_participants(s_e, limit=300):
            if not p.bot: users.add(p.id)
        
        user_list = list(users)
        while added < count and user_list:
            for c in active:
                if added >= count or not user_list: break
                try:
                    await c(InviteToChannelRequest(t_e, [user_list.pop(0)]))
                    added += 1
                    if added % 5 == 0: bot.edit_message_text(f"⏳ تم إضافة {added} عضو...", uid, mid)
                    await asyncio.sleep(2)
                except FloodWaitError: active.remove(c); break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    
    update_balance(uid, -(added * PRICE_PER_MEMBER))
    bot.send_message(uid, f"✅ اكتمل النقل! المضاف: {added}")

def start_tr_thread(uid, s, t, c, mid):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); loop.run_until_complete(transfer_worker(uid, s, t, c, mid))

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def tr_start(message):
    uid = message.chat.id
    if get_balance(uid) < PRICE_PER_MEMBER: return bot.send_message(uid, "❌ رصيدك 0.")
    msg = bot.send_message(uid, "📦 رابط المصدر:")
    bot.register_next_step_handler(msg, lambda m: bot.register_next_step_handler(bot.send_message(uid, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(uid, "🔢 العدد؟"), tr_final, m.text, m2.text)))

def tr_final(message, s, t):
    try:
        cnt = int(message.text); uid = message.chat.id
        todo = min(cnt, int(get_balance(uid)/PRICE_PER_MEMBER))
        status = bot.send_message(uid, "🚀 جاري البدء...")
        threading.Thread(target=start_tr_thread, args=(uid, s, t, todo, status.message_id)).start()
    except: bot.send_message(message.chat.id, "⚠️ خطأ")

# --- 📱 إدارة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_init(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل الرقم (+966...):")
    bot.register_next_step_handler(msg, add_otp)

def add_otp(message):
    phone = message.text.strip(); client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h(): await client.connect(); r = await client.send_code_request(phone); return r.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(get_h())
        msg = bot.send_message(message.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(msg, add_verify, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_verify(message, phone, h, s):
    otp = message.text.strip(); client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try: await client.sign_in(phone, otp, phone_code_hash=h); return "OK", client.session.save()
        except SessionPasswordNeededError: return "2FA", client.session.save()
    try:
        st, fs = asyncio.run(sign())
        if st == "OK":
            conn = sqlite3.connect('mega_bot.db'); conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone)); conn.commit(); conn.close()
            bot.send_message(message.chat.id, "✅ تم الربط!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:")
            bot.register_next_step_handler(msg, add_pwd, phone, fs)
    except: bot.send_message(message.chat.id, "❌ خطأ.")

def add_pwd(message, phone, s):
    pwd = message.text.strip(); client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log(): await client.connect(); await client.sign_in(password=pwd); return client.session.save()
    try:
        fs = asyncio.run(log())
        conn = sqlite3.connect('mega_bot.db'); conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone)); conn.commit(); conn.close()
        bot.send_message(message.chat.id, "✅ تم بنجاح!")
    except: bot.send_message(message.chat.id, "❌ خطأ.")

# --- 🚀 الأوامر العامة ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي", "💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 رصيدك: {get_balance(message.chat.id)}$", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ تلقائي", callback_data="method_auto"), types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="method_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

def process_auto(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'): bot.send_message(message.chat.id, "💳 ادفع هنا:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("رابط الدفع", url=res['payLink'])))
    except: bot.send_message(message.chat.id, "⚠️ خطأ")

init_db()
print("🔥 تم إصلاح الخطأ.. البوت جاهز تماماً!")
bot.infinity_polling()
