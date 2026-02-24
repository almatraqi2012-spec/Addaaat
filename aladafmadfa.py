import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetHistoryRequest
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

# مسار قاعدة البيانات الدائم (للحفاظ على الرصيد في Railway)
DB_PATH = '/app/data/dragon_final_v15.db' if os.path.exists('/app/data') else 'dragon_final_v15.db'
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

# إنشاء الجداول
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- ⌨️ لوحات التحكم ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.row("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.row("💰 شحن الرصيد")
    return m

# --- 🏠 الأوامر الأساسية ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔙 رجوع للقائمة الرئيسية")
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في دراجون V15**\n💰 رصيدك الحالي: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"📊 **بيانات الحساب:**\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المربوطة: `{count}`", parse_mode="Markdown")

# --- 💰 نظام الشحن المتكامل ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="pay_auto"),
           types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المفضلة:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data == "pay_manual":
        bot.send_message(uid, f"💳 **الشحن اليدوي**\n\nحول لعنوان TRC20 التالي:\n`{MY_WALLET}`\n\nثم ارسل صورة الإيصال هنا 👇")
    
    elif call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المراد شحنه بالدولار ($):")
        bot.register_next_step_handler(msg, oxapay_link_logic)

    elif call.data.startswith("admin_accept_"): # موافقة الإدارة على الشحن اليدوي
        _, _, amt, target_id = call.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target_id)))
        bot.send_message(int(target_id), f"✅ تمت الموافقة! أضيفت {amt}$ لرصيدك.")
        bot.edit_message_caption(f"✅ تم شحن {amt}$ لـ {target_id}", uid, call.message.message_id)
    
    bot.answer_callback_query(call.id)

# منطق توليد رابط Oxapay
def oxapay_link_logic(m):
    try:
        amount = float(m.text)
        payload = {'merchant': OXAPAY_KEY, 'amount': amount, 'currency': 'USD', 'lifeTime': 30}
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amount}$:\n(الرابط صالح لمدة 30 دقيقة)", reply_markup=kb)
        else:
            bot.send_message(m.chat.id, "❌ عذراً، فشل الاتصال ببوابة الدفع حالياً.")
    except:
        bot.send_message(m.chat.id, "⚠️ يرجى إدخال مبلغ صحيح (أرقام فقط).")

# استقبال صور الإيصالات اليدوية
@bot.message_handler(content_types=['photo'])
def handle_payment_photo(m):
    kb = types.InlineKeyboardMarkup()
    # أزرار سريعة للأدمن للموافقة
    kb.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"admin_accept_5_{m.chat.id}"),
           types.InlineKeyboardButton("✅ 10$", callback_data=f"admin_accept_10_{m.chat.id}"))
    kb.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"admin_accept_20_{m.chat.id}"),
           types.InlineKeyboardButton("✅ 50$", callback_data=f"admin_accept_50_{m.chat.id}"))
    
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال الإيصال للمراجعة، سيتم شحن رصيدك فور التأكد.")

# --- 🔄 محرك النقل "كاسر الحماية" V15 ---
async def transfer_engine(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if not clients: return bot.edit_message_text("❌ لا توجد حسابات شغالة!", uid, mid)

    added = 0
    bot.edit_message_text(f"🔍 جاري فحص المصدر: {source}", uid, mid)
    
    try:
        scrapper = random.choice(clients)
        source = source.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
        target = target.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
        
        src_ent = await scrapper.get_entity(source)
        trg_ent = await scrapper.get_entity(target)

        # محاولة النبش من القائمة ومن الشات (للمخفي)
        users = []
        try: users = await scrapper.get_participants(src_ent, limit=1000)
        except: pass
        
        if len(users) < 5: # لو القائمة مخفية اسحب من الشات
            history = await scrapper(GetHistoryRequest(peer=src_ent, limit=100, offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for msg in history.messages:
                if msg.from_id:
                    try: 
                        u = await scrapper.get_entity(msg.from_id)
                        if u.id not in [x.id for x in users]: users.append(u)
                    except: continue

        targets = [u for u in users if not u.bot and not u.deleted]
        random.shuffle(targets)
        
        if not targets: return bot.edit_message_text("❌ لم يتم العثور على أعضاء (المجموعة محمية).", uid, mid)
        bot.edit_message_text(f"🔥 تم صيد {len(targets)} عضو. جاري النقل...", uid, mid)

        for user in targets:
            if added >= requested: break
            if db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0] < PRICE_PER_MEMBER: break

            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(trg_ent, [user]))
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    bot.edit_message_text(f"✅ تم إضافة: {added}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                    await asyncio.sleep(random.randint(20, 40)) # أمان عالي جداً
                    break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ حدث خطأ: {e}")
    bot.send_message(uid, f"🏁 اكتمل النقل بنجاح لـ {added} عضو.")

# --- الأوامر المساعدة ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def init_transfer(m):
    msg = bot.send_message(m.chat.id, "📦 أرسل رابط المصدر:")
    bot.register_next_step_handler(msg, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 أرسل رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 العدد المطلوب:"), execute_transfer, m1.text, m2.text)))

def execute_transfer(m, s, t):
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري التحضير...").message_id
        threading.Thread(target=lambda: asyncio.run(transfer_engine(m.chat.id, s, t, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال رقم صحيح.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def clear_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم مسح جميع حساباتك.")

# --- نظام إضافة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc_1(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل رقم الهاتف مع رمز الدولة (مثال: +966...):")
    bot.register_next_step_handler(msg, add_acc_2)

def add_acc_2(m):
    phone = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def connect(): await cl.connect(); r = await cl.send_code_request(phone); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(connect())
        msg = bot.send_message(m.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(msg, add_acc_3, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def add_acc_3(m, p, h, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(login())
    if res == "OK": db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم الربط!")
    elif res == "2FA": bot.register_next_step_handler(bot.send_message(m.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:"), add_acc_4, p, fs)

def add_acc_4(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_2fa(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    try:
        fs = asyncio.run(log_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم الربط بنجاح!")
    except: bot.send_message(m.chat.id, "❌ الباسورد خاطئ.")

bot.infinity_polling()
