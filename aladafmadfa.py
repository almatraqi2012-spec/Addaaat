import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import threading
import time
import os
from telethon import TelegramClient, functions, types as tel_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import (SessionPasswordNeededError, FloodWaitError, 
                             UserPrivacyRestrictedError, PasswordHashInvalidError,
                             PhoneCodeInvalidError, PeerIdInvalidError, RPCError)

# ================= [ 🛠️ الإعدادات النهائية ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=30)

# --- 🗄️ نظام إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_accounts 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                      session_string TEXT, phone TEXT)''')
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

# --- 🎯 محرك الاستجابة الفوري (للمالك والمستخدم) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_global_callbacks(call):
    # الرد الفوري لتحرير الزر من وضع الانتظار
    try: bot.answer_callback_query(call.id)
    except: pass
    
    uid = call.message.chat.id

    # 1. نظام شحن المالك
    if call.data.startswith("confirm_charge_"):
        try:
            _, _, amt, target_id = call.data.split("_")
            update_balance(int(target_id), float(amt))
            bot.send_message(int(target_id), f"✅ **تم الشحن بنجاح!**\nتم إضافة {amt}$ إلى رصيدك من قِبل الإدارة.")
            bot.edit_message_caption(f"✅ تم تنفيذ الطلب لـ {target_id}\nالمبلغ: {amt}$", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ خطأ في معالجة الشحن: {e}")

    # 2. حذف الحسابات
    elif call.data.startswith("terminate_"):
        acc_id = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("DELETE FROM user_accounts WHERE id=?", (acc_id,))
        conn.commit()
        conn.close()
        bot.delete_message(uid, call.message.message_id)
        bot.send_message(uid, "🗑️ تم حذف الحساب بنجاح.")

    # 3. خيارات الدفع
    elif call.data == "method_manual":
        msg = bot.send_message(uid, f"💳 **شحن يدوي USDT (TRC20)**\n\nالعنوان:\n`{MY_WALLET}`\n\nأرسل صورة الإيصال هنا 👇")
        bot.register_next_step_handler(msg, handle_manual_payment_photo)

    elif call.data == "method_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المطلوب بالدولار ($):")
        bot.register_next_step_handler(msg, handle_auto_invoice)

# --- 📸 معالجة صور الشحن (نظام المالك البديل) ---
def handle_manual_payment_photo(message):
    if message.content_type == 'photo':
        uid = message.chat.id
        markup = types.InlineKeyboardMarkup()
        # بيانات مختصرة لضمان عمل الأزرار حتى مع التقييد
        markup.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"confirm_charge_5_{uid}"),
                   types.InlineKeyboardButton("✅ 10$", callback_data=f"confirm_charge_10_{uid}"))
        markup.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"confirm_charge_20_{uid}"),
                   types.InlineKeyboardButton("✅ 50$", callback_data=f"confirm_charge_50_{uid}"))
        
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=f"📩 **طلب شحن جديد**\n👤 المستخدم: `{uid}`\n💰 رصيده الحالي: {get_balance(uid)}$", 
                       reply_markup=markup)
        bot.send_message(uid, "⏳ تم إرسال إثباتك. سيتم التفعيل فور مراجعة المالك.")
    else:
        bot.send_message(message.chat.id, "⚠️ يرجى إرسال صورة فقط.")

# --- ⚔️ محرك النقل والنبش (النسخة الكاملة) ---
async def deep_transfer_worker(uid, source_url, target_url, amount, status_msg_id):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT session_string, phone FROM user_accounts WHERE user_id=?", (uid,)).fetchall()
    conn.close()
    
    if not accs: return

    successful_adds = 0
    active_clients = []
    
    # تحضير الجيش وفحص الحسابات
    for session_str, phone in accs:
        client = TelegramClient(StringSession(session_str), MY_API_ID, MY_API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                active_clients.append(client)
        except: continue

    if not active_clients:
        bot.send_message(uid, "❌ جميع حساباتك لا تعمل حالياً. يرجى إعادة إضافتها.")
        return

    # الانضمام والنبش العميق (أعضاء + رسائل)
    target_pool = set()
    try:
        # استخدام أول حساب لسحب الأعضاء
        leader = active_clients[0]
        s_ent = await leader.get_entity(source_url)
        t_ent = await leader.get_entity(target_url)
        
        await leader(JoinChannelRequest(s_ent))
        await leader(JoinChannelRequest(t_ent))
        
        # نبش القائمة
        async for user in leader.iter_participants(s_ent, limit=500):
            if not user.bot: target_pool.add(user.id)
        
        # نبش الرسائل (في حال كانت القائمة مخفية)
        async for msg in leader.iter_messages(s_ent, limit=200):
            if msg.sender_id and msg.sender_id not in target_pool:
                target_pool.add(msg.sender_id)
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ في الوصول للمجموعات: {e}")
        return

    # عملية النقل المتناوب (Round Robin)
    user_list = list(target_pool)
    while successful_adds < amount and user_list:
        for client in active_clients:
            if successful_adds >= amount or not user_list: break
            current_user = user_list.pop(0)
            try:
                await client(InviteToChannelRequest(t_ent, [current_user]))
                successful_adds += 1
                if successful_adds % 5 == 0:
                    try: bot.edit_message_text(f"⏳ جاري النقل... تم إضافة {successful_adds} عضو بنجاح.", uid, status_msg_id)
                    except: pass
                await asyncio.sleep(2.5) # حماية من الحظر
            except FloodWaitError:
                active_clients.remove(client) # الحساب أُرهق
                break
            except (UserPrivacyRestrictedError, PeerIdInvalidError):
                continue
            except RPCError:
                continue

    # الخاتمة والخصم المالي
    cost = round(successful_adds * PRICE_PER_MEMBER, 2)
    update_balance(uid, -cost)
    bot.send_message(uid, f"✅ **اكتملت العملية!**\n➕ الأعضاء المضافين: {successful_adds}\n💸 الخصم: {cost}$\n💰 رصيدك الحالي: {get_balance(uid)}$")

def start_transfer_process(uid, src, trg, count, mid):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(deep_transfer_worker(uid, src, trg, count, mid))

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def main_transfer_flow(message):
    uid = message.chat.id
    if get_balance(uid) < PRICE_PER_MEMBER:
        return bot.send_message(uid, "❌ رصيدك كافٍ للنقل. يرجى الشحن أولاً.")
    
    msg = bot.send_message(uid, "📦 **أرسل رابط المجموعة المصدر:**")
    bot.register_next_step_handler(msg, lambda m: bot.register_next_step_handler(bot.send_message(uid, "🎯 **أرسل رابط مجموعتك (الهدف):**"), lambda m2: bot.register_next_step_handler(bot.send_message(uid, "🔢 **كم العدد المطلوب؟**"), finalize_war, m.text, m2.text)))

def finalize_war(message, src, trg):
    try:
        count = int(message.text)
        uid = message.chat.id
        affordable = int(get_balance(uid) / PRICE_PER_MEMBER)
        final_count = min(count, affordable)
        
        status = bot.send_message(uid, f"🚀 بدأنا غزو {final_count} عضو.. يرجى الانتظار.")
        threading.Thread(target=start_transfer_process, args=(uid, src, trg, final_count, status.message_id)).start()
    except:
        bot.send_message(message.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# --- 📱 إضافة الحسابات مع فك التحقق بخطوتين (كاملة) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_account_init(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل رقم الهاتف مع رمز الدولة (مثال: +966...):")
    bot.register_next_step_handler(msg, add_account_otp_request)

def add_account_otp_request(message):
    phone = message.text.strip().replace(" ", "")
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(get_h())
        msg = bot.send_message(message.chat.id, "📩 أرسل كود التحقق الذي وصلك:")
        bot.register_next_step_handler(msg, add_account_verify, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_account_verify(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def sign_in():
        await client.connect()
        try:
            await client.sign_in(phone, otp, phone_code_hash=h)
            return "OK", client.session.save()
        except SessionPasswordNeededError:
            return "2FA", client.session.save()
    try:
        status, fs = asyncio.run(sign_in())
        if status == "OK":
            save_acc(message.chat.id, fs, phone)
            bot.send_message(message.chat.id, "✅ تم ربط الحساب بنجاح!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 الحساب محمي بالتحقق بخطوتين. أرسل كلمة السر:")
            bot.register_next_step_handler(msg, add_account_password, phone, fs)
    except: bot.send_message(message.chat.id, "❌ الكود خاطئ.")

def add_account_password(message, phone, s):
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
    except: bot.send_message(message.chat.id, "❌ كلمة السر خاطئة.")

def save_acc(uid, s, p):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (uid, s, p))
    conn.commit()
    conn.close()

# --- 🏠 الأوامر العامة ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي")
    markup.add("💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 **مرحباً بك في دراجون بوت**\n💰 رصيدك: `{get_balance(message.chat.id)}$`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def show_my_account(message):
    uid = message.chat.id
    conn = sqlite3.connect('mega_bot.db')
    count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"📊 **معلومات الحساب:**\n🆔 الآيدي: `{uid}`\n💰 الرصيد: `{get_balance(uid)}$`\n📱 جيش الحسابات: `{count}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="method_auto"),
               types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="method_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

def handle_auto_invoice(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 ادفع الآن", url=res['payLink']))
            bot.send_message(message.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$", reply_markup=btn)
    except: bot.send_message(message.chat.id, "⚠️ المبلغ غير صحيح.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def list_for_deletion(message):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall()
    conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا توجد حسابات.")
    markup = types.InlineKeyboardMarkup()
    for aid, phone in accs:
        markup.add(types.InlineKeyboardButton(f"❌ {phone}", callback_data=f"terminate_{aid}"))
    bot.send_message(message.chat.id, "اختر الحساب لحذفه:", reply_markup=markup)

# --- 🚀 الإقلاع ---
init_db()
print("🔥 دراجون النسخة الكاملة انطلق الآن..")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
