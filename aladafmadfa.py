import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import User, PeerUser
from telethon.errors import *

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

DB_PATH = '/app/data/dragon_v22.db' if os.path.exists('/app/data') else 'dragon_v22.db'
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

# إنشاء الجداول
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- 🚀 محرك النقل المتطور ---
async def dragon_v22_worker(uid, source, target, requested, mid):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    bal = float(res[0][0]) if res else 0.0
    if bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"❌ رصيدك {bal:.2f}$ لا يكفي لنقل {requested} عضو.", uid, mid)

    acc_data = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not acc_data: return bot.edit_message_text("❌ لم تضف أي حسابات نبش!", uid, mid)
    
    clients = []
    for s in acc_data:
        c = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await c.connect()
        if await c.is_user_authorized(): clients.append(c)

    if not clients: return bot.edit_message_text("❌ الحسابات المرتبطة معطلة، أعد ربطها.", uid, mid)

    added = 0
    bot.edit_message_text(f"🔍 جاري سحب الأعضاء من {source}...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        src_ent = await scrapper.get_entity(source)
        trg_ent = await scrapper.get_entity(target)

        p = await scrapper.get_participants(src_ent, limit=1000)
        targets = [u for u in p if isinstance(u, User) and not u.bot and not u.deleted]
        random.shuffle(targets)

        bot.edit_message_text(f"🔥 تم صيد {len(targets)} هدف متفاعل. بدأ الغزو!", uid, mid)

        for user in targets:
            if added >= requested: break
            
            # محاولة الإضافة بالتناوب بين الحسابات
            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(trg_ent, [user]))
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    
                    if added % 1 == 0:
                        bot.edit_message_text(f"✅ تم إضافة: {added}/{requested}\n💰 المتبقي: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$", uid, mid)
                    
                    await asyncio.sleep(random.randint(15, 25))
                    break 
                except (UserPrivacyRestrictedError, UserNotMutualContactError): break
                except (FloodWaitError, PeerFloodError): continue 
                except Exception: continue

    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    bot.send_message(uid, f"🏁 اكتمل النقل!\n✅ مضاف فعلياً: {added}\n💰 الرصيد: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$")

# --- ⌨️ لوحات التحكم ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

# --- 💰 نظام الشحن (تلقائي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="pay_auto"),
           types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المفضلة:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = c.message.chat.id
    if c.data == "pay_manual":
        bot.send_message(uid, f"💳 حول لعنوان TRC20 التالي:\n`{MY_WALLET}`\nارسل صورة الإيصال بعد التحويل.")
    elif c.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار ($):")
        bot.register_next_step_handler(msg, oxapay_logic)
    elif c.data.startswith("confirm_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تم شحن {amt}$ لرصيدك!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", uid, c.message.message_id)
    bot.answer_callback_query(c.id)

def oxapay_logic(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ فاتورة شحن {amt}$ جاهزة:", reply_markup=kb)
    except: bot.send_message(m.chat.id, "⚠️ أدخل أرقام فقط.")

# --- 📱 إدارة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def start_add(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع مفتاح الدولة (مثال: +966...):")
    bot.register_next_step_handler(msg, add_step_2)

def add_step_2(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def connect(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        msg = bot.send_message(m.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, add_step_3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_step_3(m, p, h, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(login())
    if res == "OK": 
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح!")
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 أرسل باسوورد التحقق بخطوتين:")
        bot.register_next_step_handler(msg, add_step_4, p, fs)

def add_step_4(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_2fa(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    try:
        fs = asyncio.run(log_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الربط بنجاح!")
    except: bot.send_message(m.chat.id, "❌ الباسوورد خاطئ.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def delete_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم مسح جميع حساباتك المرتبطة بالبوت.")

# --- 🏠 الأوامر العامة ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في دراجون V22**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"👤 **بيانات حسابك:**\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المرتبطة: `{count}`")

@bot.message_handler(content_types=['photo'])
def handle_manual_pay(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✅ 10$", callback_data=f"confirm_10.0_{m.chat.id}"),
        types.InlineKeyboardButton("✅ 20$", callback_data=f"confirm_20.0_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال شحن من `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال الإيصال للمراجعة.")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def init_raid(m):
    msg = bot.send_message(m.chat.id, "📦 أرسل رابط المصدر:")
    bot.register_next_step_handler(msg, step_1)

def step_1(m):
    s = m.text
    msg = bot.send_message(m.chat.id, "🎯 أرسل رابط مجموعتك:")
    bot.register_next_step_handler(msg, step_2, s)

def step_2(m, s):
    t = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد المطلوب:")
    bot.register_next_step_handler(msg, step_3, s, t)

def step_3(m, s, t):
    try:
        req = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري التحضير...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v22_worker(m.chat.id, s, t, req, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقم صحيح.")

bot.infinity_polling()
