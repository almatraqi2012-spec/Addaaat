import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import User

# ================= [ 🛠️ الإعدادات الرسمية ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
API_ID = 26569209
API_HASH = '1f52802d99787e2213a8089417032724'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# مسار قاعدة البيانات (متوافق مع Volumes ريلوي)
DB_PATH = '/app/data/dragon_official.db' if os.path.exists('/app/data') else 'dragon_official.db'

# ذاكرة حية لحماية الرصيد
LIVE_BALANCES = {}
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=50)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=60)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

# تهيئة النظام
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# تحميل الأرصدة للذاكرة
rows = db_manage("SELECT user_id, balance FROM users", fetch=True)
for r in rows: LIVE_BALANCES[r[0]] = r[1]

def update_bal(uid, amt):
    LIVE_BALANCES[uid] = LIVE_BALANCES.get(uid, 0.0) + amt
    db_manage("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)", (uid, LIVE_BALANCES[uid]))

# --- 🚀 محرك النقل الذكي ---
async def dragon_engine(uid, source, target, requested, mid):
    bal = LIVE_BALANCES.get(uid, 0.0)
    if bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"⚠️ رصيدك ({bal:.2f}$) غير كافٍ.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.edit_message_text("❌ لم تربط حسابات سحب!", uid, mid)
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients: return bot.edit_message_text("❌ الحسابات منتهية الصلاحية.", uid, mid)

    added = 0
    bot.edit_message_text("📡 جاري استخراج المتفاعلين من المصدر...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        targets = []
        async for message in scrapper.iter_messages(source, limit=1000):
            if len(targets) >= requested: break
            sender = await message.get_sender()
            if isinstance(sender, User) and not sender.bot: targets.append(sender)

        for user in targets:
            if added >= requested: break
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added += 1
                    update_bal(uid, -PRICE_PER_MEMBER)
                    bot.edit_message_text(f"📊 **تقرير النقل:**\n✅ تم نقل: {added}/{requested}\n💰 المتبقي: {LIVE_BALANCES.get(uid, 0.0):.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(35, 50))
                    break 
                except: continue
    except Exception as e: bot.send_message(uid, f"ℹ️ انتهى العمل: {e}")

# --- 💳 نظام الشحن (تلقائي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 شحن تلقائي (OxaPay)", callback_data="pay_auto"))
    kb.add(types.InlineKeyboardButton("📸 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "💎 **اختر وسيلة الشحن:**", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = c.message.chat.id
    if c.data == "pay_manual":
        bot.send_message(uid, f"📍 حول لمحافظنا (TRC20):\n`{MY_WALLET}`\nوأرسل صورة الإيصال هنا.")
    elif c.data == "pay_auto":
        msg = bot.send_message(uid, "💵 أدخل المبلغ بالدولار (مثال: 10):")
        bot.register_next_step_handler(msg, oxa_pay)
    elif c.data.startswith("check_"):
        _, track_id, amt = c.data.split("_")
        r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': track_id}).json()
        if r.get('status') == 'Paid':
            update_bal(uid, float(amt))
            bot.edit_message_text(f"⭐ تم شحن {amt}$ تلقائياً!", uid, c.message.message_id)
        else:
            bot.answer_callback_query(c.id, "⏳ لم يتم الدفع بعد.", show_alert=True)
    elif c.data.startswith("ok_"):
        _, amt, target = c.data.split("_")
        update_bal(int(target), float(amt))
        bot.send_message(int(target), f"✅ تم شحن {amt}$ يدوياً.")
        bot.edit_message_caption(f"✅ تم لـ {target}", uid, c.message.message_id)

def oxa_pay(m):
    try:
        amt = float(m.text)
        r = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if r.get('payLink'):
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔗 رابط الدفع", url=r['payLink']))
            kb.add(types.InlineKeyboardButton("✅ تحقق", callback_data=f"check_{r['trackId']}_{amt}"))
            bot.send_message(m.chat.id, f"📝 فاتورة بمبلغ {amt}$", reply_markup=kb)
    except: pass

# --- 📱 القائمة الرئيسية والنقل ---
def main_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    if m.chat.id not in LIVE_BALANCES: LIVE_BALANCES[m.chat.id] = 0.0
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في دراجون V36**\n💰 رصيدك: `{LIVE_BALANCES[m.chat.id]:.2f}$`", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n💰 الرصيد: `{LIVE_BALANCES.get(m.chat.id, 0.0):.2f}$`")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def move_start(m):
    msg = bot.send_message(m.chat.id, "📦 يوزر المصدر (بدون @):")
    bot.register_next_step_handler(msg, m1)

def m1(m):
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 يوزر مجموعتك (بدون @):")
    bot.register_next_step_handler(msg, m2, src)

def m2(m, src):
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد المطلوب:")
    bot.register_next_step_handler(msg, m3, src, trg)

def m3(m, src, trg):
    try:
        num = int(m.text)
        mid = bot.send_message(m.chat.id, "⏳ جاري البدء...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_engine(m.chat.id, src, trg, num, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل أرقاماً فقط.")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc1(m):
    bot.register_next_step_handler(bot.send_message(m.chat.id, "📱 رقم الهاتف:"), add_acc2)

def add_acc2(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), API_ID, API_HASH)
    async def con(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(con())
        bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), add_acc3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_acc3(m, p, h, s):
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
        bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 باسوورد التحقق بخطوتين:"), add_acc4, p, fs)

def add_acc4(m, p, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def log2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(log2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم الحذف.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup().row(types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من: `{m.chat.id}`", reply_markup=kb)

bot.infinity_polling()
