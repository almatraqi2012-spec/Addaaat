import telebot
from telebot import types
import sqlite3, threading, time, asyncio, requests, random
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# ================= [ ⚙️ الإعدادات ] =================
BOT_TOKEN = "8774804527:AAHaCMOst4XZVpowd6lw483gsUZuIlHkXlY"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.01
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- محرك قاعدة البيانات ---
def db_exec(query, params=(), fetch=False):
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally:
        conn.close()

db_exec('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_exec('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')

def get_balance(uid):
    res = db_exec("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    if not res:
        db_exec("INSERT INTO users (user_id, balance) VALUES (?, ?)", (uid, 0.0))
        return 0.0
    return round(res[0][0], 2)

# --- الكيبوردات ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء النقل (نظام دراجون)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب من الجيش")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في نظام دراجون الخارق!**\n💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=main_markup(), parse_mode="Markdown")

# --- 1: نظام الشحن ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن تلقائي (Crypto)", callback_data="pay_auto"),
        types.InlineKeyboardButton("💳 شحن يدوي (بواسطة الإدمن)", callback_data="pay_manual")
    )
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار ($):")
        bot.register_next_step_handler(msg, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 **الدفع اليدوي (USDT TRC20):**\n\n`{MY_WALLET}`\n\nأرسل صورة الإيصال بعد التحويل 👇")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    elif call.data.startswith("check_"):
        _, tid, amt = call.data.split("_")
        res = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
        if res.get('status') == 'Paid':
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), uid))
            bot.send_message(uid, f"✅ تم تفعيل {amt}$ بنجاح!")
        else:
            bot.answer_callback_query(call.id, "❌ لم يصل الدفع بعد.", show_alert=True)
    elif call.data.startswith("adm_confirm_"):
        _, _, amt, target_id = call.data.split("_")
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target_id)))
        bot.send_message(int(target_id), f"✅ تم تفعيل رصيدك بـ {amt}$!")
        bot.edit_message_caption("✅ تم قبول الطلب.", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("del_"):
        db_exec("DELETE FROM user_accounts WHERE id=?", (call.data.split("_")[1],))
        bot.edit_message_text("✅ تم حذف الجندي.", uid, call.message.message_id)

def create_invoice(m):
    try:
        amt = float(m.text.strip())
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            mk.add(types.InlineKeyboardButton("✅ تحقق", callback_data=f"check_{res.get('trackId')}_{amt}"))
            bot.send_message(m.chat.id, f"فاتورة شحن {amt}$ جاهزة:", reply_markup=mk)
    except:
        bot.send_message(m.chat.id, "⚠️ أدخل رقم صحيح.")

def wait_for_receipt(m):
    if m.photo:
        uid = m.chat.id
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_confirm_5_{uid}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_confirm_10_{uid}"))
        mk.add(types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_confirm_20_{uid}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"adm_confirm_50_{uid}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن يدوي من `{uid}`", reply_markup=mk)
        bot.send_message(uid, "✅ تم الإرسال، انتظر تفعيل الإدارة.")
    else:
        bot.send_message(m.chat.id, "⚠️ أرسل صورة فقط.")

# --- 2: نظام إضافة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    bot.send_message(m.chat.id, "📱 أرسل الرقم مع مفتاح الدولة (مثال: +967...):")
    bot.register_next_step_handler(m, step_phone)

def step_phone(m):
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h():
        await cl.connect()
        r = await cl.send_code_request(phone)
        return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(get_h())
        bot.send_message(m.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(m, step_otp, phone, h, s)
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_otp(m, phone, h, s):
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(phone, otp, phone_code_hash=h)
            return cl.session.save(), False
        except SessionPasswordNeededError:
            return cl.session.save(), True
    try:
        new_s, need_2fa = asyncio.run(login())
        if need_2fa:
            bot.send_message(m.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:")
            bot.register_next_step_handler(m, step_2fa, phone, new_s)
        else:
            db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, new_s, phone))
            bot.send_message(m.chat.id, "✅ تم ربط الحساب!")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_2fa(m, phone, s):
    pw = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login_2fa():
        await cl.connect()
        await cl.sign_in(password=pw)
        return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, fs, phone))
        bot.send_message(m.chat.id, "✅ تم التجاوز وربط الحساب!")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ غلط: {e}")

# --- 3: نظام سحب دراجون (نسخة سهم المطورة) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (نظام دراجون)")
def flow_1(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك 0$")
    bot.send_message(m.chat.id, "📡 **يوزر المجموعة المصدر (بدون @):**")
    bot.register_next_step_handler(m, flow_2)

def flow_2(m):
    src = m.text.strip().replace('@', '').split('/')[-1]
    bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(m, flow_3, src)

def flow_3(m, src):
    trg = m.text.strip().replace('@', '').split('/')[-1]
    bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله:**")
    bot.register_next_step_handler(m, flow_final, src, trg)

def flow_final(m, src, trg):
    try:
        count = int(m.text)
        sessions = [r[0] for r in db_exec("SELECT session_string FROM user_accounts WHERE user_id=?", (m.chat.id,), True)]
        if not sessions:
            return bot.send_message(m.chat.id, "❌ جيشك خالي.")
        
        db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (count * PRICE_PER_MEMBER, m.chat.id))
        bot.send_message(m.chat.id, "⚔️ **نظام دراجون بدأ السحب العميق (نظام الدفعات)...**")
        threading.Thread(target=lambda: asyncio.run(dragon_engine(sessions, src, trg, count, m.chat.id))).start()
    except:
        bot.send_message(m.chat.id, "⚠️ خطأ في المدخلات.")

async def dragon_engine(sessions, src, trg, total, uid):
    found = []
    # مرحلة الصيد (القناص)
    cl_hunter = TelegramClient(StringSession(sessions[0]), MY_API_ID, MY_API_HASH)
    try:
        await cl_hunter.connect()
        async for msg in cl_hunter.iter_messages(src, limit=5000):
            if len(found) >= total: break
            if msg.sender_id and isinstance(msg.sender, tl_types.User):
                if msg.sender.username and not msg.sender.bot:
                    if msg.sender.id not in [u.id for u in found]:
                        found.append(msg.sender)
        await cl_hunter.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ فشل الصيد: {e}")

    if not found:
        return bot.send_message(uid, "❌ المجموعة المصدر محصنة!")

    bot.send_message(uid, f"🐲 تم قنص `{len(found)}` هدف. بدأ الجر القسري...")
    
    success = 0
    for i, target_user in enumerate(found):
        if success >= total: break
        
        # تقسيم العمل على الحسابات (نفس نظام التحدي)
        current_session = sessions[i % len(sessions)]
        cl = TelegramClient(StringSession(current_session), MY_API_ID, MY_API_HASH)
        
        try:
            await cl.connect()
            await cl(functions.channels.InviteToChannelRequest(channel=trg, users=[target_user.username]))
            success += 1
            await cl.disconnect()
            
            if success % 5 == 0:
                bot.send_message(uid, f"🛡️ تم سحب: `{success}/{total}` أعضاء.")
            
            await asyncio.sleep(12) # أمان عالي
        except:
            continue

    bot.send_message(uid, f"🏁 **تمت الغزوة بنجاح!**\n✅ الأعضاء المضافين: `{success}`")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    accs = db_exec("SELECT phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    bot.send_message(m.chat.id, f"🆔 الآيدي: `{m.chat.id}`\n💰 رصيدك: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(accs)}` حساب.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc_menu(m):
    accs = db_exec("SELECT id, phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    if not accs: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for aid, ph in accs:
        mk.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(m.chat.id, "اختر حساباً لحذفه:", reply_markup=mk)

if __name__ == "__main__":
    print("🐲 الإمبراطور شغال...")
    bot.infinity_polling()import telebot
from telebot import types
import sqlite3, threading, time, asyncio, requests, random
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# ================= [ ⚙️ الإعدادات ] =================
BOT_TOKEN = "8774804527:AAHaCMOst4XZVpowd6lw483gsUZuIlHkXlY"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.01
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- محرك قاعدة البيانات ---
def db_exec(query, params=(), fetch=False):
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally:
        conn.close()

db_exec('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_exec('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')

def get_balance(uid):
    res = db_exec("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    if not res:
        db_exec("INSERT INTO users (user_id, balance) VALUES (?, ?)", (uid, 0.0))
        return 0.0
    return round(res[0][0], 2)

# --- الكيبوردات ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء النقل (نظام دراجون)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب من الجيش")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في نظام دراجون الخارق!**\n💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=main_markup(), parse_mode="Markdown")

# --- 1: نظام الشحن ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن تلقائي (Crypto)", callback_data="pay_auto"),
        types.InlineKeyboardButton("💳 شحن يدوي (بواسطة الإدمن)", callback_data="pay_manual")
    )
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار ($):")
        bot.register_next_step_handler(msg, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 **الدفع اليدوي (USDT TRC20):**\n\n`{MY_WALLET}`\n\nأرسل صورة الإيصال بعد التحويل 👇")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    elif call.data.startswith("check_"):
        _, tid, amt = call.data.split("_")
        res = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
        if res.get('status') == 'Paid':
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), uid))
            bot.send_message(uid, f"✅ تم تفعيل {amt}$ بنجاح!")
        else:
            bot.answer_callback_query(call.id, "❌ لم يصل الدفع بعد.", show_alert=True)
    elif call.data.startswith("adm_confirm_"):
        _, _, amt, target_id = call.data.split("_")
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target_id)))
        bot.send_message(int(target_id), f"✅ تم تفعيل رصيدك بـ {amt}$!")
        bot.edit_message_caption("✅ تم قبول الطلب.", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("del_"):
        db_exec("DELETE FROM user_accounts WHERE id=?", (call.data.split("_")[1],))
        bot.edit_message_text("✅ تم حذف الجندي.", uid, call.message.message_id)

def create_invoice(m):
    try:
        amt = float(m.text.strip())
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            mk.add(types.InlineKeyboardButton("✅ تحقق", callback_data=f"check_{res.get('trackId')}_{amt}"))
            bot.send_message(m.chat.id, f"فاتورة شحن {amt}$ جاهزة:", reply_markup=mk)
    except:
        bot.send_message(m.chat.id, "⚠️ أدخل رقم صحيح.")

def wait_for_receipt(m):
    if m.photo:
        uid = m.chat.id
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_confirm_5_{uid}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_confirm_10_{uid}"))
        mk.add(types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_confirm_20_{uid}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"adm_confirm_50_{uid}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن يدوي من `{uid}`", reply_markup=mk)
        bot.send_message(uid, "✅ تم الإرسال، انتظر تفعيل الإدارة.")
    else:
        bot.send_message(m.chat.id, "⚠️ أرسل صورة فقط.")

# --- 2: نظام إضافة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    bot.send_message(m.chat.id, "📱 أرسل الرقم مع مفتاح الدولة (مثال: +967...):")
    bot.register_next_step_handler(m, step_phone)

def step_phone(m):
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h():
        await cl.connect()
        r = await cl.send_code_request(phone)
        return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(get_h())
        bot.send_message(m.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(m, step_otp, phone, h, s)
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_otp(m, phone, h, s):
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(phone, otp, phone_code_hash=h)
            return cl.session.save(), False
        except SessionPasswordNeededError:
            return cl.session.save(), True
    try:
        new_s, need_2fa = asyncio.run(login())
        if need_2fa:
            bot.send_message(m.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:")
            bot.register_next_step_handler(m, step_2fa, phone, new_s)
        else:
            db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, new_s, phone))
            bot.send_message(m.chat.id, "✅ تم ربط الحساب!")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_2fa(m, phone, s):
    pw = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login_2fa():
        await cl.connect()
        await cl.sign_in(password=pw)
        return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, fs, phone))
        bot.send_message(m.chat.id, "✅ تم التجاوز وربط الحساب!")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ غلط: {e}")

# --- 3: نظام سحب دراجون (نسخة سهم المطورة) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (نظام دراجون)")
def flow_1(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك 0$")
    bot.send_message(m.chat.id, "📡 **يوزر المجموعة المصدر (بدون @):**")
    bot.register_next_step_handler(m, flow_2)

def flow_2(m):
    src = m.text.strip().replace('@', '').split('/')[-1]
    bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(m, flow_3, src)

def flow_3(m, src):
    trg = m.text.strip().replace('@', '').split('/')[-1]
    bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله:**")
    bot.register_next_step_handler(m, flow_final, src, trg)

def flow_final(m, src, trg):
    try:
        count = int(m.text)
        sessions = [r[0] for r in db_exec("SELECT session_string FROM user_accounts WHERE user_id=?", (m.chat.id,), True)]
        if not sessions:
            return bot.send_message(m.chat.id, "❌ جيشك خالي.")
        
        db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (count * PRICE_PER_MEMBER, m.chat.id))
        bot.send_message(m.chat.id, "⚔️ **نظام دراجون بدأ السحب العميق (نظام الدفعات)...**")
        threading.Thread(target=lambda: asyncio.run(dragon_engine(sessions, src, trg, count, m.chat.id))).start()
    except:
        bot.send_message(m.chat.id, "⚠️ خطأ في المدخلات.")

async def dragon_engine(sessions, src, trg, total, uid):
    found = []
    # مرحلة الصيد (القناص)
    cl_hunter = TelegramClient(StringSession(sessions[0]), MY_API_ID, MY_API_HASH)
    try:
        await cl_hunter.connect()
        async for msg in cl_hunter.iter_messages(src, limit=5000):
            if len(found) >= total: break
            if msg.sender_id and isinstance(msg.sender, tl_types.User):
                if msg.sender.username and not msg.sender.bot:
                    if msg.sender.id not in [u.id for u in found]:
                        found.append(msg.sender)
        await cl_hunter.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ فشل الصيد: {e}")

    if not found:
        return bot.send_message(uid, "❌ المجموعة المصدر محصنة!")

    bot.send_message(uid, f"🐲 تم قنص `{len(found)}` هدف. بدأ الجر القسري...")
    
    success = 0
    for i, target_user in enumerate(found):
        if success >= total: break
        
        # تقسيم العمل على الحسابات (نفس نظام التحدي)
        current_session = sessions[i % len(sessions)]
        cl = TelegramClient(StringSession(current_session), MY_API_ID, MY_API_HASH)
        
        try:
            await cl.connect()
            await cl(functions.channels.InviteToChannelRequest(channel=trg, users=[target_user.username]))
            success += 1
            await cl.disconnect()
            
            if success % 5 == 0:
                bot.send_message(uid, f"🛡️ تم سحب: `{success}/{total}` أعضاء.")
            
            await asyncio.sleep(12) # أمان عالي
        except:
            continue

    bot.send_message(uid, f"🏁 **تمت الغزوة بنجاح!**\n✅ الأعضاء المضافين: `{success}`")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    accs = db_exec("SELECT phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    bot.send_message(m.chat.id, f"🆔 الآيدي: `{m.chat.id}`\n💰 رصيدك: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(accs)}` حساب.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc_menu(m):
    accs = db_exec("SELECT id, phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    if not accs: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for aid, ph in accs:
        mk.add(types.InlineKeyboardButton(f"❌ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(m.chat.id, "اختر حساباً لحذفه:", reply_markup=mk)

if __name__ == "__main__":
    print("🐲 الإمبراطور شغال...")
    bot.infinity_polling()
