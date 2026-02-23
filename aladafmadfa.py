import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time
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

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=50)

# --- 🗄️ محرك قاعدة البيانات ---
def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_final_v7.db', check_same_thread=False)
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

# --- ⌨️ لوحات المفاتيح (Keyboards) ---
def main_markup(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    markup.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    markup.row("💰 شحن الرصيد")
    return markup

def back_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 رجوع للقائمة الرئيسية")
    return markup

# --- 🏠 الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **مرحباً بك في بوت دراجون العالمي**\n💰 رصيدك الحالي: `{bal:.2f}$`", 
                     reply_markup=main_markup(m.chat.id), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    text = f"📊 **معلومات حسابك:**\n\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المربوطة: `{count}`"
    bot.send_message(m.chat.id, text, parse_mode="Markdown", reply_markup=main_markup(m.chat.id))

# --- 🗑️ حذف الحسابات ---
@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def delete_accs_prompt(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚠️ نعم، احذف جميع حساباتي", callback_data="confirm_delete_all"))
    bot.send_message(m.chat.id, "هل أنت متأكد من حذف جميع الحسابات المربوطة؟", reply_markup=markup)

# --- 💰 نظام الشحن ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="p_auto"))
    markup.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إيصال)", callback_data="p_man"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المناسبة:", reply_markup=markup)

# --- 🔄 محرك النقل ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_start(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    if bal < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك غير كافٍ، يرجى الشحن أولاً.")
    
    msg = bot.send_message(m.chat.id, "📦 أرسل رابط المجموعة المصدر (الكروب اللي نسحب منه):", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_source)

def get_source(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 أرسل رابط مجموعتك (التي سيتم النقل إليها):")
    bot.register_next_step_handler(msg, get_target, src)

def get_target(m, src):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 كم العدد المطلوب نقله؟")
    bot.register_next_step_handler(msg, execute_transfer, src, trg)

def execute_transfer(m, src, trg):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري بدء عملية النقل الواقعي...").message_id
        threading.Thread(target=lambda: asyncio.run(real_transfer_worker(m.chat.id, src, trg, count, mid))).start()
    except:
        bot.send_message(m.chat.id, "⚠️ يرجى إدخال رقم صحيح.")

async def real_transfer_worker(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if not clients: return bot.send_message(uid, "❌ لا توجد حسابات شغالة.")

    added = 0
    try:
        leader = clients[0]
        s_ent = await leader.get_entity(source); t_ent = await leader.get_entity(target)
        await leader(JoinChannelRequest(s_ent)); await leader(JoinChannelRequest(t_ent))
        
        async for user in leader.iter_participants(s_ent, limit=requested*2, aggressive=True):
            if added >= requested: break
            if db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0] < PRICE_PER_MEMBER: break

            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(t_ent, [user]))
                    check = await cl(GetParticipantsRequest(t_ent, ChannelParticipantsRecent(), 0, 5, hash=0))
                    if any(p.id == user.id for p in check.users):
                        added += 1
                        db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                        bot.edit_message_text(f"🚀 جاري النقل...\n✅ تم إضافة: {added}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                        await asyncio.sleep(4)
                        break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    bot.send_message(uid, f"🏁 اكتمل النقل! المضافين فعلياً: {added}")

# --- 📱 إضافة الحسابات (مع 2FA) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc_init(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع رمز الدولة (مثال: +966...):", reply_markup=back_markup())
    bot.register_next_step_handler(msg, add_acc_otp)

def add_acc_otp(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def connect():
        await cl.connect()
        r = await cl.send_code_request(phone)
        return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        msg = bot.send_message(m.chat.id, "📩 أرسل الكود المكون من 5 أرقام:")
        bot.register_next_step_handler(msg, add_acc_verify, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_acc_verify(m, p, h, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(p, otp, phone_code_hash=h)
            return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
        except: return "ERR", None
    
    res, fs = asyncio.run(login())
    if res == "OK":
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح!", reply_markup=main_markup(m.chat.id))
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 هذا الحساب محمي بكلمة سر، أرسلها الآن:")
        bot.register_next_step_handler(msg, add_acc_2fa, p, fs)
    else: bot.send_message(m.chat.id, "❌ الكود خاطئ.")

def add_acc_2fa(m, p, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login_2fa():
        await cl.connect(); await cl.sign_in(password=m.text.strip()); return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم فك التشفير والربط!", reply_markup=main_markup(m.chat.id))
    except: bot.send_message(m.chat.id, "❌ كلمة السر خاطئة.")

# --- 🎯 معالج الكولباك (Callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(call.id)
    uid = call.message.chat.id
    if call.data == "confirm_delete_all":
        db_manage("DELETE FROM accounts WHERE user_id=?", (uid,))
        bot.edit_message_text("✅ تم حذف جميع حساباتك بنجاح.", uid, call.message.message_id)
    elif call.data == "p_man":
        bot.send_message(uid, f"💳 حول لعنوان TRC20:\n`{MY_WALLET}`\nوارسل صورة الإيصال:")
    elif call.data.startswith("admin_ok_"):
        _, amt, target = call.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, target))
        bot.send_message(target, f"✅ تم شحن {amt}$ في حسابك!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", uid, call.message.message_id)

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"admin_ok_5_{m.chat.id}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"admin_ok_10_{m.chat.id}"))
    kb.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"admin_ok_20_{m.chat.id}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"admin_ok_50_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال الإيصال للمالك.")

bot.infinity_polling()
