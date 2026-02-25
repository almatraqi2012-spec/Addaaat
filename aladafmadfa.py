import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import User

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
API_ID = 23269382
API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# المسار لضمان الحفظ في Railway
DB_PATH = '/app/data/dragon_final.db' if os.path.exists('/app/data') else 'dragon_final.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=150)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=60)
    conn.execute('PRAGMA journal_mode=WAL;') 
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

# إنشاء الجداول
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')
db_manage('CREATE TABLE IF NOT EXISTS memory (target_id INTEGER PRIMARY KEY)')

# --- 🛠️ أوامر الإدارة ---
@bot.message_handler(commands=['add_balance'])
def admin_add(m):
    if m.chat.id == ADMIN_ID:
        try:
            parts = m.text.split()
            tid, amt = int(parts[1]), float(parts[2])
            db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, tid))
            bot.send_message(m.chat.id, f"✅ تم شحن {amt}$ للحساب {tid}")
            bot.send_message(tid, f"⭐ مبروك! أضاف لك الأدمن {amt}$ برصيدك.")
        except: bot.send_message(m.chat.id, "النمط: `/add_balance ID Amount`")

# --- 🚀 محرك النقل (الرادار العميق) ---
async def dragon_v27_engine(uid, source, target, requested, mid):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    bal = float(res[0][0]) if res else 0.0
    if bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"⚠️ رصيدك {bal:.2f}$ لا يكفي.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.edit_message_text("❌ لم تضف حسابات!", uid, mid)
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients: return bot.edit_message_text("❌ الحسابات معطلة.", uid, mid)

    added = 0
    blacklist = [row[0] for row in db_manage("SELECT target_id FROM memory", fetch=True)]
    bot.edit_message_text("📡 الرادار يبحث عن أهداف متفاعلة...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        targets = []
        async for message in scrapper.iter_messages(source, limit=2000):
            if len(targets) >= requested: break
            if message.sender_id and message.sender_id not in blacklist:
                sender = await message.get_sender()
                if isinstance(sender, User) and not sender.bot:
                    if sender.id not in [u.id for u in targets]: targets.append(sender)

        if not targets: return bot.edit_message_text("❌ لم نجد أعضاء جدد.", uid, mid)
        bot.edit_message_text(f"🛡️ صيد {len(targets)} هدف. جاري النقل...", uid, mid)

        for user in targets:
            if added >= requested: break
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added += 1
                    db_manage("INSERT OR IGNORE INTO memory (target_id) VALUES (?)", (user.id,))
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    bot.edit_message_text(f"✅ مضاف: {added}/{requested}\n💰 الرصيد: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(30, 60))
                    break 
                except: continue
    except Exception as e: bot.send_message(uid, f"ℹ️ انتهى: {e}")

# --- 📱 القوائم الرئيسية ---
def main_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 العودة للقائمة")
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"🐲 **Dragon V27 Pro**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n🆔 آيديك: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_choice(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("⚡ تلقائي", callback_data="auto_p"),
        types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="manual_p"))
    bot.send_message(m.chat.id, f"محفظة الإيداع (TRC20):\n`{MY_WALLET}`", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid = c.message.chat.id
    if c.data == "manual_p":
        bot.send_message(uid, "📸 أرسل صورة الإيصال للمراجعة.")
    elif c.data == "auto_p":
        msg = bot.send_message(uid, "المبلغ بالدولار:")
        bot.register_next_step_handler(msg, oxa_gen)
    elif c.data.startswith("confirm_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تم شحن {amt}$ برصيدك!")
        bot.edit_message_caption(f"✅ تم التأكيد لـ {target}", uid, c.message.message_id)

def oxa_gen(m):
    try:
        r = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': float(m.text), 'currency': 'USD'}).json()
        if r.get('payLink'): bot.send_message(m.chat.id, f"🔗 رابط الدفع: {r['payLink']}")
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✅ 10$", callback_data=f"confirm_10.0_{m.chat.id}"),
        types.InlineKeyboardButton("✅ 20$", callback_data=f"confirm_20.0_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري مراجعة إيصالك...")

# --- ➕ إضافة حسابات (مع نظام 2FA الكامل) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc1(m):
    msg = bot.send_message(m.chat.id, "📱 الرقم مع مفتاح الدولة (مثال: +966...):")
    bot.register_next_step_handler(msg, add_acc2)

def add_acc2(m):
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), API_ID, API_HASH)
    async def connect():
        await cl.connect()
        r = await cl.send_code_request(phone)
        return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        msg = bot.send_message(m.chat.id, "📩 الكود:")
        bot.register_next_step_handler(msg, add_acc3, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_acc3(m, p, h, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(p, m.text, phone_code_hash=h)
            return "OK", cl.session.save()
        except errors.SessionPasswordNeededError:
            return "2FA", cl.session.save()
    try:
        res, fs = asyncio.run(login())
        if res == "OK":
            db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
            bot.send_message(m.chat.id, "✅ تم ربط الحساب.")
        elif res == "2FA":
            msg = bot.send_message(m.chat.id, "🔐 أرسل باسوورد التحقق بخطوتين:")
            bot.register_next_step_handler(msg, add_acc4, p, fs)
    except Exception as e: bot.send_message(m.chat.id, f"❌ كود خاطئ: {e}")

def add_acc4(m, p, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def login_2fa():
        await cl.connect()
        await cl.sign_in(password=m.text)
        return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الربط بنجاح.")
    except Exception as e: bot.send_message(m.chat.id, f"❌ الباسوورد خاطئ.")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def start_raid(m):
    msg = bot.send_message(m.chat.id, "📦 المصدر (بدون @):")
    bot.register_next_step_handler(msg, r1)

def r1(m):
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 مجموعتك (بدون @):")
    bot.register_next_step_handler(msg, r2, src)

def r2(m, src):
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد:")
    bot.register_next_step_handler(msg, r3, src, trg)

def r3(m, s, t):
    try:
        req = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري التحضير...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v27_engine(m.chat.id, s, t, req, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ رقم فقط.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم المسح.")

bot.infinity_polling()
