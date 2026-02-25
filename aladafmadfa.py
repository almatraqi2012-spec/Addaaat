import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time, random, os
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import User, ChannelParticipantsSearch

# ================= [ 🛠️ الإعدادات الرسمية - عبده ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
API_ID = 21349867
API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

# مسار قاعدة البيانات - يدعم التخزين الدائم
DB_PATH = '/app/data/dragon_v40.db' if os.path.exists('/app/data') else 'dragon_v40.db'
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=100)

def db_manage(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=60)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch: return cur.fetchall()
        conn.commit()
    finally: conn.close()

# تهيئة الجداول بنظام احترافي
db_manage('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_manage('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- 🚀 محرك النقل الخارق (رادار الصيد) ---
async def super_dragon_engine(uid, source, target, requested, mid):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    curr_bal = float(res[0][0]) if res else 0.0
    
    if curr_bal < (requested * PRICE_PER_MEMBER):
        return bot.edit_message_text(f"⚠️ عذراً، رصيدك الحالي ({curr_bal:.2f}$) لا يغطي تكلفة {requested} عضو.", uid, mid)

    accs = db_manage("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.edit_message_text("❌ لم تقم بإضافة حسابات سحب إلى البوت بعد.", uid, mid)
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)

    if not clients: return bot.edit_message_text("❌ جميع الحسابات المضافة انتهت صلاحيتها. أعد ربطها.", uid, mid)

    added = 0
    bot.edit_message_text("📡 **بدء تشغيل الرادار..**\nجاري اختراق قائمة المتفاعلين والمدردشين في المصدر...", uid, mid)
    
    try:
        # استراتيجية الصيد: سحب من الرسائل (للمجموعات المخفية) + سحب من القائمة (للمفتوحة)
        scrapper = random.choice(clients)
        targets = []
        
        # 1. صيد المدردشين (الأكثر تفاعلاً)
        async for message in scrapper.iter_messages(source, limit=1500):
            if len(targets) >= requested: break
            sender = await message.get_sender()
            if isinstance(sender, User) and not sender.bot:
                if sender.id not in [u.id for u in targets]: targets.append(sender)

        # 2. إذا لم يكتمل العدد، نسحب من قائمة المنضمين حديثاً
        if len(targets) < requested:
            try:
                async for user in scrapper.iter_participants(source, limit=requested, filter=ChannelParticipantsSearch("")):
                    if len(targets) >= requested: break
                    if not user.bot and user.id not in [u.id for u in targets]: targets.append(user)
            except: pass

        bot.edit_message_text(f"⚔️ **تم الصيد!**\nوجدت {len(targets)} هدف حقيقي.\nبدء الإضافة الفعلية داخل المجموعة...", uid, mid)

        for user in targets:
            if added >= requested: break
            for cl in clients:
                try:
                    await cl(functions.channels.InviteToChannelRequest(target, [user]))
                    added += 1
                    db_manage("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                    
                    # تحديث النتيجة للمشترك
                    new_bal = float(db_manage("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0])
                    bot.edit_message_text(f"🔥 **عملية نقل جارية..**\n━━━━━━━━━━━━━━\n✅ تم النقل: `{added}/{requested}`\n💰 الرصيد المتبقي: `{new_bal:.2f}$`", uid, mid)
                    
                    await asyncio.sleep(random.randint(40, 60)) # تأخير آمن جداً
                    break 
                except errors.FloodWaitError as e:
                    continue # ننتقل للحساب التالي
                except:
                    continue
                    
    except Exception as e: 
        bot.send_message(uid, f"🏁 **انتهت العملية:** {e}")
    
    bot.send_message(uid, f"✅ **تمت المهمة بنجاح!**\nمجموع ما تم إضافته فعلياً: {added} عضو.")

# --- 💳 نظام الشحن المتكامل (تلقائي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment_hub(m):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("⚡ شحن تلقائي (USDT/TRX)", callback_data="oxa_auto"),
        types.InlineKeyboardButton("📸 شحن يدوي (إرسال إيصال)", callback_data="manual_pay")
    )
    bot.send_message(m.chat.id, "💎 **مركز شحن الرصيد**\n\nيرجى اختيار وسيلة الدفع المناسبة لك:\n*(الشحن التلقائي يضيف الرصيد فوراً بعد الدفع)*", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = c.message.chat.id
    if c.data == "oxa_auto":
        msg = bot.send_message(uid, "💵 أدخل المبلغ الذي تود شحنه بالدولار (مثال: 10):")
        bot.register_next_step_handler(msg, create_oxa_invoice)
    
    elif c.data == "manual_pay":
        bot.send_message(uid, f"📍 **التحويل اليدوي:**\nحول للمحفظة التالية (TRC20):\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا ليقوم الأدمن بتأكيدها.")

    elif c.data.startswith("check_"):
        _, track_id, amt = c.data.split("_")
        r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': track_id}).json()
        if r.get('status') == 'Paid':
            db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), uid))
            bot.edit_message_text(f"⭐ **تم الدفع بنجاح!**\nتم إضافة {amt}$ إلى رصيدك. يمكنك البدء بالنقل الآن.", uid, c.message.message_id)
        else:
            bot.answer_callback_query(c.id, "⏳ لم يتم استلام الدفع بعد.. تأكد من التحويل.", show_alert=True)

    elif c.data.startswith("confirm_"):
        _, amt, target_id = c.data.split("_")
        db_manage("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target_id)))
        bot.send_message(int(target_id), f"✅ **تم تأكيد شحن رصيدك بمبلغ {amt}$**\nشكراً لثقتك بنا!")
        bot.edit_message_caption(f"✅ تم تأكيد الشحن لـ {target_id}", uid, c.message.message_id)

def create_oxa_invoice(m):
    try:
        amt = float(m.text)
        r = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if r.get('payLink'):
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=r['payLink']))
            kb.add(types.InlineKeyboardButton("✅ تحقق من العملية", callback_data=f"check_{r['trackId']}_{amt}"))
            bot.send_message(m.chat.id, f"📝 **فاتورة دفع رقم {r['trackId']}**\nالمبلغ: {amt}$\nيرجى الدفع عبر الرابط ثم الضغط على تحقق:", reply_markup=kb)
    except: bot.send_message(m.chat.id, "⚠️ خطأ في إدخال المبلغ.")

# --- 📱 لوحة التحكم والأوامر ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء نقل أعضاء", "👤 حسابي")
    m.add("➕ إضافة حسابات", "🗑️ حذف الحسابات")
    m.add("💰 شحن الرصيد")
    return m

@bot.message_handler(commands=['start'])
def start_cmd(m):
    db_manage("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (m.chat.id,))
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في نظام دراجون V40**\nالنظام الأقوى لنقل الأعضاء وتكبير المجموعات.\n\n💰 رصيدك الحالي: `{bal:.2f}$`", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    res = db_manage("SELECT balance FROM users WHERE user_id=?", (m.chat.id,), True)
    bal = float(res[0][0]) if res else 0.0
    acc_count = db_manage("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.chat.id,), True)[0][0]
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n━━━━━━━━━━━━━━\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal:.2f}$`\n📱 الحسابات المرتبطة: `{acc_count}`\n━━━━━━━━━━━━━━\n* سعر العضو الواحد: {PRICE_PER_MEMBER}$")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء نقل أعضاء")
def init_transfer(m):
    msg = bot.send_message(m.chat.id, "📥 **الخطوة 1:** أرسل يوزر المجموعة (المصدر) التي تريد السحب منها:")
    bot.register_next_step_handler(msg, get_source)

def get_source(m):
    src = m.text.replace("@", "")
    msg = bot.send_message(m.chat.id, "🎯 **الخطوة 2:** أرسل يوزر مجموعتك التي سيتم النقل إليها:")
    bot.register_next_step_handler(msg, get_target, src)

def get_target(m, src):
    trg = m.text.replace("@", "")
    msg = bot.send_message(m.chat.id, "🔢 **الخطوة 3:** أدخل عدد الأعضاء المطلوب نقله:")
    bot.register_next_step_handler(msg, run_final, src, trg)

def run_final(m, src, trg):
    try:
        num = int(m.text)
        mid = bot.send_message(m.chat.id, "⏳ جاري فحص البيانات وتجهيز المحرك...").message_id
        threading.Thread(target=lambda: asyncio.run(super_dragon_engine(m.chat.id, src, trg, num, mid))).start()
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال عدد صحيح.")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_account_init(m):
    bot.send_message(m.chat.id, "📱 **إضافة حساب سحب جديد**\nأرسل رقم الهاتف مع مفتاح الدولة (مثال: +9665xxxxx):")
    bot.register_next_step_handler(m, add_account_step2)

def add_account_step2(m):
    phone = m.text.strip()
    cl = TelegramClient(StringSession(), API_ID, API_HASH)
    async def get_code():
        await cl.connect()
        res = await cl.send_code_request(phone)
        return res.phone_code_hash, cl.session.save()
    try:
        hash_id, session_str = asyncio.run(get_code())
        msg = bot.send_message(m.chat.id, "📩 وصلك كود على التليجرام، أرسله هنا:")
        bot.register_next_step_handler(msg, add_account_step3, phone, hash_id, session_str)
    except Exception as e: bot.send_message(m.chat.id, f"❌ حدث خطأ: {e}")

def add_account_step3(m, phone, hash_id, session_str):
    cl = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    async def sign_in():
        await cl.connect()
        try:
            await cl.sign_in(phone, m.text, phone_code_hash=hash_id)
            return "OK", cl.session.save()
        except errors.SessionPasswordNeededError:
            return "2FA", cl.session.save()
    try:
        status, final_session = asyncio.run(sign_in())
        if status == "OK":
            db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, final_session, phone))
            bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح! يمكنك الآن استخدامه في النقل.")
        else:
            msg = bot.send_message(m.chat.id, "🔐 الحساب محمي بخطوتين، أرسل كلمة السر:")
            bot.register_next_step_handler(msg, add_account_step4, final_session, phone)
    except: bot.send_message(m.chat.id, "❌ الكود خاطئ أو انتهت صلاحيته.")

def add_account_step4(m, session_str, phone):
    cl = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    async def log2fa():
        await cl.connect()
        await cl.sign_in(password=m.text)
        return cl.session.save()
    try:
        final_s = asyncio.run(log2fa())
        db_manage("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, final_s, phone))
        bot.send_message(m.chat.id, "✅ تم فك الحماية وربط الحساب بنجاح!")
    except: bot.send_message(m.chat.id, "❌ كلمة السر خاطئة.")

@bot.message_handler(content_types=['photo'])
def handle_manual_receipt(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ تأكيد 10$", callback_data=f"confirm_10.0_{m.chat.id}"),
        types.InlineKeyboardButton("✅ تأكيد 20$", callback_data=f"confirm_20.0_{m.chat.id}")
    )
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 **إيصال جديد للشحن اليدوي:**\nآيدي المستخدم: `{m.chat.id}`", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ تم إرسال إيصالك للمراجعة، سيصلك إشعار عند التفعيل.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف الحسابات")
def delete_accs(m):
    db_manage("DELETE FROM accounts WHERE user_id=?", (m.chat.id,))
    bot.send_message(m.chat.id, "🗑️ تم حذف جميع حسابات السحب الخاصة بك من النظام.")

bot.infinity_polling()
