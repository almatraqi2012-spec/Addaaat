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
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# مسار قاعدة البيانات الثابت لضمان عدم ضياع الرصيد
DB_PATH = '/app/data/dragon_pro_v25.db' if os.path.exists('/app/data') else 'dragon_pro_v25.db'

# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=150)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=60)
    conn.execute('PRAGMA journal_mode=WAL;') # وضع السرعة والاستقرار
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

# تهيئة الجداول بنظام احترافي
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')
db_manage('CREATE TABLE IF NOT EXISTS memory (target_id INTEGER PRIMARY KEY)')

# --- 🚀 المحرك الذكي (نظام الرادار العميق V25) ---
async def dragon_v25_pro_engine(uid, source, target, requested, mid):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    current_balance = float(res[0][0]) if res else 0.0
    
    if current_balance < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"⚠️ عذراً، رصيدك الحالي ({current_balance:.2f}$) غير كافٍ للعدد المطلوب.", uid, mid)

    acc_data = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not acc_data: return bot.edit_message_text("❌ لم يتم العثور على حسابات مرتبطة للقيام بالعملية.", uid, mid)
    
    clients = []
    for s in acc_data:
        cl = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients: return bot.edit_message_text("❌ جميع الجلسات المرتبطة منتهية الصلاحية. يرجى إعادة إضافة الحسابات.", uid, mid)

    added = 0
    bot.edit_message_text(f"📡 جاري مسح المجموعة المصدر واستخراج الأعضاء المتفاعلين...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        blacklist = [row[0] for row in db_manage("SELECT target_id FROM memory", fetch=True)]
        targets = []
        
        # الرادار العميق: سحب المتفاعلين فقط
        async for message in scrapper.iter_messages(source, limit=1500):
            if len(targets) >= requested: break
            if message.sender_id and message.sender_id not in blacklist:
                sender = await message.get_sender()
                if isinstance(sender, User) and not sender.bot:
                    if sender.id not in [u.id for u in targets]: targets.append(sender)
        
        if not targets: return bot.edit_message_text("❌ لم نجد أعضاء جدد متاحين للسحب حالياً.", uid, mid)
        
        bot.edit_message_text(f"🛡️ تم تجهيز {len(targets)} هدف متفاعل.\n🚀 بدأ النقل الآمن...", uid, mid)

        for user in targets:
            if added >= requested: break
            
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added += 1
                    db_manage("INSERT OR IGNORE INTO memory (target_id) VALUES (?)", (user.id,))
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    
                    if added % 1 == 0:
                        b = float(db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0])
                        bot.edit_message_text(f"📊 **تقرير التقدم المباشر**\n━━━━━━━━━━━━━━\n✅ مضاف بنجاح: {added}\n🎯 المستهدف: {requested}\n💰 الرصيد المتبقي: {b:.2f}$", uid, mid)
                    
                    await asyncio.sleep(random.randint(30, 60)) # تأخير لضمان الأمان
                    break 
                except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
                    db_manage("INSERT OR IGNORE INTO memory (target_id) VALUES (?)", (user.id,))
                    break
                except errors.FloodWaitError:
                    clients.remove(cl); continue
                except: continue

    except Exception as e: bot.send_message(uid, f"ℹ️ ملاحظة تقنية: {e}")
    bot.send_message(uid, f"🏁 **اكتملت العملية بنجاح**\n━━━━━━━━━━━━━━\n✅ الأعضاء المضافين: {added}\n💰 رصيدك الحالي: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$")

# --- 📱 القوائم والتحكم الاحترافي ---

def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.add("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.add("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 العودة للقائمة")
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"🐲 **مرحباً بك في Dragon V25 Pro**\n\nنظامك المتكامل لإدارة ونقل الأعضاء باحترافية.\n💰 رصيدك الحالي: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("💳 شحن تلقائي", callback_data="pay_auto"),
           types.InlineKeyboardButton("🛠️ شحن يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, f"📍 **عنوان محفظة الإيداع (TRC20):**\n`{MY_WALLET}`\n\nيرجى اختيار وسيلة الشحن:", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def query_handler(c):
    uid = c.message.chat.id
    if c.data == "pay_manual":
        bot.send_message(uid, "📸 يرجى إرسال صورة إيصال التحويل للمراجعة.")
    elif c.data == "pay_auto":
        msg = bot.send_message(uid, "💵 أدخل المبلغ المطلوب شحنه بالدولار:")
        bot.register_next_step_handler(msg, oxa_process)
    elif c.data.startswith("adm_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"⭐ **تم شحن حسابك بمبلغ {amt}$ بنجاح.**")
        bot.edit_message_caption(f"✅ تم تأكيد الشحن لـ {target}", uid, c.message.message_id)
    bot.answer_callback_query(c.id)

def oxa_process(m):
    try:
        r = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': float(m.text), 'currency': 'USD'}).json()
        if r.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط للدفع الفوري", url=r['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {m.text}$", reply_markup=kb)
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال مبلغ صالح.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10.0_{m.chat.id}"),
        types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_20.0_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن يدوي:\nID: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "✅ تم استلام إيصالك، جاري التدقيق من قبل الإدارة.")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_init(m):
    msg = bot.send_message(m.chat.id, "📥 يرجى إرسال يوزر المجموعة المصدر (بدون @):")
    bot.register_next_step_handler(msg, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 يرجى إرسال يوزر مجموعتك (بدون @):"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 حدد عدد الأعضاء المطلوب:"), start_engine, m1.text, m2.text)))

def start_engine(m, s, t):
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "⏳ جاري تهيئة المحرك وفحص الحسابات...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v25_pro_engine(m.chat.id, s, t, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال أرقام فقط.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    accs = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"👤 **معلومات الحساب**\n━━━━━━━━━━━━━━\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المرتبطة: `{accs}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def clear_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم قطع الاتصال بجميع الحسابات المرتبطة بنجاح.")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc_1(m):
    msg = bot.send_message(m.chat.id, "📱 أدخل رقم الهاتف مع مفتاح الدولة (مثال: +966...):")
    bot.register_next_step_handler(msg, add_acc_2)

def add_acc_2(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), API_ID, API_HASH)
    async def connect(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 أدخل رمز التحقق الوارد إليك:"), add_acc_3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ حدث خطأ: {e}")

def add_acc_3(m, p, h, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def login():
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except errors.SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(login())
    if res == "OK": 
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح.")
    elif res == "2FA":
        bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 الحساب محمي، أدخل كلمة مرور التحقق بخطوتين:"), add_acc_4, p, fs)

def add_acc_4(m, p, s):
    cl = TelegramClient(StringSession(s), API_ID, API_HASH)
    async def log2fa(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(log2fa()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم الربط.")

bot.infinity_polling()
