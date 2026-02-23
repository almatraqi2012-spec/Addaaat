import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent
from telethon.errors import *

# ================= [ 🛠️ الإعدادات الحقيقية ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=40)

# --- 🗄️ محرك قاعدة البيانات (الحفظ الفوري) ---
def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_master_v6.db', check_same_thread=False)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        res = cur.fetchall() if fetch else None
        conn.commit()
        return res
    except Exception as e:
        print(f"DB Error: {e}")
        return None
    finally:
        conn.close()

# تهيئة الجداول
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- ⚔️ محرك النقل الذكي (الواقعي) ---
async def transfer_worker(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs:
        return bot.send_message(uid, "❌ لا توجد حسابات! أضف حساباتك أولاً.")

    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients:
        return bot.send_message(uid, "❌ جميع حساباتك مسجلة خروج!")

    added = 0
    try:
        leader = clients[0]
        s_ent = await leader.get_entity(source)
        t_ent = await leader.get_entity(target)
        await leader(JoinChannelRequest(s_ent))
        await leader(JoinChannelRequest(t_ent))
        
        async for user in leader.iter_participants(s_ent, limit=requested*2, aggressive=True):
            if added >= requested: break
            
            # فحص الرصيد الحي
            bal = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0]
            if bal < PRICE_PER_MEMBER:
                bot.send_message(uid, "⚠️ توقف! رصيدك غير كافٍ للاستمرار.")
                break

            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(t_ent, [user]))
                    # التحقق من الوجود الفعلي بالعضوية
                    check = await cl(GetParticipantsRequest(t_ent, ChannelParticipantsRecent(), 0, 5, hash=0))
                    if any(p.id == user.id for p in check.users):
                        added += 1
                        db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                        bot.edit_message_text(f"🚀 جاري الغزو الحقيقي...\n✅ مضافين: {added}\n💰 الرصيد: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                        await asyncio.sleep(4)
                        break
                except: continue
                
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ تقني: {e}")
    
    bot.send_message(uid, f"🏁 المهمة انتهت!\n✅ الأعضاء الجدد فعلياً: {added}")

# --- 🎯 معالج الأزرار الاستجابة الفورية ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id)
    uid = call.message.chat.id

    if call.data.startswith("ok_"):
        _, amt, target = call.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, target))
        bot.send_message(target, f"✅ تم شحن {amt}$ لرصيدك!")
        bot.edit_message_caption(f"✅ تم تأكيد الشحن لـ {target}", uid, call.message.message_id)

    elif call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ ($):")
        bot.register_next_step_handler(msg, oxapay_start)

    elif call.data == "pay_manual":
        bot.send_message(uid, f"💳 حول لعنوان TRC20:\n`{MY_WALLET}`\nثم أرسل صورة الإيصال هنا:")

# --- 📱 إضافة الحسابات (شامل التحقق بخطوتين) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc_1(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع المفتاح (مثال: +9665xxxxx):")
    bot.register_next_step_handler(msg, add_acc_2)

def add_acc_2(m):
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def connect():
        await cl.connect()
        r = await cl.send_code_request(phone)
        return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        msg = bot.send_message(m.chat.id, "📩 أرسل الكود الذي وصلك:")
        bot.register_next_step_handler(msg, add_acc_3, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_acc_3(m, p, h, s):
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def sign():
        await cl.connect()
        try:
            await cl.sign_in(p, otp, phone_code_hash=h)
            return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    try:
        res, fs = asyncio.run(sign())
        if res == "OK":
            db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
            bot.send_message(m.chat.id, "✅ تم الربط بنجاح!")
        elif res == "2FA":
            msg = bot.send_message(m.chat.id, "🔐 الحساب محمي، أرسل كلمة السر:")
            bot.register_next_step_handler(msg, add_acc_final, p, fs)
    except: bot.send_message(m.chat.id, "❌ الكود خاطئ.")

def add_acc_final(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login_2fa():
        await cl.connect()
        await cl.sign_in(password=m.text.strip())
        return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم فك التشفير والربط!")
    except: bot.send_message(m.chat.id, "❌ كلمة السر خاطئة.")

# --- 🏠 الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    kb.row("➕ إضافة حسابات", "💰 شحن الرصيد")
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **مرحباً بك في دراجون V6 الخارق**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"📊 **معلوماتك:**\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المربوطة: `{count}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="pay_auto"), types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def tr_start(m):
    if db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0] < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك صفر!")
    bot.send_message(m.chat.id, "📦 رابط المصدر:")
    bot.register_next_step_handler(m, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 العدد المطلوب:"), tr_final, m1.text, m2.text)))

def tr_final(m, s, t):
    try:
        c = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري التحقق والنقل...").message_id
        threading.Thread(target=lambda: asyncio.run(transfer_worker(m.chat.id, s, t, c, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقم فقط.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10_{m.chat.id}"), types.InlineKeyboardButton("✅ 25$", callback_data=f"ok_25_{m.chat.id}"))
    kb.add(types.InlineKeyboardButton("✅ 50$", callback_data=f"ok_50_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال الإيصال للمراجعة.")

def oxapay_start(m):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': float(m.text), 'currency': 'USD'}).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, "💳 ادفع عبر الرابط:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("رابط الدفع", url=res['payLink'])))
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

# تشغيل البوت
print("🚀 دراجون V6 انطلق! الكود الآن خارق ومستقر.")
bot.infinity_polling()
