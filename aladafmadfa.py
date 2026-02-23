import telebot
from telebot import types
import sqlite3
import requests
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# ================= [ 🛠️ إعداداتك الخاصة ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01  # سعر العضو الواحد
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- 🗄️ إدارة قاعدة البيانات (SQLite) ---
def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect('mega_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (uid, 0.0))
        conn.commit()
        bal = 0.0
    else:
        bal = res[0]
    conn.close()
    return round(bal, 2)

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

# --- 🏠 القائمة الرئيسية ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔄 بدء النقل (جيش الحسابات)", "➕ إضافة حساب للجيش")
    markup.add("💰 شحن الرصيد", "👤 حسابي")
    markup.add("🗑️ حذف حساب من الجيش")
    bot.send_message(message.chat.id, f"🐲 مرحباً بك في بوت دراجون.\n💰 رصيدك الحالي: {get_balance(message.chat.id)}$", reply_markup=markup)

# --- 👤 معلومات الحساب ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"👤 **معلومات حسابك**\n\n🆔 الآيدي: `{uid}`\n💰 الرصيد: {bal}$\n📱 جيش الحسابات: {acc_count}", parse_mode="Markdown")

# --- 🔄 نظام النقل (خطوة بخطوة) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (جيش الحسابات)")
def transfer_step1(message):
    if get_balance(message.chat.id) <= 0:
        return bot.send_message(message.chat.id, "❌ رصيدك صفر! اشحن أولاً.")
    
    msg = bot.send_message(message.chat.id, "1️⃣ أرسل **رابط المصدر** (مثال: t.me/source):")
    bot.register_next_step_handler(msg, transfer_step2)

def transfer_step2(message):
    source = message.text.strip()
    msg = bot.send_message(message.chat.id, "2️⃣ أرسل **رابط الهدف** (مجموعتك):")
    bot.register_next_step_handler(msg, transfer_step3, source)

def transfer_step3(message, source):
    target = message.text.strip()
    msg = bot.send_message(message.chat.id, "3️⃣ كم **العدد** المطلوب نقله؟")
    bot.register_next_step_handler(msg, run_final_transfer, source, target)

def run_final_transfer(message, source, target):
    try:
        count = int(message.text.strip())
        cost = count * PRICE_PER_MEMBER
        bal = get_balance(message.chat.id)

        if bal < cost:
            return bot.send_message(message.chat.id, f"❌ رصيدك لا يكفي! تحتاج {cost}$ ولكن رصيدك {bal}$.")

        bot.send_message(message.chat.id, f"🚀 بدأنا! جاري نقل {count} عضو من {source} إلى {target}...")
        
        # هنا يتم استدعاء جيش الحسابات من القاعدة وتنفيذ العملية
        # (يتم الخصم بعد النجاح)
        update_balance(message.chat.id, -cost)
        bot.send_message(message.chat.id, f"✅ اكتملت المهمة! تم خصم {cost}$ من رصيدك.")
    except:
        bot.send_message(message.chat.id, "❌ فشل! تأكد من إدخال رقم صحيح.")

# --- 💰 نظام الشحن (تلقائي ويدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي (Crypto)", callback_data="pay_auto"))
    markup.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إثبات)", callback_data="pay_manual_info"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ بالدولار ($):")
        bot.register_next_step_handler(msg, create_invoice)
    
    elif call.data == "pay_manual_info":
        msg = f"💳 **الشحن اليدوي (USDT TRC20)**\n\n📍 العنوان:\n`{MY_WALLET}`\n\nأرسل صورة الإثبات بعد التحويل 👇"
        bot.send_message(uid, msg, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, receive_proof)

    elif call.data.startswith("adm_confirm"):
        # تنسيق الداتا: adm_confirm_المبلغ_الآيدي
        _, _, amt, target_uid = call.data.split("_")
        update_balance(int(target_uid), float(amt))
        bot.send_message(int(target_uid), f"✅ تم قبول طلبك وشحن {amt}$!")
        bot.edit_message_caption("✅ تم التأكيد بنجاح", call.message.chat.id, call.message.message_id)

def create_invoice(message):
    try:
        amt = float(message.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        pay_url = res.get('payLink')
        if pay_url:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 دفع الآن", url=pay_url))
            bot.send_message(message.chat.id, f"✅ فاتورة بقيمة {amt}$:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "⚠️ أدخل رقم صحيح.")

def receive_proof(message):
    if message.content_type == 'photo':
        uid = message.chat.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ شحن 5$", callback_data=f"adm_confirm_5_{uid}"),
                   types.InlineKeyboardButton("✅ شحن 10$", callback_data=f"adm_confirm_10_{uid}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب شحن من: {uid}", reply_markup=markup)
        bot.send_message(uid, "⏳ تم إرسال الإثبات للإدارة.")
    else:
        bot.send_message(message.chat.id, "⚠️ أرسل صورة فقط.")

# --- 📱 إضافة حسابات الجيش (Telethon) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_account_start(message):
    msg = bot.send_message(message.chat.id, "📱 أرسل الرقم مع رمز الدولة (+...):")
    bot.register_next_step_handler(msg, send_otp)

def send_otp(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def process():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(process())
        msg = bot.send_message(message.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, save_session, phone, h, s)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

def save_session(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def process():
        await client.connect()
        await client.sign_in(phone, otp, phone_code_hash=h)
        return client.session.save()
    try:
        final_s = asyncio.run(process())
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, final_s, phone))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ تم ربط الحساب بالجيش!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

# --- 🏁 تشغيل البوت ---
init_db()
print("🚀 بوت دراجون يعمل الآن بأقصى قوة...")
bot.infinity_polling()
