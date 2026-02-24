import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent
from telethon.errors import *

# ================= [ 🛠️ الإعدادات ] =================
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
    conn = sqlite3.connect('dragon_final_v10.db', check_same_thread=False)
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

# --- ⌨️ لوحات التحكم ---
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

# --- 🏠 الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **مرحباً بك في دراجون V10 **\n💰 رصيدك الحالي: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"📊 **إحصائيات حسابك:**\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المربوطة: `{count}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم حذف جميع حساباتك بنجاح من القاعدة.")

# --- 💰 نظام الشحن (كامل ومستجيب) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="pay_auto_trigger"),
           types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="pay_manual_trigger"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المتاحة:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    bot.answer_callback_query(call.id)
    uid = call.message.chat.id

    if call.data == "pay_manual_trigger":
        bot.send_message(uid, f"💳 **الشحن اليدوي**\nحول لعنوان TRC20:\n`{MY_WALLET}`\nوارسل صورة الإيصال هنا 👇")
    
    elif call.data == "pay_auto_trigger":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المراد شحنه بالدولار ($):")
        bot.register_next_step_handler(msg, oxapay_link_generator)

    elif call.data.startswith("admin_ok_"): # موافقة المالك
        _, _, amt, target = call.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تمت الموافقة! أضيفت {amt}$ لرصيدك.")
        bot.edit_message_caption(f"✅ تم شحن {amt}$ لـ {target}", uid, call.message.message_id)

def oxapay_link_generator(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ فاتورة شحن بقيمة {amt}$ جاهزة:", reply_markup=kb)
        else: bot.send_message(m.chat.id, "❌ فشل الاتصال ببوابة Oxapay.")
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال مبلغ صحيح.")

# --- 📸 استقبال الإيصالات اليدوية ---
@bot.message_handler(content_types=['photo'])
def handle_manual(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"admin_ok_5_{m.chat.id}"),
           types.InlineKeyboardButton("✅ 10$", callback_data=f"admin_ok_10_{m.chat.id}"))
    kb.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"admin_ok_20_{m.chat.id}"),
           types.InlineKeyboardButton("✅ 50$", callback_data=f"admin_ok_50_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال طلبك للمراجعة.")

# --- ➕ إضافة الحسابات (مع التحقق بخطوتين 2FA) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def acc_start(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع رمز الدولة (مثال: +966...):", reply_markup=back_markup())
    bot.register_next_step_handler(msg, acc_step_2)

def acc_step_2(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    phone = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def con(): await cl.connect(); r = await cl.send_code_request(phone); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(con())
        msg = bot.send_message(m.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, acc_step_3, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def acc_step_3(m, p, h, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    otp = m.text.strip(); cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try: await cl.sign_in(p, otp, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
        except Exception as e: return str(e), None
    res, fs = asyncio.run(login())
    if res == "OK":
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح!", reply_markup=main_markup())
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:")
        bot.register_next_step_handler(msg, acc_step_final, p, fs)
    else: bot.send_message(m.chat.id, f"❌ فشل: {res}")

def acc_step_final(m, p, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_2fa(): await cl.connect(); await cl.sign_in(password=m.text.strip()); return cl.session.save()
    try:
        fs = asyncio.run(log_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم فك التشفير والربط!", reply_markup=main_markup())
    except: bot.send_message(m.chat.id, "❌ كلمة السر خاطئة.")

# --- 🔄 محرك النقل الهجومي (يتحدى الجروبات) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def tr_init(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    if bal < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيدك كافٍ.")
    msg = bot.send_message(m.chat.id, "📦 رابط المجموعة المصدر:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 العدد المطلوب:"), tr_execute, m1.text, m2.text)))

def tr_execute(m, s, t):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري تفعيل محرك النبش والزحف...").message_id
        threading.Thread(target=lambda: asyncio.run(super_transfer_logic(m.chat.id, s, t, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

async def super_transfer_logic(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    if not clients: return bot.edit_message_text("❌ لا توجد حسابات صالحة!", uid, mid)

    added = 0
    try:
        leader = random.choice(clients)
        s_ent = await leader.get_entity(source); t_ent = await leader.get_entity(target)
        # النبش الهجومي
        bot.edit_message_text("🔍 جاري سحب قائمة الأعضاء (Aggressive)...", uid, mid)
        users = await leader.get_participants(s_ent, limit=2000)
        active_list = [u for u in users if not u.bot and not u.deleted]
        random.shuffle(active_list)

        for user in active_list:
            if added >= requested: break
            if db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0] < PRICE_PER_MEMBER: break
            
            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(t_ent, [user]))
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    bot.edit_message_text(f"🔥 جاري النقل...\n✅ مضافين: {added}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(5, 12))
                    break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ عطل: {e}")
    bot.send_message(uid, f"🏁 اكتمل النقل!\n✅ الأعضاء الجدد: {added}")

bot.infinity_polling()
