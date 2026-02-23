import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError

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

def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def get_balance(uid):
    init_db()
    conn = sqlite3.connect('mega_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return round(float(res[0]), 2)
    return 0.0

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    if cursor.fetchone():
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    else:
        conn.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (uid, amount))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي")
    markup.add("💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 **مرحباً بك في بوت دراجون**\n💰 رصيدك الحالي: `{get_balance(message.chat.id)}$`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"📊 **معلومات حسابك:**\n\n🆔 الآيدي: `{uid}`\n💰 الرصيد الحالي: `{bal}$`\n📱 الحسابات المضافة: `{acc_count}`", parse_mode="Markdown")

# --- محرك النقل المعدل (حل مشكلة رفض الرصيد) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_start(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()

    if acc_count == 0: 
        return bot.send_message(uid, "⚠️ يجب إضافة حسابات أولاً!")
    
    if bal < PRICE_PER_MEMBER:
        return bot.send_message(uid, f"❌ رصيدك الحالي ({bal}$) أقل من سعر عضو واحد ({PRICE_PER_MEMBER}$).")

    max_members = int(bal / PRICE_PER_MEMBER)
    msg = bot.send_message(uid, f"✅ رصيدك يسمح بنقل حتى **{max_members}** عضو.\n📦 أرسل رابط المجموعة المصدر:")
    bot.register_next_step_handler(msg, step_2)

def step_2(message):
    source = message.text.strip()
    msg = bot.send_message(message.chat.id, "🎯 أرسل رابط مجموعتك (الهدف):")
    bot.register_next_step_handler(msg, step_3, source)

def step_3(message, source):
    target = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔢 كم عدد الأعضاء المطلوب نقلهم؟")
    bot.register_next_step_handler(msg, run_transfer, source, target)

def run_transfer(message, source, target):
    try:
        requested_count = int(message.text.strip())
        uid = message.chat.id
        bal = get_balance(uid)
        
        # السماح بنقل الممكن فقط بناء على الرصيد
        allowed_count = int(bal / PRICE_PER_MEMBER)
        final_target_count = min(requested_count, allowed_count)

        if final_target_count <= 0:
            return bot.send_message(uid, "❌ رصيدك لا يكفي لهذا العدد.")

        status_msg = bot.send_message(uid, f"🚀 بدأنا! جاري نقل {final_target_count} عضو...")

        conn = sqlite3.connect('mega_bot.db')
        sessions = [r[0] for r in conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (uid,)).fetchall()]
        conn.close()

        added = 0
        async def main_logic():
            nonlocal added
            for s in sessions:
                if added >= final_target_count: break
                client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
                try:
                    await client.connect()
                    s_ent = await client.get_entity(source)
                    t_ent = await client.get_entity(target)
                    await client(JoinChannelRequest(s_ent))
                    await client(JoinChannelRequest(t_ent))
                    
                    users = set()
                    async for m in client.iter_messages(s_ent, limit=400):
                        if m.sender_id and not m.sender.bot: users.add(m.sender_id)
                    
                    for u_id in users:
                        if added >= final_target_count: break
                        try:
                            await client(InviteToChannelRequest(t_ent, [u_id]))
                            added += 1
                            if added % 5 == 0:
                                try: bot.edit_message_text(f"⏳ جاري النقل... تم إضافة {added} عضو.", uid, status_msg.message_id)
                                except: pass
                            await asyncio.sleep(2)
                        except FloodWaitError: break
                        except Exception: continue
                except Exception: continue
                finally: await client.disconnect()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_logic())

        if added > 0:
            total_cost = round(added * PRICE_PER_MEMBER, 2)
            update_balance(uid, -total_cost)
            bot.send_message(uid, f"✅ تم النقل بنجاح!\n➕ العدد المضاف: {added}\n💸 الخصم: {total_cost}$\n💰 الرصيد الباقي: {get_balance(uid)}$")
        else:
            bot.send_message(uid, "❌ فشل النقل. تأكد من الروابط وحالة الحسابات.")
    except:
        bot.send_message(message.chat.id, "⚠️ خطأ في البيانات.")

# --- دوال الشحن وإدارة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="p_auto"), types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="p_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid = call.message.chat.id
    if call.data == "p_auto":
        bot.register_next_step_handler(bot.send_message(uid, "💰 أدخل المبلغ ($):"), create_inv)
    elif call.data == "p_manual":
        bot.send_message(uid, f"💳 **شحن USDT (TRC20)**\n`{MY_WALLET}`\nأرسل صورة التحويل 👇")
        bot.register_next_step_handler(call.message, receive_p)
    elif call.data.startswith("adm_ok"):
        _, _, amt, t_id = call.data.split("_")
        update_balance(int(t_id), float(amt))
        bot.send_message(int(t_id), f"✅ تم شحن {amt}$ في رصيدك!")
        bot.edit_message_caption(f"✅ تم تأكيد شحن {amt}$", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("del_"):
        aid = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("DELETE FROM user_accounts WHERE id=?", (aid,))
        conn.commit()
        conn.close()
        bot.delete_message(call.message.chat.id, call.message.message_id)

def create_inv(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط للدفع", url=res['payLink']))
            bot.send_message(message.chat.id, f"✅ فاتورة بقيمة {amt}$", reply_markup=markup)
    except: bot.send_message(message.chat.id, "⚠️ رقم غير صحيح.")

def receive_p(message):
    if message.content_type == 'photo':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ شحن 5$", callback_data=f"adm_ok_5_{message.chat.id}"), 
                   types.InlineKeyboardButton("✅ شحن 10$", callback_data=f"adm_ok_10_{message.chat.id}"),
                   types.InlineKeyboardButton("✅ شحن 20$", callback_data=f"adm_ok_20_{message.chat.id}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب شحن من: {message.chat.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "⏳ جاري المراجعة من الإدارة...")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_phone(message):
    bot.register_next_step_handler(bot.send_message(message.chat.id, "📱 أرسل الرقم مع رمز الدولة:"), get_otp)

def get_otp(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def run():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(run())
        bot.register_next_step_handler(bot.send_message(message.chat.id, "📩 أرسل كود التحقق:"), final_save, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def final_save(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def run():
        await client.connect()
        await client.sign_in(phone, otp, phone_code_hash=h)
        return client.session.save()
    try:
        fs = asyncio.run(run())
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ تم حفظ الحساب!")
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def del_acc(message):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall()
    conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا توجد حسابات.")
    markup = types.InlineKeyboardMarkup()
    for aid, ph in accs: markup.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(message.chat.id, "اختر الحساب لحذفه:", reply_markup=markup)

init_db()
bot.infinity_polling()
