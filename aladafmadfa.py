import telebot
from telebot import types
import sqlite3
import requests
import asyncio
import threading
import time
from telethon import TelegramClient, functions, types as tel_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.errors import (SessionPasswordNeededError, FloodWaitError, 
                             UserPrivacyRestrictedError, PasswordHashInvalidError,
                             PhoneCodeInvalidError, PeerIdInvalidError)

# ================= [ 🛠️ إعدادات الإمبراطور ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  # آيديك يا ملك
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

# --- 🗄️ تهيئة المخازن (Database) ---
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

# --- 🎯 نظام الاستجابة الفوري (علاج عدم الاستجابة) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # الرد الفوري لتحرير الزر من وضع "التحميل"
    bot.answer_callback_query(call.id)
    uid = call.message.chat.id

    # موافقة المالك (بيانات مختصرة جداً لضمان السرعة)
    if call.data.startswith("ok_"):
        # التنسيق: ok_المبلغ_آيدي
        parts = call.data.split("_")
        amt = float(parts[1])
        t_uid = int(parts[2])
        update_balance(t_uid, amt)
        bot.send_message(t_uid, f"✅ **تم الشحن!**\nأضيفت {amt}$ لرصيدك بنجاح.")
        bot.edit_message_caption(f"✅ تم تأكيد العملية لـ {parts[2]}\nبمبلغ {amt}$", call.message.chat.id, call.message.message_id)

    elif call.data == "p_manual":
        msg = bot.send_message(uid, f"💳 **شحن USDT (TRC20)**\n\nالعنوان:\n`{MY_WALLET}`\n\nأرسل صورة الإيصال هنا 👇")
        bot.register_next_step_handler(msg, process_manual_photo)

    elif call.data == "p_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المطلوب شحنه ($):")
        bot.register_next_step_handler(msg, process_oxapay)

    elif call.data.startswith("del_"):
        acc_id = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("DELETE FROM user_accounts WHERE id=?", (acc_id,))
        conn.commit()
        conn.close()
        bot.delete_message(uid, call.message.message_id)
        bot.send_message(uid, "🗑️ تم حذف الحساب من جيشك.")

# --- 📸 استقبال صور الشحن ---
def process_manual_photo(message):
    if message.content_type == 'photo':
        u = message.chat.id
        markup = types.InlineKeyboardMarkup()
        # أزرار سريعة للمالك
        markup.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"ok_5_{u}"),
                   types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10_{u}"))
        markup.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"ok_20_{u}"),
                   types.InlineKeyboardButton("✅ 50$", callback_data=f"ok_50_{u}"))
        
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                       caption=f"📩 **طلب شحن جديد**\n👤 المستخدم: `{u}`\n💰 رصيده الحالي: {get_balance(u)}$", 
                       reply_markup=markup)
        bot.send_message(u, "⏳ تم إرسال الإثبات بنجاح. سيتم التفعيل فور مراجعة المالك.")
    else:
        bot.send_message(message.chat.id, "⚠️ يرجى إرسال صورة الإيصال فقط.")

# --- ⚔️ محرك النقل والنبش (الأسطورة) ---
async def start_transfer_engine(uid, src_link, trg_link, count, status_mid):
    conn = sqlite3.connect('mega_bot.db')
    accounts = conn.execute("SELECT session_string, phone FROM user_accounts WHERE user_id=?", (uid,)).fetchall()
    conn.close()
    
    if not accounts: return
    
    added_total = 0
    clients = []
    
    # تحضير الجيش
    for session_str, phone in accounts:
        cl = TelegramClient(StringSession(session_str), MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            if await cl.is_user_authorized():
                clients.append(cl)
        except: continue

    if not clients:
        bot.send_message(uid, "❌ جميع حساباتك لا تعمل. أعد إضافتها.")
        return

    # الانضمام والنبش
    target_users = set()
    for cl in clients:
        try:
            s_entity = await cl.get_entity(src_link)
            t_entity = await cl.get_entity(trg_link)
            await cl(JoinChannelRequest(s_entity))
            await cl(JoinChannelRequest(t_entity))
            
            # نبش من قائمة الأعضاء + الرسائل الأخيرة
            async for u in cl.iter_participants(s_entity, limit=200):
                if not u.bot: target_users.add(u.id)
            async for m in cl.iter_messages(s_entity, limit=200):
                if m.sender_id and m.sender_id not in target_users: target_users.add(m.sender_id)
        except: continue

    # عملية النقل المتناوب
    user_list = list(target_users)
    while added_total < count and user_list:
        for cl in clients:
            if added_total >= count or not user_list: break
            u_to_add = user_list.pop(0)
            try:
                await cl(InviteToChannelRequest(t_entity, [u_to_add]))
                added_total += 1
                if added_total % 5 == 0:
                    try: bot.edit_message_text(f"⏳ جاري النقل... تم إضافة {added_total} عضو بنجاح.", uid, status_mid)
                    except: pass
                await asyncio.sleep(2) # تأخير بسيط لتجنب الحظر
            except FloodWaitError as e:
                clients.remove(cl) # الحساب تعب، نطلعه من الدورة
                break
            except: continue
        if not clients: break

    # الخاتمة والخصم
    final_cost = round(added_total * PRICE_PER_MEMBER, 2)
    update_balance(uid, -final_cost)
    bot.send_message(uid, f"✅ **اكتمل الغزو!**\n➕ الأعضاء المضافين: {added_total}\n💸 التكلفة: {final_cost}$\n💰 رصيدك المتبقي: {get_balance(uid)}$")

def transfer_thread_starter(uid, src, trg, count, mid):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_transfer_engine(uid, src, trg, count, mid))

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def init_transfer(message):
    uid = message.chat.id
    if get_balance(uid) < PRICE_PER_MEMBER:
        return bot.send_message(uid, "❌ رصيدك غير كافٍ، اشحن أولاً.")
    
    msg = bot.send_message(uid, "📦 **أرسل رابط المجموعة المصدر (التي سنسحب منها):**")
    bot.register_next_step_handler(msg, step_2_target)

def step_2_target(message):
    source = message.text.strip()
    msg = bot.send_message(message.chat.id, "🎯 **أرسل رابط مجموعتك (الهدف):**")
    bot.register_next_step_handler(msg, step_3_count, source)

def step_3_count(message, source):
    target = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔢 **كم العدد المطلوب نقله؟**")
    bot.register_next_step_handler(msg, final_check, source, target)

def final_check(message, source, target):
    try:
        req = int(message.text)
        uid = message.chat.id
        max_allowed = int(get_balance(uid) / PRICE_PER_MEMBER)
        final_todo = min(req, max_allowed)
        
        status = bot.send_message(uid, f"🚀 جاري تجهيز الجيش لنقل {final_todo} عضو...")
        threading.Thread(target=transfer_thread_starter, args=(uid, source, target, final_todo, status.message_id)).start()
    except:
        bot.send_message(message.chat.id, "⚠️ يرجى إدخال رقم صحيح.")

# --- 📱 إضافة الحسابات وفك الـ 2FA (الكاملة) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات للنقل")
def add_acc_start(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل رقم الهاتف (مثال: +9665xxxxx):")
    bot.register_next_step_handler(msg, add_acc_otp)

def add_acc_otp(message):
    phone = message.text.strip().replace(" ", "")
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_code():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(get_code())
        msg = bot.send_message(message.chat.id, "📩 أرسل كود التحقق الذي وصلك:")
        bot.register_next_step_handler(msg, add_acc_verify, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def add_acc_verify(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_in():
        await client.connect()
        try:
            await client.sign_in(phone, otp, phone_code_hash=h)
            return "OK", client.session.save()
        except SessionPasswordNeededError:
            return "2FA", client.session.save()
    try:
        status, fs = asyncio.run(log_in())
        if status == "OK":
            save_acc_to_db(message.chat.id, fs, phone)
            bot.send_message(message.chat.id, "✅ تم ربط الحساب بنجاح!")
        else:
            msg = bot.send_message(message.chat.id, "🔐 الحساب محمي بكلمة سر (التحقق بخطوتين)، أرسلها الآن:")
            bot.register_next_step_handler(msg, add_acc_password, phone, fs)
    except: bot.send_message(message.chat.id, "❌ الكود خاطئ أو منتهي.")

def add_acc_password(message, phone, s):
    pwd = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_in_pwd():
        await client.connect()
        await client.sign_in(password=pwd)
        return client.session.save()
    try:
        fs = asyncio.run(log_in_pwd())
        save_acc_to_db(message.chat.id, fs, phone)
        bot.send_message(message.chat.id, "✅ تم فك القفل وربط الحساب!")
    except: bot.send_message(message.chat.id, "❌ كلمة السر خاطئة.")

def save_acc_to_db(uid, s, p):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (uid, s, p))
    conn.commit()
    conn.close()

# --- 🏠 بقية الوظائف (ستارت، حذف، شحن تلقائي) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👤 حسابي", "🔄 بدء نقل أعضاء")
    markup.add("➕ إضافة حسابات للنقل", "🗑️ حذف حساباتي")
    markup.add("💰 شحن الرصيد")
    bot.send_message(message.chat.id, f"🐲 **مرحباً بك في دراجون النسخة العملاقة**\n💰 رصيدك: `{get_balance(message.chat.id)}$`", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def show_acc(message):
    uid = message.chat.id
    conn = sqlite3.connect('mega_bot.db')
    count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"📊 **معلوماتك:**\n🆔 آيدي: `{uid}`\n💰 رصيد: `{get_balance(uid)}$`\n📱 حساباتك: `{count}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="p_auto"),
               types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="p_manual"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

def process_oxapay(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط للدفع الآمن", url=res['payLink']))
            bot.send_message(message.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$", reply_markup=btn)
    except: bot.send_message(message.chat.id, "⚠️ خطأ في المبلغ.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساباتي")
def list_accounts_to_del(message):
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall()
    conn.close()
    if not accs: return bot.send_message(message.chat.id, "❌ لا توجد حسابات مسجلة.")
    markup = types.InlineKeyboardMarkup()
    for aid, phone in accs:
        markup.add(types.InlineKeyboardButton(f"❌ {phone}", callback_data=f"del_{aid}"))
    bot.send_message(message.chat.id, "اختر الحساب الذي تريد حذفه من الجيش:", reply_markup=markup)

init_db()
print("🐲 الوحش استيقظ.. النسخة الكاملة تعمل الآن!")
bot.infinity_polling()
