import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent
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

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=60)

# --- 🗄️ محرك قاعدة البيانات ---
def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_v8_final.db', check_same_thread=False)
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

# --- 🏠 الأوامر الأساسية ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في بوت دراجون الشامل**\n💰 رصيدك الحالي: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"📊 **معلوماتك:**\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات: `{count}`", parse_mode="Markdown")

# --- 🗑️ حذف الحسابات ---
@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def del_accs(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ تأكيد حذف جميع الحسابات", callback_data="confirm_del_all"))
    bot.send_message(m.chat.id, "⚠️ هل أنت متأكد؟ هذا سيحذف جميع جلساتك المربوطة.", reply_markup=kb)

# --- 💰 نظام الشحن (تلقائي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="btn_auto"),
           types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="btn_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=kb)

# --- 🎯 معالج الكولباك (Callback) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    uid = call.message.chat.id
    
    if call.data == "confirm_del_all":
        db_manage("DELETE FROM accounts WHERE user_id=?", (uid,))
        bot.edit_message_text("✅ تم مسح جميع حساباتك بنجاح.", uid, call.message.message_id)

    elif call.data == "btn_manual":
        bot.send_message(uid, f"💳 **الشحن اليدوي**\nحول لعنوان TRC20:\n`{MY_WALLET}`\nوارسل صورة الإيصال هنا 👇")

    elif call.data == "btn_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المراد شحنه ($):")
        bot.register_next_step_handler(msg, process_oxapay)

    elif call.data.startswith("adm_pay_"): # موافقة المالك
        _, _, amt, target = call.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تمت الموافقة! أضيفت {amt}$ لرصيدك.")
        bot.edit_message_caption(f"✅ تم شحن {amt}$ للآيدي {target}", uid, call.message.message_id)

    bot.answer_callback_query(call.id)

# --- ⚡ معالجة Oxapay ---
def process_oxapay(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$", reply_markup=kb)
        else: bot.send_message(m.chat.id, "❌ خطأ في بوابة الدفع.")
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# --- 📸 استقبال الإيصالات اليدوية ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.chat.id
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_pay_5_{uid}"),
           types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_pay_10_{uid}"))
    kb.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_pay_20_{uid}"),
           types.InlineKeyboardButton("✅ 50$", callback_data=f"adm_pay_50_{uid}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من: `{uid}`", reply_markup=kb)
    bot.send_message(uid, "⏳ تم إرسال إثباتك للمراجعة.")

# --- ➕ إضافة الحسابات (شامل التحقق بخطوتين) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc_1(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع رمز الدولة (مثال: +966...):", reply_markup=back_markup())
    bot.register_next_step_handler(msg, add_acc_2)

def add_acc_2(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def connect():
        await cl.connect(); r = await cl.send_code_request(phone); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        msg = bot.send_message(m.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, add_acc_3, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_acc_3(m, p, h, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    otp = m.text.strip(); cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try: await cl.sign_in(p, otp, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
        except: return "ERR", None
    res, fs = asyncio.run(login())
    if res == "OK":
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الربط!", reply_markup=main_markup())
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:")
        bot.register_next_step_handler(msg, add_acc_final, p, fs)
    else: bot.send_message(m.chat.id, "❌ الكود خاطئ.")

def add_acc_final(m, p, s):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_2fa():
        await cl.connect(); await cl.sign_in(password=m.text.strip()); return cl.session.save()
    try:
        fs = asyncio.run(log_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الربط بنجاح!", reply_markup=main_markup())
    except: bot.send_message(m.chat.id, "❌ كلمة السر خاطئة.")

# --- 🔄 محرك النقل الواقعي ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def tr_start(m):
    if db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0] < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك غير كافٍ.")
    msg = bot.send_message(m.chat.id, "📦 رابط المجموعة المصدر:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 العدد المطلوب:"), tr_final, m1.text, m2.text)))

def tr_final(m, s, t):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start_cmd(m)
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري النقل الحقيقي...").message_id
        threading.Thread(target=lambda: asyncio.run(transfer_logic(m.chat.id, s, t, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقم فقط.")

async def transfer_logic(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    if not clients: return bot.send_message(uid, "❌ لا توجد حسابات صالحة.")
    
    added = 0
    try:
        main = clients[0]; s_ent = await main.get_entity(source); t_ent = await main.get_entity(target)
        await main(JoinChannelRequest(s_ent)); await main(JoinChannelRequest(t_ent))
        async for u in main.iter_participants(s_ent, limit=requested*2, aggressive=True):
            if added >= requested or db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0] < PRICE_PER_MEMBER: break
            for c in clients:
                try:
                    await c(InviteToChannelRequest(t_ent, [u]))
                    check = await c(GetParticipantsRequest(t_ent, ChannelParticipantsRecent(), 0, 5, hash=0))
                    if any(p.id == u.id for p in check.users):
                        added += 1
                        db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                        bot.edit_message_text(f"🚀 جاري النقل...\n✅ مضافين: {added}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                        await asyncio.sleep(5); break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    bot.send_message(uid, f"🏁 اكتمل النقل! المضافين فعلياً: {added}")

bot.infinity_polling()
