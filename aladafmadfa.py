import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import ChannelParticipantsRecent, User, Channel
from telethon.errors import *

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

DB_PATH = '/app/data/dragon_v16.db' if os.path.exists('/app/data') else 'dragon_v16.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=150)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        res = cur.fetchall() if fetch else None
        conn.commit()
        return res
    finally:
        conn.close()

db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- 🚀 محرك النقل المطور V16 ---
async def dragon_v16_engine(uid, source, target, requested, mid):
    # 1. فحص الرصيد أولاً وقبل كل شيء (المنع من المصدر)
    user_data = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    if not user_data or user_data[0][0] < PRICE_PER_MEMBER:
        return bot.edit_message_text("❌ عذراً! رصيدك غير كافٍ للبدء. يرجى شحن حسابك أولاً.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.edit_message_text("❌ لم تضف أي حسابات بعد!", uid, mid)
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if not clients: return bot.edit_message_text("❌ جميع حساباتك معطلة أو سجلت خروج!", uid, mid)

    added = 0
    bot.edit_message_text(f"📡 جاري فحص المصدر وتجهيز الهجوم...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        source = source.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
        target = target.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
        
        src_ent = await scrapper.get_entity(source)
        trg_ent = await scrapper.get_entity(target)

        # محاولة سحب الأعضاء (مع إصلاح خطأ AttributeError)
        all_users = []
        try:
            participants = await scrapper.get_participants(src_ent, limit=1000)
            for u in participants:
                # التأكد أن الكائن "مستخدم" وليس "قناة" أو "بوت"
                if isinstance(u, User) and not u.bot and not u.deleted:
                    all_users.append(u)
        except: pass
        
        # نبش إضافي من الشات إذا القائمة مخفية
        if len(all_users) < 10:
            bot.edit_message_text("🛡️ القائمة مخفية.. جاري استخراج المتفاعلين من الدردشة...", uid, mid)
            history = await scrapper(GetHistoryRequest(peer=src_ent, limit=200, offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for msg in history.messages:
                if msg.from_id and hasattr(msg.from_id, 'user_id'):
                    try:
                        u = await scrapper.get_entity(msg.from_id.user_id)
                        if isinstance(u, User) and not u.bot and u.id not in [x.id for x in all_users]:
                            all_users.append(u)
                    except: continue

        if not all_users:
            return bot.edit_message_text("❌ فشل النبش! المصدر لا يحتوي على أعضاء متاحين أو محمي جداً.", uid, mid)

        random.shuffle(all_users)
        bot.edit_message_text(f"🔥 تم صيد {len(all_users)} هدف متفاعل.\n🚀 بدأ غزو دراجون الآن...", uid, mid)

        for user in all_users:
            if added >= requested: break
            
            # فحص الرصيد قبل كل عملية إضافة
            bal = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0]
            if bal < PRICE_PER_MEMBER:
                bot.send_message(uid, "⚠️ توقف النقل! نفذ رصيدك تماماً.")
                break

            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(trg_ent, [user]))
                    # إذا وصلنا هنا يعني تمت الإضافة بنجاح أو لم يعطِ خطأ
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    bot.edit_message_text(f"✅ مضاف: {added}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(15, 35)) # أمان عالي جداً
                    break
                except (UserPrivacyRestrictedError, UserNotMutualContactError):
                    break # هذا المستخدم مستحيل إضافته، انتقل للتالي
                except FloodWaitError as e:
                    continue # هذا الحساب تعب، جرب الحساب اللي بعده لنفس العضو
                except Exception:
                    continue

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ فني: {str(e)}")
    
    bot.send_message(uid, f"🏁 **اكتمل غزو دراجون!**\n✅ الأعضاء المضافين: {added}\n💰 رصيدك الحالي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$")

# --- ⚙️ بقية الوظائف الأساسية (شحن + حسابي) ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في بوت دراجون V16**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="auto"), types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid = c.message.chat.id
    if c.data == "manual":
        bot.send_message(uid, f"💳 عنوان TRC20:\n`{MY_WALLET}`\nارسل صورة الإيصال بعد التحويل.")
    elif c.data == "auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ ($):")
        bot.register_next_step_handler(msg, oxapay_gen)
    elif c.data.startswith("ok_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تم شحن {amt}$!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", uid, c.message.message_id)
    bot.answer_callback_query(c.id)

def oxapay_gen(m):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': float(m.text), 'currency': 'USD'}).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, f"🔗 رابط الدفع: {res['payLink']}")
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def init_tr(m):
    msg = bot.send_message(m.chat.id, "📦 أرسل رابط المصدر:")
    bot.register_next_step_handler(msg, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 العدد:"), execute_v16, m1.text, m2.text)))

def execute_v16(m, s, t):
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 استدعاء التنانين...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v16_engine(m.chat.id, s, t, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أرسل رقماً فقط!")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من {m.chat.id}", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري المراجعة...")

# --- إضافة الحسابات (نفس المنطق المستقر) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_a(m):
    msg = bot.send_message(m.chat.id, "📱 الرقم مع المفتاح:")
    bot.register_next_step_handler(msg, add_b)

def add_b(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def c(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try: h, s = asyncio.run(c()); bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), add_c, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌: {e}")

def add_c(m, p, h, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l(): 
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(l())
    if res == "OK": db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")
    elif res == "2FA": bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 الباسورد:"), add_d, p, fs)

def add_d(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(l2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")

bot.infinity_polling()
