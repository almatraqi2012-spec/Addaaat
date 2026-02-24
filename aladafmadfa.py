import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import ChannelParticipantsRecent, User, PeerUser
from telethon.errors import *

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" # مفتاحك التلقائي
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

DB_PATH = '/app/data/dragon_v19.db' if os.path.exists('/app/data') else 'dragon_v19.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=200)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- 🚀 محرك النقل السريع ---
async def dragon_v19_engine(uid, source, target, requested, mid):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    balance = float(res[0][0]) if res else 0.0
    
    if balance < PRICE_PER_MEMBER:
        return bot.edit_message_text(f"⚠️ رصيدك {balance:.2f}$ غير كافٍ.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if not clients: return bot.edit_message_text("❌ أضف حسابات أولاً!", uid, mid)

    added = 0
    bot.edit_message_text(f"📡 جاري غزو المصدر...", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        src = source.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
        trg = target.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
        src_ent = await scrapper.get_entity(src); trg_ent = await scrapper.get_entity(trg)

        all_users = []
        try:
            p = await scrapper.get_participants(src_ent, limit=1500)
            all_users = [u for u in p if isinstance(u, User) and not u.bot and not u.deleted]
        except: pass
        
        if len(all_users) < 10:
            h = await scrapper(GetHistoryRequest(peer=src_ent, limit=300, offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for m in h.messages:
                if m.from_id and isinstance(m.from_id, PeerUser):
                    try:
                        u = await scrapper.get_entity(m.from_id.user_id)
                        if isinstance(u, User) and not u.bot and u.id not in [x.id for x in all_users]: all_users.append(u)
                    except: continue

        if not all_users: return bot.edit_message_text("❌ المصدر محمي جداً.", uid, mid)
        random.shuffle(all_users)
        bot.edit_message_text(f"⚔️ تم تجهيز {len(all_users)} هدف. انطلق!", uid, mid)

        for user in all_users:
            if added >= requested: break
            bal_now = float(db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0])
            if bal_now < PRICE_PER_MEMBER: break

            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(trg_ent, [user]))
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (float(PRICE_PER_MEMBER), uid))
                    bot.edit_message_text(f"🔥 **غزو دراجون**\n✅ مضاف: {added}\n💰 المتبقي: {float(db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]):.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(15, 25))
                    break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    bot.send_message(uid, f"🏁 انتهى النقل بنجاح لـ {added} عضو.")

# --- 💰 نظام الشحن (تلقائي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي (كريبتو)", callback_data="pay_auto"),
           types.InlineKeyboardButton("👨‍💻 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المناسبة لك:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = c.message.chat.id
    if c.data == "pay_manual":
        bot.send_message(uid, f"💳 عنوان TRC20:\n`{MY_WALLET}`\nارسل صورة الإيصال هنا.")
    elif c.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المراد شحنه ($):")
        bot.register_next_step_handler(msg, generate_oxapay_link)
    elif c.data.startswith("adm_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تم شحن {amt}$ لرصيدك!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", uid, c.message.message_id)
    bot.answer_callback_query(c.id)

def generate_oxapay_link(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$:", reply_markup=kb)
        else: bot.send_message(m.chat.id, "❌ فشل الاتصال ببوابة Oxapay.")
    except: bot.send_message(m.chat.id, "⚠️ أرقام فقط!")

# --- ⚙️ التحكم الرئيسي ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"🐲 **دراجون V19 - الإمبراطورية**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    accs = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات: `{accs}`")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10.0_{m.chat.id}"),
        types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_20.0_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري مراجعة إيصالك...")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def ask_trans(m):
    msg = bot.send_message(m.chat.id, "📦 أرسل رابط المصدر:")
    bot.register_next_step_handler(msg, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 العدد:"), start_raid, m1.text, m2.text)))

def start_raid(m, s, t):
    try:
        c = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 استدعاء القوة الضاربة...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_v19_engine(m.chat.id, s, t, c, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أرقام فقط!")

# --- إضافة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def acc_1(m):
    msg = bot.send_message(m.chat.id, "📱 الرقم (+966...):")
    bot.register_next_step_handler(msg, acc_2)

def acc_2(m):
    p = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def c(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try: h, s = asyncio.run(c()); bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), acc_3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌: {e}")

def acc_3(m, p, h, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l(): 
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(l())
    if res == "OK": db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")
    elif res == "2FA": bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 الباسورد:"), acc_4, p, fs)

def acc_4(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(l2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم المسح.")

bot.infinity_polling()
