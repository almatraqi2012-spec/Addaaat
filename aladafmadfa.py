import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import User, PeerUser

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
API_ID = 23269382
API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

DB_PATH = '/app/data/dragon_v23.db' if os.path.exists('/app/data') else 'dragon_v23.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=60)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

# تهيئة الجداول (إضافة جدول الذاكرة لمنع التكرار)
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')
db_manage('CREATE TABLE IF NOT EXISTS memory (target_id INTEGER PRIMARY KEY)')

# --- 🎯 محرك الرادار العميق ومانع التكرار ---
async def dragon_v23_radar_engine(uid, source, target, requested, mid):
    # 1. فحص الرصيد والحسابات
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    bal = float(res[0][0]) if res else 0.0
    if bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"❌ رصيدك {bal:.2f}$ لا يكفي.", uid, mid)

    acc_data = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not acc_data: return bot.edit_message_text("❌ أضف حسابات أولاً!", uid, mid)
    
    clients = []
    for s in acc_data:
        c = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await c.connect()
        if await c.is_user_authorized(): clients.append(c)

    if not clients: return bot.edit_message_text("❌ الحسابات معطلة!", uid, mid)

    added_total = 0
    blacklist = [row[0] for row in db_manage("SELECT target_id FROM memory", fetch=True)]
    
    bot.edit_message_text(f"📡 جاري تشغيل الرادار العميق في {source}...", uid, mid)
    
    try:
        # صيد الأهداف من الرسائل (مثل سكربت سهم)
        scrapper = random.choice(clients)
        targets = []
        async for message in scrapper.iter_messages(source, limit=3000):
            if len(targets) >= (requested + 50): break
            if message.sender_id and message.sender_id not in blacklist:
                sender = await message.get_sender()
                if isinstance(sender, User) and not sender.bot:
                    if sender.id not in [u.id for u in targets]:
                        targets.append(sender)
        
        if not targets: return bot.edit_message_text("❌ الرادار لم يجد أهدافاً جديدة.", uid, mid)
        
        bot.edit_message_text(f"⚔️ تم صيد {len(targets)} هدف جديد. بدأ الغزو الموزع...", uid, mid)

        # الإضافة الموزعة (نظام المداورة)
        for user in targets:
            if added_total >= requested: break
            
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added_total += 1
                    # حفظ في الذاكرة لمنع التكرار للأبد
                    db_manage("INSERT OR IGNORE INTO memory (target_id) VALUES (?)", (user.id,))
                    # خصم الرصيد
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    
                    bot.edit_message_text(f"🚀 **إعصار سهم & دراجون**\n✅ مضاف: {added_total}/{requested}\n💰 الرصيد: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$", uid, mid)
                    
                    await asyncio.sleep(random.randint(30, 60)) # وقت الأمان
                    break 
                except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
                    db_manage("INSERT OR IGNORE INTO memory (target_id) VALUES (?)", (user.id,))
                    break
                except errors.FloodWaitError:
                    clients.remove(cl)
                    continue
                except: continue

    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    bot.send_message(uid, f"🏁 انتهى النقل!\n✅ مضاف: {added_total}\n💰 رصيدك: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$")

# --- 🛠️ الوظائف الإدارية (الشحن، الحسابات، الحذف) ---

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    bal = float(db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0])
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    kb.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    kb.row("💰 شحن الرصيد")
    bot.send_message(m.chat.id, f"🐲 **دراجون V23 - نظام الرادار**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم مسح جميع حساباتك.")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_m(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("⚡ تلقائي (Oxapay)", callback_data="pay_auto"),
        types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="pay_manual")
    )
    bot.send_message(m.chat.id, "اختر وسيلة الدفع:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    if c.data == "pay_manual":
        bot.send_message(c.message.chat.id, f"💳 عنوان TRC20:\n`{MY_WALLET}`\nارسل صورة الإيصال.")
    elif c.data == "pay_auto":
        msg = bot.send_message(c.message.chat.id, "💰 المبلغ ($):")
        bot.register_next_step_handler(msg, oxa_pay)
    elif c.data.startswith("ok_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تم شحن {amt}$!")
    bot.answer_callback_query(c.id)

def oxa_pay(m):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': float(m.text), 'currency': 'USD'}).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, f"🔗 رابط الدفع: {res['payLink']}")
    except: pass

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def raid_init(m):
    msg = bot.send_message(m.chat.id, "📦 يوزر المصدر (بدون @):")
    bot.register_next_step_handler(msg, r1)

def r1(m):
    s = m.text
    msg = bot.send_message(m.chat.id, "🎯 يوزر مجموعتك (بدون @):")
    bot.register_next_step_handler(msg, r2, s)

def r2(m, s):
    t = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد:")
    bot.register_next_step_handler(msg, r3, s, t)

def r3(m, s, t):
    try:
        req = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري تشغيل المحرك...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v23_radar_engine(m.chat.id, s, t, req, mid))).start()
    except: pass

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def acc1(m):
    msg = bot.send_message(m.chat.id, "📱 الرقم (+966...):")
    bot.register_next_step_handler(msg, acc2)

def acc2(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), API_ID, API_HASH)
    async def c(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(c())
        bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), acc3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌: {e}")

def acc3(m, p, h, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def l(): 
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except errors.SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(l())
    if res == "OK": 
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم!")
    elif res == "2FA":
        bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 الباسوورد:"), acc4, p, fs)

def acc4(m, p, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def l2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(l2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{bal:.2f}$`")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup().row(types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10.0_{m.chat.id}"), types.InlineKeyboardButton("✅ 20$", callback_data=f"ok_20.0_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب من `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري المراجعة...")

bot.infinity_polling()
