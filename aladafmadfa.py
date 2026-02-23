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

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=50)

# --- 🗄️ محرك قاعدة البيانات المحمي ---
def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_v_master.db', check_same_thread=False)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        res = cur.fetchall() if fetch else None
        conn.commit()
        return res
    finally:
        conn.close()

# تهيئة الجداول (مرة واحدة)
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- ⚔️ محرك النقل "العبقري" (فحص حقيقي + خصم عادل) ---
async def transfer_logic(uid, source, target, requested, mid):
    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs:
        return bot.send_message(uid, "❌ لم تقم بإضافة حسابات للنقل بعد!")

    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients:
        return bot.send_message(uid, "❌ جميع الحسابات المضافة غير صالحة.")

    added = 0
    try:
        leader = clients[0]
        s_ent = await leader.get_entity(source)
        t_ent = await leader.get_entity(target)
        await leader(JoinChannelRequest(s_ent))
        await leader(JoinChannelRequest(t_ent))
        
        # نبش الأعضاء
        async for user in leader.iter_participants(s_ent, limit=requested*2, aggressive=True):
            if added >= requested: break
            
            # فحص الرصيد قبل المحاولة
            user_data = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
            if not user_data or user_data[0][0] < PRICE_PER_MEMBER:
                bot.send_message(uid, "⚠️ توقف النقل: الرصيد غير كافٍ.")
                break

            for cl in clients:
                try:
                    await cl(InviteToChannelRequest(t_ent, [user]))
                    # الذكاء الباهر: هل دخل فعلاً؟
                    check = await cl(GetParticipantsRequest(t_ent, ChannelParticipantsRecent(), 0, 5, hash=0))
                    if any(p.id == user.id for p in check.users):
                        added += 1
                        db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                        bot.edit_message_text(f"🚀 جاري النقل الحقيقي...\n✅ المضافين فعلياً: {added}\n💰 المتبقي: {db_manage('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                        await asyncio.sleep(3) # حماية للحسابات
                        break
                except (UserPrivacyRestrictedError, FloodWaitError): continue
                except Exception: continue
                
    except Exception as e:
        bot.send_message(uid, f"❌ حدث خطأ في الوصول للروابط: {e}")
    
    bot.send_message(uid, f"🏁 اكتملت المهمة بنجاح!\n✅ تم إضافة {added} عضو حقيقي للجروب.")

# --- 🎯 معالجة الأزرار (الاستجابة الفورية) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_queries(call):
    # أهم سطر لإصلاح "عدم الاستجابة"
    bot.answer_callback_query(call.id)
    uid = call.message.chat.id

    if call.data.startswith("charge_"): # للمالك
        _, amt, target = call.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, target))
        bot.send_message(target, f"✅ تم شحن {amt}$ في حسابك بنجاح!")
        bot.edit_message_caption(f"✅ تم تنفيذ الشحن لـ {target}", uid, call.message.message_id)

    elif call.data == "p_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ المطلوب شحنه ($):")
        bot.register_next_step_handler(msg, oxapay_exec)

    elif call.data == "p_man":
        bot.send_message(uid, f"💳 **الشحن اليدوي (USDT TRC20)**\nالعنوان: `{MY_WALLET}`\nأرسل صورة الإيصال بعد التحويل:")

# --- 🏠 الأوامر وقوائم البوت ---
@bot.message_handler(commands=['start'])
def start(m):
    db_manage("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔄 بدء نقل أعضاء", "👤 حسابي")
    kb.row("➕ إضافة حسابات", "💰 شحن الرصيد")
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في بوت دراجون العالمي**\n💰 رصيدك الحالي: `{db_manage('SELECT balance FROM users WHERE user_id=?', (m.chat.id,), True)[0][0]:.2f}$`", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ شحن تلقائي (Oxapay)", callback_data="p_auto"))
    kb.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إيصال)", callback_data="p_man"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def transfer_start(m):
    if db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)[0][0] < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك غير كافٍ.")
    
    bot.send_message(m.chat.id, "📦 أرسل رابط المجموعة المصدر:")
    bot.register_next_step_handler(m, lambda msg1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 أرسل رابط مجموعتك:"), lambda msg2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 كم العدد المطلوب؟"), final_trigger, msg1.text, msg2.text)))

def final_trigger(m, src, trg):
    try:
        count = int(m.text)
        mid = bot.send_message(m.chat.id, "📡 جاري تهيئة المحرك والنقل الحقيقي...").message_id
        threading.Thread(target=lambda: asyncio.run(transfer_logic(m.chat.id, src, trg, count, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

@bot.message_handler(content_types=['photo'])
def manual_receipt(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 5$", callback_data=f"charge_5_{m.chat.id}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"charge_10_{m.chat.id}"))
    kb.row(types.InlineKeyboardButton("✅ 20$", callback_data=f"charge_20_{m.chat.id}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"charge_50_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال إيصالك للمراجعة.")

def oxapay_exec(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 ادفع الآن", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$", reply_markup=kb)
    except: bot.send_message(m.chat.id, "⚠️ رقم غير صحيح.")

# --- 📱 محرك إضافة الحسابات المتطور (يدعم التحقق بخطوتين) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def acc_init(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل رقم الهاتف مع رمز الدولة (مثال: +966...):")
    bot.register_next_step_handler(msg, acc_otp)

def acc_otp(m):
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_c():
        await cl.connect()
        # إرسال الكود للرقم
        r = await cl.send_code_request(phone)
        return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(get_c())
        bot.send_message(m.chat.id, "📩 وصلك كود من تليجرام، أرسله الآن:")
        bot.register_next_step_handler(m, acc_verify, phone, h, s)
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ خطأ في الرقم: {e}")

def acc_verify(m, p, h, s):
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log():
        await cl.connect()
        try:
            # محاولة تسجيل الدخول بالكود
            await cl.sign_in(p, otp, phone_code_hash=h)
            return "OK", cl.session.save()
        except SessionPasswordNeededError:
            # هنا الذكاء: إذا طلب باسورد (التحقق بخطوتين)
            return "2FA", cl.session.save()
        except Exception as e:
            return str(e), None

    try:
        res, fs = asyncio.run(log())
        if res == "OK":
            db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
            bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح (بدون باسورد)!")
        elif res == "2FA":
            # نطلب الباسورد من المستخدم
            bot.send_message(m.chat.id, "🔐 هذا الحساب محمي بـ (التحقق بخطوتين).\nأرسل كلمة السر الآن:")
            bot.register_next_step_handler(m, acc_2fa_final, p, fs)
        else:
            bot.send_message(m.chat.id, f"❌ فشل: {res}")
    except:
        bot.send_message(m.chat.id, "❌ حدث خطأ غير متوقع.")

def acc_2fa_final(m, p, s):
    pwd = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log_2fa():
        await cl.connect()
        # تسجيل الدخول بكلمة السر
        await cl.sign_in(password=pwd)
        return cl.session.save()
    try:
        fs = asyncio.run(log_2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم فك التشفير وربط الحساب بنجاح!")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ كلمة السر خاطئة أو حدثت مشكلة: {e}")

print("🔥 دراجون الإمبراطوري يعمل الآن بأقصى ذكاء!")
bot.infinity_polling()
