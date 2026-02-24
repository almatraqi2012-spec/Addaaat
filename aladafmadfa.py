import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent, ChannelParticipantsSearch
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

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_v_super.db', check_same_thread=False)
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

# --- ⌨️ القوائم ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

def back_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🔙 رجوع للقائمة الرئيسية")
    return m

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في النسخة القاهرة من دراجون**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

# --- ⚙️ المحرك الجبار (النبش والاضافة) ---
async def aggressive_transfer(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if not clients: 
        return bot.edit_message_text("❌ لم يتم العثور على حسابات صالحة للنقل!", uid, mid)

    added = 0
    tried_users = set()
    
    try:
        leader = random.choice(clients) # اختيار حساب عشوائي للنبش
        source_entity = await leader.get_entity(source)
        target_entity = await leader.get_entity(target)
        
        # الانضمام للمجموعات بكل الحسابات لضمان القدرة على الإضافة
        for c in clients:
            try: await c(JoinChannelRequest(source_entity))
            except: pass
            try: await c(JoinChannelRequest(target_entity))
            except: pass

        # نبش الأعضاء بطريقة هجومية (Aggressive)
        bot.edit_message_text("🔍 جاري نبش الأعضاء النشطين من المصدر...", uid, mid)
        participants = await leader.get_participants(source_entity, limit=2000)
        
        # تصفية الأعضاء (تجاهل البوتات والمحذوفين والمنضمين قديماً جداً)
        active_users = [u for u in participants if not u.bot and not u.deleted]
        random.shuffle(active_users) # عشوائية لضمان عدم كشف النمط

        for user in active_users:
            if added >= requested: break
            if user.id in tried_users: continue
            
            # فحص الرصيد
            bal = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0]
            if bal < PRICE_PER_MEMBER:
                bot.send_message(uid, "⚠️ توقف! رصيدك غير كافٍ.")
                break

            # محاولة الإضافة بكل الحسابات المتاحة بالتناوب
            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(target_entity, [user]))
                    # التحقق من النجاح
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    bot.edit_message_text(f"🔥 جاري الغزو...\n✅ تم إضافة: {added}\n👤 العضو: {user.first_name}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                    tried_users.add(user.id)
                    await asyncio.sleep(random.randint(5, 10)) # وقت أمان
                    break # نجحت الإضافة، انتقل للعضو التالي
                except (UserPrivacyRestrictedError, UserNotMutualContactError):
                    tried_users.add(user.id)
                    break # العضو قافل الخصوصية، لا تضيع وقت
                except FloodWaitError as e:
                    continue # الحساب هذا تعب، جرب بحساب آخر لنفس العضو
                except Exception:
                    continue

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ غير متوقع: {e}")
    
    bot.send_message(uid, f"🏁 **انتهت المعركة بنجاح!**\n✅ الأعضاء الذين دخلوا الجروب فعلياً: {added}")

# --- الأزرار وبقية الكود (نفس الميزات السابقة مع تحسين الاستجابة) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def tr_start(m):
    msg = bot.send_message(m.chat.id, "📦 رابط المجموعة المصدر:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_s)

def get_s(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    s = m.text
    msg = bot.send_message(m.chat.id, "🎯 رابط مجموعتك:")
    bot.register_next_step_handler(msg, get_t, s)

def get_t(m, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    t = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد المطلوب:")
    bot.register_next_step_handler(msg, get_c, s, t)

def get_c(m, s, t):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري تفعيل محرك النبش العميق...").message_id
        threading.Thread(target=lambda: asyncio.run(aggressive_transfer(m.chat.id, s, t, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أرسل رقماً فقط.")

# إضافة الحسابات، الشحن، والحذف (نفس الكود المستقر السابق)
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def acc_1(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم (+966...):", reply_markup=back_markup())
    bot.register_next_step_handler(msg, acc_2)

def acc_2(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    p = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def con(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try: h, s = asyncio.run(con()); bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), acc_3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌: {e}")

def acc_3(m, p, h, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log():
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(log())
    if res == "OK": db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")
    elif res == "2FA": bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 الباسورد:"), acc_f, p, fs)

def acc_f(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    fs = asyncio.run(l2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم!")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_acc(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم حذف جميع حساباتك.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    accs = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات: `{accs}`")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ تلقائي", callback_data="a"), types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="m"))
    bot.send_message(m.chat.id, "شحن:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    if c.data == "m": bot.send_message(c.message.chat.id, f"💳 `{MY_WALLET}`")
    elif c.data.startswith("ok_"):
        _, amt, uid = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
        bot.send_message(uid, f"✅ تم شحن {amt}$")
    bot.answer_callback_query(c.id)

@bot.message_handler(content_types=['photo'])
def receipt(m):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"من {m.chat.id}", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري الفحص..")

bot.infinity_polling()
