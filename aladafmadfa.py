import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent, UserStatusRecently, UserStatusOnline
from telethon.errors import *

# ================= [ 🛠️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# مسار قاعدة البيانات الدائم في Railway
DB_PATH = '/app/data/dragon_final_v13.db' if os.path.exists('/app/data') else 'dragon_final_v13.db'

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

# --- 🔄 محرك النقل "غزو التنين" (الإصدار المرعب) ---
async def dragon_raid_engine(uid, source, target, requested, mid):
    # جلب الحسابات
    raw_accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not raw_accs:
        return bot.edit_message_text("❌ لم تضيف أي حسابات لتبدأ الغزو!", uid, mid)

    clients = []
    for s in raw_accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if len(clients) < 1:
        return bot.edit_message_text("❌ جميع حساباتك معطلة، يرجى إضافة حسابات جديدة.", uid, mid)

    added = 0
    bot.edit_message_text(f"🐲 **دراجون بدأ الغزو..**\n🔍 جاري نبش أعضاء (متفاعلين) من: {source}", uid, mid)
    
    try:
        # استخدام حساب عشوائي للنبش لتفادي الحظر
        scrapper = random.choice(clients)
        src_entity = await scrapper.get_entity(source)
        trg_entity = await scrapper.get_entity(target)
        
        # انضمام جميع الحسابات للمجموعة الهدف لضمان القدرة على الإضافة
        for cl in clients:
            try: await cl(JoinChannelRequest(trg_entity))
            except: pass

        # نبش الأعضاء "المتفاعلين فقط" (المتصلين حالاً أو مؤخراً)
        all_participants = await scrapper.get_participants(src_entity, limit=2000)
        active_users = [
            u for u in all_participants 
            if not u.bot and not u.deleted and (isinstance(u.status, (UserStatusRecently, UserStatusOnline)))
        ]
        
        random.shuffle(active_users)
        bot.edit_message_text(f"🎯 تم العثور على {len(active_users)} هدف متفاعل.\n🚀 جاري البدء بالنقل القوي...", uid, mid)

        for user in active_users:
            if added >= requested: break
            
            # فحص الرصيد قبل كل عملية
            current_bal = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0]
            if current_bal < PRICE_PER_MEMBER:
                bot.send_message(uid, "⚠️ توقف الغزو! نفذ رصيدك.")
                break

            # محاولة الإضافة بنظام التدوير (كل عضو يجربه حساب مختلف)
            success = False
            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(trg_entity, [user]))
                    
                    # التحقق الفوري من دخول العضو
                    check = await cl(GetParticipantsRequest(trg_entity, ChannelParticipantsRecent(), 0, 5, hash=0))
                    if any(p.id == user.id for p in check.users):
                        added += 1
                        db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                        bot.edit_message_text(f"🐲 **إعصار دراجون شغال..**\n✅ تم إضافة: {added}\n👤 العضو: {user.first_name}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                        success = True
                        # تأخير عشوائي ذكي (بين 5 و 15 ثانية) لمحاكاة البشر
                        await asyncio.sleep(random.uniform(5, 15))
                        break # نجح الحساب، اذهب للعضو التالي
                except (UserPrivacyRestrictedError, UserNotMutualContactError):
                    break # العضو مانع الإضافة، لا تضيع وقت الحسابات عليه
                except FloodWaitError as e:
                    clients.remove(cl) # الحساب تعب، شيله من القائمة مؤقتاً
                    continue 
                except Exception:
                    continue
            
            if not success:
                # إذا جربنا كل الحسابات وما انضاف، ننتقل للهدف التالي
                continue

    except Exception as e:
        bot.send_message(uid, f"❌ حدث تداخل في البيانات: {e}")

    bot.send_message(uid, f"🏁 **انتهى غزو دراجون!**\n✅ الأعضاء الذين دخلوا المجموعة فعلياً: {added}\n💰 تم خصم: {added * PRICE_PER_MEMBER:.2f}$")

# --- ⌨️ القوائم الرئيسية ---
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
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في بوت دراجون العالي**\n💰 رصيدك: `{bal:.2f}$`", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def ask_source(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔙 رجوع للقائمة الرئيسية")
    msg = bot.send_message(m.chat.id, "📦 أرسل رابط (المجموعة المصدر):", reply_markup=kb)
    bot.register_next_step_handler(msg, get_source)

def get_source(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start(m)
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 أرسل رابط (مجموعتك):")
    bot.register_next_step_handler(msg, get_target, src)

def get_target(m, src):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start(m)
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 كم العدد المطلوب نقله؟")
    bot.register_next_step_handler(msg, do_raid, src, trg)

def do_raid(m, src, trg):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start(m)
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري استدعاء التنانين...").message_id
        threading.Thread(target=lambda: asyncio.run(dragon_raid_engine(m.chat.id, src, trg, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أرسل رقماً فقط!")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    bal = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0]
    accs = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات: `{accs}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def clear_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم مسح جميع حساباتك من قاعدة البيانات.")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="auto_p"), 
           types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="manual_p"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = c.message.chat.id
    if c.data == "manual_p":
        bot.send_message(uid, f"💳 حول لعنوان TRC20:\n`{MY_WALLET}`\nوارسل صورة الإيصال.")
    elif c.data == "auto_p":
        msg = bot.send_message(uid, "💰 كم المبلغ الذي تود شحنه ($)؟")
        bot.register_next_step_handler(msg, oxapay_exec)
    elif c.data.startswith("confirm_"):
        _, amt, target = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, target))
        bot.send_message(target, f"✅ تم شحن {amt}$ في حسابك، استمتع!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target}", uid, c.message.message_id)
    bot.answer_callback_query(c.id)

def oxapay_exec(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ فاتورة شحن بقيمة {amt}$ جاهزة:", reply_markup=kb)
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"confirm_5_{m.chat.id}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"confirm_10_{m.chat.id}"))
    kb.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"confirm_20_{m.chat.id}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"confirm_50_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم الإرسال، بانتظار موافقة الإدارة.")

# --- ➕ إضافة الحسابات (شامل 2FA) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_a1(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع المفتاح (مثال: +966...):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("🔙 رجوع للقائمة الرئيسية"))
    bot.register_next_step_handler(msg, add_a2)

def add_a2(m):
    if m.text == "🔙 رجوع للقائمة الرئيسية": return start(m)
    p = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def c(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try: h, s = asyncio.run(c()); msg = bot.send_message(m.chat.id, "📩 أرسل كود التحقق:"); bot.register_next_step_handler(msg, add_a3, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌: {e}")

def add_a3(m, p, h, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l(): 
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK", cl.session.save()
        except SessionPasswordNeededError: return "2FA", cl.session.save()
    res, fs = asyncio.run(l())
    if res == "OK": db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم الربط!", reply_markup=main_markup())
    elif res == "2FA": msg = bot.send_message(m.chat.id, "🔐 أرسل كلمة سر التحقق بخطوتين:"); bot.register_next_step_handler(msg, add_a4, p, fs)

def add_a4(m, p, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def l2(): await cl.connect(); await cl.sign_in(password=m.text); return cl.session.save()
    try: fs = asyncio.run(l2()); db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p)); bot.send_message(m.chat.id, "✅ تم الربط!", reply_markup=main_markup())
    except: bot.send_message(m.chat.id, "❌ الباسورد خطأ.")

bot.infinity_polling()
