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
ADMIN_ID = 5163375125  # آيديك يا ملك
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- 🗄️ إدارة قاعدة البيانات (المخ الحافظ) ---
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

# --- 🏠 واجهة المستخدم ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي")
    markup.add("💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 **أهلاً بك في بوت دراجون (النسخة المدمرة)**\n\n💰 رصيدك الحالي: `{get_balance(message.chat.id)}$`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"📊 **إحصائياتك:**\n🆔 الآيدي: `{uid}`\n💰 الرصيد: `{bal}$`\n📱 جيش الحسابات: `{acc_count}`", parse_mode="Markdown")

# --- ⚔️ محرك النقل (قلب التنين) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_init(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()

    if acc_count == 0: return bot.send_message(uid, "⚠️ أضف حسابات أولاً!")
    if bal < PRICE_PER_MEMBER: return bot.send_message(uid, "❌ رصيدك لا يكفي لنقل حتى عضو واحد!")

    msg = bot.send_message(uid, "📦 **أرسل رابط المجموعة (المصدر):**")
    bot.register_next_step_handler(msg, get_source)

def get_source(message):
    source = message.text.strip()
    msg = bot.send_message(message.chat.id, "🎯 **أرسل رابط مجموعتك (الهدف):**")
    bot.register_next_step_handler(msg, get_target, source)

def get_target(message, source):
    target = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔢 **كم العدد المطلوب نقله؟**")
    bot.register_next_step_handler(msg, start_war, source, target)

def start_war(message, source, target):
    try:
        req_count = int(message.text)
        uid = message.chat.id
        bal = get_balance(uid)
        max_m = int(bal / PRICE_PER_MEMBER)
        todo = min(req_count, max_m)

        status_msg = bot.send_message(uid, f"🚀 **جاري اختراق الحواجز ونقل {todo} عضو...**")

        conn = sqlite3.connect('mega_bot.db')
        sessions = [r[0] for r in conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (uid,)).fetchall()]
        conn.close()

        added = 0
        async def run_logic():
            nonlocal added
            for s in sessions:
                if added >= todo: break
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
                        if added >= todo: break
                        try:
                            await client(InviteToChannelRequest(t_ent, [u_id]))
                            added += 1
                            if added % 5 == 0:
                                try: bot.edit_message_text(f"⏳ جاري الاختراق... تم إضافة {added} عضواً.", uid, status_msg.message_id)
                                except: pass
                            await asyncio.sleep(2)
                        except FloodWaitError: break
                        except: continue
                except: continue
                finally: await client.disconnect()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_logic())

        if added > 0:
            cost = round(added * PRICE_PER_MEMBER, 2)
            update_balance(uid, -cost)
            bot.send_message(uid, f"✅ **اكتمل الغزو بنجاح!**\n➕ تم إضافة: {added}\n💸 الخصم: {cost}$\n💰 رصيدك: {get_balance(uid)}$")
        else: bot.send_message(uid, "❌ لم يتم إضافة أي عضو. تأكد من الروابط وحالة الحسابات.")
    except: bot.send_message(message.chat.id, "⚠️ خطأ في البيانات!")

# --- 📱 إضافة الحسابات وفك التشفير ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_acc_step1(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل رقم الهاتف مع رمز الدولة (مثال: +213...):")
    bot.register_next_step_handler(msg, add_acc_step2)

def add_acc_step2(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(get_h())
        msg = bot.send_message(message.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, add_acc_step3, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_acc_step3(message, phone, h, s):
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
            save_acc(message.chat.id, fs, phone)
            bot.send_message(message.chat.id, "✅ تم الربط!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 هذا الحساب محمي بكلمة سر.. أرسلها الآن:")
            bot.register_next_step_handler(msg, add_acc_step_pwd, phone, fs)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_acc_step_pwd(message, phone, s):
    pwd = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def sign_pwd():
        await client.connect()
        await client.sign_in(password=pwd)
        return client.session.save()
    try:
        fs = asyncio.run(sign_pwd())
        save_acc(message.chat.id, fs, phone)
        bot.send_message(message.chat.id, "✅ تم فك التشفير والربط!")
    except: bot.send_message(message.chat.id, "❌ كلمة سر خاطئة!")

def save_acc(uid, s, p):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (uid, s, p))
    conn.commit()
    conn.close()

# --- 💰 نظام الشحن (المتكامل والمستجيب) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="p_auto"))
    markup.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (USDT)", callback_data="p_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الدفع:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    uid = call.message.chat.id
    if call.data == "p_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار:")
        bot.register_next_step_handler(msg, auto_inv)
    elif call.data == "p_manual":
        bot.send_message(uid, f"💳 **شحن USDT (TRC20)**\n`{MY_WALLET}`\nأرسل صورة الإيصال 👇")
        bot.register_next_step_handler(call.message, manual_proof)
    elif call.data.startswith("adm_"):
        # تنسيق: adm_المبلغ_الآيدي
        _, amt, target = call.data.split("_")
        update_balance(int(target), float(amt))
        bot.send_message(int(target), f"✅ تم شحن {amt}$ في حسابك!")
        bot.edit_message_caption(f"✅ تم تأكيد الشحن لآيدي {target}", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "تم الشحن")
    elif call.data.startswith("del_"):
        aid = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("DELETE FROM user_accounts WHERE id=?", (aid,))
        conn.commit()
        conn.close()
        bot.delete_message(uid, call.message.message_id)

def auto_inv(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(message.chat.id, f"✅ فاتورة شحن {amt}$", reply_markup=btn)
    except: bot.send_message(message.chat.id, "⚠️ أدخل رقماً صحيحاً.")

def manual_proof(message):
    if message.content_type == 'photo':
        u = message.chat.id
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_5_{u}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10_{u}"))
        markup.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_20_{u}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"adm_50_{u}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب شحن من: `{u}`", reply_markup=markup)
        bot.send_message(u, "⏳ تم إرسال طلبك للإدارة.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def list_del(message):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall()
    conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا توجد حسابات.")
    markup = types.InlineKeyboardMarkup()
    for aid, ph in accs: markup.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(message.chat.id, "اختر الحساب لحذفه:", reply_markup=markup)

# --- 🚀 الإقلاع ---
init_db()
print("🔥 دراجون يقرع الأرض الآن.. البوت شغال!")
bot.infinity_polling()
