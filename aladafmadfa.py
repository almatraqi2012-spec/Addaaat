import telebot
from telebot import types
import sqlite3, threading, time, asyncio, requests, random
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserPrivacyRestrictedError, PeerFloodError

# ================= [ ⚙️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFU30-IOr522e_y1H7NW5V_hN4R3yXMExg"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125
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
    finally: conn.close()

db_exec('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_exec('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')

def get_balance(uid):
    res = db_exec("SELECT balance FROM users WHERE user_id=?", (uid,), True)
    if not res:
        db_exec("INSERT INTO users (user_id, balance) VALUES (?, ?)", (uid, 0.0))
        return 0.0
    return round(res[0][0], 2)

# --- الكيبورد الرئيسي ---
def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء النقل (نظام دراجون)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب من الجيش")
    return m

# --- الأوامر الأساسية ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🐲 **مرحباً بكم في بوت دراجون العابر للقارات لأضافة الاعضاء للقروبك من اي قروب تريده!**", reply_markup=main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    accs = db_exec("SELECT phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    msg = f"👤 **معلومات حسابك:**\n\n🆔 الآيدي: `{m.chat.id}`\n💰 رصيدك: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(accs)}` حساب."
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

# --- نظام الشحن (كامل ومصلح) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن تلقائي (Crypto)", callback_data="pay_auto"),
        types.InlineKeyboardButton("💳 شحن يدوي (بواسطة الإدمن)", callback_data="pay_manual")
    )
    bot.send_message(m.chat.id, "اختر الطريقة المناسبة للشحن:", reply_markup=mk)

def create_invoice(m):
    try:
        amt = float(m.text.strip())
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            mk.add(types.InlineKeyboardButton("✅ تحقق من الدفع", callback_data=f"check_{res.get('trackId')}_{amt}"))
            bot.send_message(m.chat.id, f"🔗 فاتورة شحن بقيمة {amt}$:", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال مبلغ صحيح.")

def wait_for_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup()
        mk.add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_confirm_5_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_confirm_10_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 20$", callback_data=f"adm_confirm_20_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 50$", callback_data=f"adm_confirm_50_{m.chat.id}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن يدوي\n👤 المستخدم: `{m.chat.id}`", reply_markup=mk, parse_mode="Markdown")
        bot.send_message(m.chat.id, "✅ تم إرسال الإيصال للإدارة. سيتم التفعيل قريباً.")
    else: bot.send_message(m.chat.id, "⚠️ يرجى إرسال صورة الإيصال فقط.")

# --- نظام حذف الحسابات (كامل ومصلح) ---
@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc_menu(m):
    accs = db_exec("SELECT id, phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    if not accs: return bot.send_message(m.chat.id, "❌ جيشك خالي حالياً.")
    mk = types.InlineKeyboardMarkup()
    for aid, ph in accs:
        mk.add(types.InlineKeyboardButton(f"🗑️ حذف {ph}", callback_data=f"del_{aid}"))
    bot.send_message(m.chat.id, "اختر الحساب المراد حذفه من القاعدة:", reply_markup=mk)

# --- معالج الأزرار الموحد (القلب النابض) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    uid = call.message.chat.id
    data = call.data

    # 1. معالجة الحذف
    if data.startswith("del_"):
        acc_id = data.split("_")[1]
        db_exec("DELETE FROM user_accounts WHERE id=?", (acc_id,))
        bot.edit_message_text("✅ تم حذف الحساب بنجاح من جيشك.", uid, call.message.message_id)

    # 2. معالجة الشحن التلقائي
    elif data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ الذي تريد شحنه ($):")
        bot.register_next_step_handler(msg, create_invoice)

    # 3. معالجة الشحن اليدوي
    elif data == "pay_manual":
        bot.send_message(uid, f"📌 **يرجى تحويل المبلغ إلى المحفظة التالية:**\n\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا 👇")
        bot.register_next_step_handler(call.message, wait_for_receipt)

    # 4. تأكيد الإدارة للشحن اليدوي
    elif data.startswith("adm_confirm_"):
        _, _, amt, target_id = data.split("_")
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target_id)))
        bot.send_message(int(target_id), f"✅ **مبروك! تم تفعيل رصيدك بـ {amt}$!**")
        bot.edit_message_caption(f"✅ تم قبول الطلب وشحن {amt}$ لـ {target_id}", call.message.chat.id, call.message.message_id)

    # 5. التحقق من بوابة OxaPay
    elif data.startswith("check_"):
        _, tid, amt = data.split("_")
        res = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
        if res.get('status') == 'Paid':
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), uid))
            bot.send_message(uid, f"✅ تم استلام {amt}$ بنجاح!")
        else: bot.answer_callback_query(call.id, "❌ لم يتم العثور على دفع مكتمل.", show_alert=True)

# --- نظام الإضافة (التحدي العابر للقارات) ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    bot.send_message(m.chat.id, "📱 أرسل الرقم مع المفتاح الدولي (مثال: +967...):")
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
        bot.send_message(m.chat.id, "📩 أرسل كود التحقق الآن:")
        bot.register_next_step_handler(m, step_otp, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_otp(m, phone, h, s):
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(phone, otp, phone_code_hash=h)
            return cl.session.save(), False
        except SessionPasswordNeededError: return cl.session.save(), True
    try:
        new_s, need_2fa = asyncio.run(login())
        if need_2fa:
            bot.send_message(m.chat.id, "🔐 الحساب محمي، أرسل كلمة السر (2FA):")
            bot.register_next_step_handler(m, step_2fa, phone, new_s)
        else:
            db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, new_s, phone))
            bot.send_message(m.chat.id, "✅ تم ربط الجندي بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_2fa(m, phone, s):
    pw = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login_2fa(): await cl.connect(); await cl.sign_in(password=pw); return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, fs, phone))
        bot.send_message(m.chat.id, "✅ تم التجاوز والربط بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

# --- محرك السحب الصاروخي (نظام التحدي) ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (نظام دراجون)")
def dragon_flow(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك لا يكفي للبدء.")
    bot.send_message(m.chat.id, "📡 **يوزر المجموعة المصدر (الضحية):**")
    bot.register_next_step_handler(m, lambda msg: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (الهدف):**"), 
        lambda msg2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله:**"), 
        final_dragon, msg.text.strip().replace('@',''), msg2.text.strip().replace('@',''))))

def final_dragon(m, src, trg):
    try:
        count = int(m.text)
        sessions = [r[0] for r in db_exec("SELECT session_string FROM user_accounts WHERE user_id=?", (m.chat.id,), True)]
        if not sessions: return bot.send_message(m.chat.id, "❌ جيشك خالي.")
        db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (count * PRICE_PER_MEMBER, m.chat.id))
        bot.send_message(m.chat.id, "⚔️ **انطلق الصاروخ.. جاري السحب بنظام التحدي!**")
        threading.Thread(target=lambda: asyncio.run(run_dragon(sessions, src, trg, count, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في الإدخال.")

async def run_dragon(sessions, src, trg, total, uid):
    found = []
    cl_hunter = TelegramClient(StringSession(random.choice(sessions)), MY_API_ID, MY_API_HASH)
    try:
        await cl_hunter.connect()
        async for user in cl_hunter.iter_participants(src, limit=total*2):
            if len(found) >= total: break
            if user.username and not user.bot: found.append(user)
        await cl_hunter.disconnect()
    except Exception as e: return bot.send_message(uid, f"❌ فشل القنص: {e}")

    success = 0
    for i, target in enumerate(found):
        if success >= total: break
        cl = TelegramClient(StringSession(sessions[i % len(sessions)]), MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            await cl(InviteToChannelRequest(channel=trg, users=[target.username]))
            success += 1
            bot.send_message(uid, f"🚀 [{success}] تم سحب: `@{target.username}` ✅")
            await cl.disconnect()
            await asyncio.sleep(12) # سرعة التحدي المتوازنة
        except: continue
    bot.send_message(uid, f"🏁 **اكتملت المهمة بنجاح!**\n✅ الإجمالي: `{success}`")

if __name__ == "__main__":
    print("🐲 البوت الصاروخي قيد التشغيل...")
    bot.infinity_polling()
