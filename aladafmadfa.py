import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import User

# ================= [ 🛠️ الإعدادات الرسمية ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
API_ID = 23269382
API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" # مفتاح الشحن التلقائي
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

DB_PATH = '/app/data/dragon_official.db' if os.path.exists('/app/data') else 'dragon_official.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=200)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=60)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

# تهيئة الجداول
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')
db_manage('CREATE TABLE IF NOT EXISTS memory (target_id INTEGER PRIMARY KEY)')

# --- 🚀 محرك النقل الذكي ---
async def dragon_v33_engine(uid, source, target, requested, mid):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    curr_bal = float(res[0][0]) if res else 0.0
    if curr_bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"⚠️ رصيدك ({curr_bal:.2f}$) لا يكفي.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.edit_message_text("❌ لم تربط حسابات سحب!", uid, mid)
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients: return bot.edit_message_text("❌ جلسات الحسابات منتهية.", uid, mid)

    added = 0
    bot.edit_message_text("📡 جاري مسح المجموعة المصدر واستخراج الأعضاء...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        targets = []
        async for message in scrapper.iter_messages(source, limit=1000):
            if len(targets) >= requested: break
            sender = await message.get_sender()
            if isinstance(sender, User) and not sender.bot:
                targets.append(sender)

        bot.edit_message_text(f"⚔️ تم تجهيز {len(targets)} هدف. بدأ النقل...", uid, mid)

        for user in targets:
            if added >= requested: break
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    bot.edit_message_text(f"📊 **التقدم**\n✅ نقل: {added}/{requested}\n💰 رصيدك: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(30, 50))
                    break 
                except: continue
    except Exception as e: bot.send_message(uid, f"ℹ️ انتهى: {e}")

# --- 💰 نظام الشحن التلقائي واليدوي ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي (OxaPay)", callback_data="pay_auto"))
    kb.row(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, f"💎 **قسم التمويل والشحن**\n\nاختر وسيلة الشحن المناسبة لك:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid = c.message.chat.id
    if c.data == "pay_manual":
        bot.send_message(uid, f"📍 حول لمحافظنا (TRC20):\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا.")
    elif c.data == "pay_auto":
        msg = bot.send_message(uid, "💵 أدخل المبلغ المطلوب شحنه بالدولار (مثال: 10):")
        bot.register_next_step_handler(msg, oxapay_request)
    elif c.data.startswith("ok_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"⭐ تم شحن {amt}$ برصيدك بنجاح!")
        bot.edit_message_caption(f"✅ تم التأكيد لـ {target}", uid, c.message.message_id)

def oxapay_request(m):
    try:
        amount = float(m.text)
        data = {
            'merchant': OXAPAY_KEY,
            'amount': amount,
            'currency': 'USD',
            'lifeTime': 30,
            'callbackUrl': 'https://google.com' # يمكنك وضع رابطك الخاص هنا
        }
        r = requests.post("https://api.oxapay.com/merchants/request", json=data).json()
        if r.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع الفوري", url=r['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amount}$\nالرابط صالح لمدة 30 دقيقة:", reply_markup=kb)
        else:
            bot.send_message(m.chat.id, "❌ فشل إنشاء رابط الدفع، يرجى المحاولة لاحقاً.")
    except:
        bot.send_message(m.chat.id, "⚠️ يرجى إدخال مبلغ صحيح.")

# --- 📱 القوائم الرئيسية ---
def main_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"🐲 **مرحباً بك في Dragon V33**\n💰 رصيدك الموثق: `{bal:.2f}$`", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n💰 الرصيد: `{bal:.2f}$`")

@bot.message_handler(content_types=['photo'])
def receipt(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10.0_{m.chat.id}"),
        types.InlineKeyboardButton("✅ 20$", callback_data=f"ok_20.0_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري مراجعة إيصالك...")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def move_init(m):
    msg = bot.send_message(m.chat.id, "📦 المصدر (بدون @):")
    bot.register_next_step_handler(msg, step1)

def step1(m):
    s = m.text
    msg = bot.send_message(m.chat.id, "🎯 مجموعتك (بدون @):")
    bot.register_next_step_handler(msg, step2, s)

def step2(m, s):
    t = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد:")
    bot.register_next_step_handler(msg, step3, s, t)

def step3(m, s, t):
    try:
        num = int(m.text); mid = bot.send_message(m.chat.id, "⏳ جاري البدء...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v33_engine(m.chat.id, s, t, num, mid))).start()
    except: pass

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_a1(m):
    bot.register_next_step_handler(bot.send_message(m.chat.id, "📱 الرقم (+...):"), add_a2)

def add_a2(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), API_ID, API_HASH)
    async def con(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(con())
        bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), add_a3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_a3(m, p, h, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def log():
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except errors.SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(log())
    if res == "OK": 
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الربط.")
    elif res == "2FA":
        bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 باسوورد التحقق بخطوتين:"), add_a4, p, fs)

def add_a4(m, p, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def log2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(log2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم مسح حساباتك.")

bot.infinity_polling()
