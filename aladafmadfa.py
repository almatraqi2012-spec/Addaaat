import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import User, ChannelParticipantsSearch

# ================= [ 🛠️ الإعدادات الرسمية ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
# الـ API الرسمي القوي لتخطي الحظر
API_ID = 6 
API_HASH = 'eb06d4ab3521ad1297469cd2db5d1cae'

ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

DB_PATH = '/app/data/dragon_v44.db' if os.path.exists('/app/data') else 'dragon_v44.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)
GLOBAL_BALANCES = {}

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

# تحميل الأرصدة للذاكرة لمنع التصفير
rows = db_manage("SELECT user_id, balance FROM users", fetch=True)
for r in rows: GLOBAL_BALANCES[r[0]] = r[1]

def update_bal(uid, amt):
    new_val = GLOBAL_BALANCES.get(uid, 0.0) + amt
    GLOBAL_BALANCES[uid] = new_val
    db_manage("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)", (uid, new_val))
    return new_val

# --- 🚀 محرك النقل الإعصاري (صيد المتفاعلين) ---
async def dragon_engine(uid, source, target, requested, mid):
    bal = GLOBAL_BALANCES.get(uid, 0.0)
    if bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"⚠️ رصيدك ({bal:.2f}$) غير كافٍ لنقل {requested} عضو.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.edit_message_text("❌ لم تربط حسابات سحب!", uid, mid)
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients: return bot.edit_message_text("❌ الحسابات تحتاج إعادة ربط.", uid, mid)

    added = 0
    bot.edit_message_text("📡 **جاري اختراق المصدر وصيد المتفاعلين...**", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        targets = []
        # تحدي المجموعات المخفية: سحب من الرسائل والمدردشين
        async for message in scrapper.iter_messages(source, limit=1200):
            if len(targets) >= requested: break
            sender = await message.get_sender()
            if isinstance(sender, User) and not sender.bot:
                if sender.id not in [u.id for u in targets]: targets.append(sender)

        bot.edit_message_text(f"⚔️ تم صيد {len(targets)} هدف حقيقي. بدأ النقل الفعلي...", uid, mid)

        for user in targets:
            if added >= requested: break
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added += 1
                    update_bal(uid, -PRICE_PER_MEMBER)
                    bot.edit_message_text(f"🔥 **نقل جاري..**\n✅ تم: `{added}/{requested}`\n💰 رصيدك: `{GLOBAL_BALANCES.get(uid, 0.0):.2f}$`", uid, mid)
                    await asyncio.sleep(random.randint(35, 55))
                    break 
                except: continue
    except Exception as e: bot.send_message(uid, f"🏁 إشعار: {e}")
    bot.send_message(uid, f"🏁 **تمت المهمة!**\nتم إضافة {added} عضو بنجاح بمجموع {added*PRICE_PER_MEMBER:.2f}$.")

# --- 💳 نظام الشحن (تلقائي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("⚡ شحن تلقائي (OxaPay)", callback_data="oxa_auto"),
           types.InlineKeyboardButton("📸 شحن يدوي (إيصال)", callback_data="manual_pay"))
    bot.send_message(m.chat.id, "💎 **شحن رصيد دراجون**\nاختر وسيلة الدفع:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid = c.message.chat.id
    if c.data == "oxa_auto":
        msg = bot.send_message(uid, "💵 أدخل المبلغ بالدولار (مثال: 10):")
        bot.register_next_step_handler(msg, oxa_invoice)
    elif c.data == "manual_pay":
        bot.send_message(uid, f"📍 حول لـ (TRC20):\n`{MY_WALLET}`\nوأرسل صورة الإيصال هنا.")
    elif c.data.startswith("check_"):
        _, tid, amt = c.data.split("_")
        r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
        if r.get('status') == 'Paid':
            update_bal(uid, float(amt))
            bot.edit_message_text(f"⭐ مبروك! تم شحن {amt}$ تلقائياً.", uid, c.message.message_id)
        else: bot.answer_callback_query(c.id, "⏳ لم يتم استلام الدفع بعد.", show_alert=True)
    elif c.data.startswith("ok_"):
        _, amt, target = c.data.split("_")
        update_bal(int(target), float(amt))
        bot.send_message(int(target), f"✅ تم تأكيد شحن {amt}$ يدوياً!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", uid, c.message.message_id)

def oxa_invoice(m):
    try:
        amt = float(m.text)
        r = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if r.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع", url=r['payLink']),
                                                 types.InlineKeyboardButton("✅ تحقق من الدفع", callback_data=f"check_{r['trackId']}_{amt}"))
            bot.send_message(m.chat.id, f"📝 فاتورة بمبلغ {amt}$:", reply_markup=kb)
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# --- 👤 قسم "حسابي" المطور ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    uid = m.chat.id
    bal = GLOBAL_BALANCES.get(uid, 0.0)
    accs = db_manage("SELECT phone FROM accounts WHERE user_id=?", (uid,), fetch=True)
    count = len(accs)
    phones = "\n".join([f"• `{p[0]}`" for p in accs]) if accs else "لا توجد حسابات مضافة."
    txt = (f"👤 **معلومات حسابك**\n━━━━━━━━━━━━━━\n🆔 الآيدي: `{uid}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات: `{count}`\n━━━━━━━━━━━━━━\n📞 **الأرقام:**\n{phones}")
    bot.send_message(uid, txt, parse_mode="Markdown")

# --- ➕ إضافة حسابات (الجلسة النظيفة) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc1(m):
    bot.register_next_step_handler(bot.send_message(m.chat.id, "📱 الرقم مع المفتاح (مثال: +9665xx):"), add_acc2)

def add_acc2(m):
    p = m.text.strip()
    cl = TelegramClient(StringSession(), API_ID, API_HASH, device_model="DragonV44", system_version="Android 12")
    async def con(): 
        await cl.connect()
        try:
            r = await cl.send_code_request(p)
            return r.phone_code_hash, cl.session.save(), None
        except Exception as e: return None, None, str(e)
    h, s, err = asyncio.run(con())
    if err: bot.send_message(m.chat.id, f"❌ خطأ من تليجرام: {err}")
    else: bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 أرسل الكود:"), add_acc3, p, h, s)

def add_acc3(m, p, h, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def log():
        await cl.connect()
        try: 
            await cl.sign_in(p, m.text, phone_code_hash=h)
            return "OK", cl.session.save()
        except errors.SessionPasswordNeededError: return "2FA", cl.session.save()
        except Exception as e: return str(e), None
    res, fs = asyncio.run(log())
    if res == "OK": 
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم ربط الحساب.")
    elif res == "2FA":
        bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 كلمة السر (التحقق بخطوتين):"), add_acc4, p, fs)
    else: bot.send_message(m.chat.id, f"❌ فشل: {res}")

def add_acc4(m, p, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def log2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    try:
        fs = asyncio.run(log2())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الفك والربط.")
    except: bot.send_message(m.chat.id, "❌ خطأ في كلمة السر.")

# --- القوائم الأساسية ---
def main_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء نقل أعضاء", "👤 حسابي", "➕ إضافة حسابات", "🗑️ حذف الحسابات", "💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    if m.chat.id not in GLOBAL_BALANCES: update_bal(m.chat.id, 0.0)
    bot.send_message(m.chat.id, f"🐲 **دراجون V44 جاهز للعمل!**\n💰 رصيدك الحالي: `{GLOBAL_BALANCES.get(m.chat.id, 0.0):.2f}$`", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def move_start(m):
    msg = bot.send_message(m.chat.id, "📥 يوزر المصدر (بدون @):")
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
        mid = bot.send_message(m.chat.id, "⏳ جاري تشغيل المحرك...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_engine(m.chat.id, src, trg, num, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل أرقاماً فقط.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم مسح جميع حساباتك.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup().row(types.InlineKeyboardButton("✅ تأكيد 10$", callback_data=f"ok_10_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال جديد من: `{m.chat.id}`", reply_markup=kb)

bot.infinity_polling()
