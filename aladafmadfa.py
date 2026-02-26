import telebot
from telebot import types
import sqlite3, threading, asyncio, requests, random
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsRecent
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserPrivacyRestrictedError

# ================= [ ⚙️ الإعدادات - عدل هذه فقط ] =================
BOT_TOKEN = "8574116889:AAFU30-IOr522e_y1H7NW5V_hN4R3yXMExg"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # محفظتك USDT
PRICE_PER_MEMBER = 0.01 
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- قاعدة البيانات ---
def db_exec(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_army.db', check_same_thread=False)
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

# --- القوائم ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء النقل (نظام دراجون)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, f"🐲 **أهلاً بك في بوت دراجون!**\n💰 رصيدك: `{get_balance(m.chat.id)}$`", reply_markup=main_menu(), parse_mode="Markdown")

# --- [ 1: نظام الشحن ] ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن تلقائي (كريبتو)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        bot.send_message(uid, "💰 أدخل المبلغ بالدولار ($):")
        bot.register_next_step_handler(call.message, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول للمحفظة: `{MY_WALLET}`\nثم أرسل صورة الإيصال هنا 👇")
        bot.register_next_step_handler(call.message, manual_receipt)
    elif call.data.startswith("adm_ok_"):
        _, _, amt, target = call.data.split("_")
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(target)))
        bot.send_message(int(target), f"✅ تم تفعيل رصيدك بـ {amt}$!")
        bot.edit_message_caption("✅ تم القبول.", call.message.chat.id, call.message.message_id)

def create_invoice(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"فاتورة شحن {amt}$:", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ رقم غير صحيح.")

def manual_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup()
        for v in [5, 10, 20, 50]: mk.add(types.InlineKeyboardButton(f"✅ شحن {v}$", callback_data=f"adm_ok_{v}_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "⏳ تم الإرسال للمراجعة.")
    else: bot.send_message(m.chat.id, "⚠️ أرسل صورة فقط.")

# --- [ 2: إضافة الحسابات و 2FA ] ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc(m):
    bot.send_message(m.chat.id, "📱 أرسل الرقم بمفتاح الدولة (مثال: +967...):")
    bot.register_next_step_handler(m, phone_step)

def phone_step(m):
    p = m.text.strip()
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_h(): await cl.connect(); r = await cl.send_code_request(p); return r.phone_code_hash, cl.session.save()
    try:
        h, s = asyncio.run(get_h())
        bot.send_message(m.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(m, otp_step, p, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def otp_step(m, p, h, s):
    o = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(p, o, phone_code_hash=h)
            return cl.session.save(), False
        except SessionPasswordNeededError: return cl.session.save(), True
    try:
        ns, need2 = asyncio.run(login())
        if need2:
            bot.send_message(m.chat.id, "🔐 الحساب محمي بكلمة سر، أرسلها الآن:")
            bot.register_next_step_handler(m, pass_2fa, p, ns)
        else:
            db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, ns, p))
            bot.send_message(m.chat.id, "✅ تم الربط!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ فشل: {e}")

def pass_2fa(m, p, s):
    pw = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log2(): await cl.connect(); await cl.sign_in(password=pw); return cl.session.save()
    try:
        fs = asyncio.run(log2())
        db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
        bot.send_message(m.chat.id, "✅ تم تجاوز الحماية والربط!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ غلط: {e}")

# --- [ 3: محرك سحب دراجون (الوحش) ] ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (نظام دراجون)")
def tr_1(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيدك ضعيف.")
    bot.send_message(m.chat.id, "📡 **1: يوزر المصدر (الذي سنسحب منه):**")
    bot.register_next_step_handler(m, tr_2)

def tr_2(m):
    src = m.text.strip().replace('@', '').split('/')[-1]
    bot.send_message(m.chat.id, "🎯 **2: يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(m, tr_3, src)

def tr_3(m, src):
    trg = m.text.strip().replace('@', '').split('/')[-1]
    bot.send_message(m.chat.id, "🔢 **3: العدد المطلوب جرّه:**")
    bot.register_next_step_handler(m, tr_final, src, trg)

def tr_final(m, src, trg):
    try:
        count = int(m.text)
        sessions = [r[0] for r in db_exec("SELECT session_string FROM user_accounts WHERE user_id=?", (m.chat.id,), True)]
        if not sessions: return bot.send_message(m.chat.id, "❌ جيشك خالي.")
        db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (count * PRICE_PER_MEMBER, m.chat.id))
        bot.send_message(m.chat.id, "⚔️ **دراجون انطلق لصيد المتفاعلين (ايموجي + دردشة)...**")
        threading.Thread(target=lambda: asyncio.run(dragon_engine(sessions, src, trg, count, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في البيانات.")
        async def dragon_engine(sessions, src, trg, total, uid):
    # 1: إعداد القائمة السوداء (عشان ما نكرر حد)
    already_tried = set()
    global_success = 0

    bot.send_message(uid, f"🚀 **انطلق جيش دراجون (تكتيك سهم العميق)...**")

    for s in sessions:
        if global_success >= total: break
        
        # استخراج اسم الحساب للتمويه
        acc_name = s[:10] + "..." 
        bot.send_message(uid, f"🔄 دور الحساب الآن: `{acc_name}`")
        
        cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            
            # صيد أهداف خاصة بهذا الحساب فقط (100 هدف جديد)
            targets = []
            async for msg in cl.iter_messages(src, limit=3000):
                if len(targets) >= 100: break
                if msg.sender_id and msg.sender_id not in already_tried:
                    if hasattr(msg.sender, 'username') and msg.sender.username:
                        targets.append(msg.sender)
                        already_tried.add(msg.sender_id)

            if not targets:
                await cl.disconnect()
                continue

            # بدء الجر بهذا الحساب (نفس نظام ملف التحدي - 15 عضو كحد أقصى للحساب)
            acc_success = 0
            for user in targets:
                if global_success >= total or acc_success >= 40: break
                
                try:
                    # الجر المباشر باليوزر
                    await cl(InviteToChannelRequest(trg, [user]))
                    acc_success += 1
                    global_success += 1
                    # طباعة النتيجة لحظياً مثل الترمكس
                    print(f"➕ أضاف بنجاح: {user.first_name}")
                except:
                    continue
                
                # انتظار بسيط بين كل جرّة (نفس السكربت)
                await asyncio.sleep(10)

            bot.send_message(uid, f"🏁 انتهى الحساب `{acc_name}`\n✅ أضاف: `{acc_success}` | المجموع الكلي: `{global_success}`")
            await cl.disconnect()
            
            # استراحة بين تبديل الحسابات
            await asyncio.sleep(5)

        except Exception as e:
            print(f"خطأ في الحساب: {e}")
            continue

    bot.send_message(uid, f"🏁 **اكتملت الغزوة الإمبراطورية!**\n✅ الإجمالي الذي تم إضافته فعلياً: `{global_success}`")


@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    accs = db_exec("SELECT phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    bot.send_message(m.chat.id, f"🆔 الآيدي: `{m.chat.id}`\n💰 رصيدك: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(accs)}` حساب.")
if __name__ == "__main__":
    import time
    print("🚀 نظام دراجون انطلق... لا تقلق من تنبيهات الاتصال المؤقتة")
    
    # دالة للتشغيل المستمر وتجاوز أخطاء الشبكة في الاستضافات
    def run_bot():
        while True:
            try:
                # timeout=10 و none_stop=True تجعل البوت يحاول الاتصال دائماً حتى لو تعثر السيرفر
                bot.polling(none_stop=True, interval=0, timeout=10)
            except Exception as e:
                # إذا حدث خطأ في الاتصال، سينتظر 5 ثواني ثم يعيد التشغيل تلقائياً
                print(f"❌ تنبيه: حدث خطأ اتصال (غالباً من السيرفر): {e}")
                time.sleep(5)

    run_bot()
