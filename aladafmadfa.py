import telebot
from telebot import types
import sqlite3
import threading
import time
import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# ================= [ 🛠️ إعداداتك الخاصة ] =================
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb43787fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
PRICE_PER_MEMBER = 0.01  
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)

def init_db():
    conn = sqlite3.connect('mega_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY, user_id INTEGER, session_string TEXT, phone TEXT)')
    conn.commit()
    conn.close()

def get_balance(uid):
    try:
        conn = sqlite3.connect('mega_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        res = cursor.fetchone()
        conn.close()
        if not res:
            conn = sqlite3.connect('mega_bot.db')
            conn.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (uid, 0.0))
            conn.commit()
            conn.close()
            return 0.0
        return round(res[0], 2)
    except: return 0.0

def update_balance(uid, amount):
    conn = sqlite3.connect('mega_bot.db')
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔄 بدء النقل (جيش الحسابات)", "➕ إضافة حساب للجيش")
    markup.add("💰 شحن الرصيد", "👤 حسابي")
    markup.add("🗑️ حذف حساب من الجيش")
    bot.send_message(message.chat.id, f"🐲 مرحباً بك في بوت دراجون.\n💰 رصيدك الحالي: {get_balance(message.chat.id)}$", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(message):
    uid = message.chat.id
    bal = get_balance(uid)
    conn = sqlite3.connect('mega_bot.db')
    acc_count = conn.execute("SELECT COUNT(*) FROM user_accounts WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    bot.send_message(uid, f"👤 **معلومات حسابك**\n\n🆔 الآيدي: `{uid}`\n💰 الرصيد: {bal}$\n📱 جيش الحسابات: {acc_count}", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن تلقائي (Crypto)", callback_data="pay_auto"))
    markup.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إثبات)", callback_data="pay_manual_info"))
    bot.send_message(message.chat.id, "اختر طريقة الشحن المفضلة لديك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data.startswith("check_"):
        _, tid, amt = call.data.split("_")
        res = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
        if res.get('status') == 'Paid' or res.get('payStatus') == 'Paid':
            update_balance(call.message.chat.id, float(amt))
            bot.send_message(call.message.chat.id, f"✅ تم تأكيد الدفع! أضيفت {amt}$ لرصيدك.")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ لم يتم استلام المبلغ بعد.", show_alert=True)
    elif call.data.startswith("del_"):
        aid = call.data.split("_")[1]
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("DELETE FROM user_accounts WHERE id=?", (aid,))
        conn.commit()
        conn.close()
        bot.edit_message_text("✅ تم حذف الحساب من جيشك بنجاح.", call.message.chat.id, call.message.message_id)
    elif call.data == "pay_auto":
        bot.register_next_step_handler(bot.send_message(call.message.chat.id, "💰 أدخل المبلغ الذي تريد شحنه بالدولار ($):"), create_invoice)
    elif call.data == "pay_manual_info":
        msg = f"💳 **الشحن اليدوي (USDT TRC20)**\n\n📍 العنوان:\n`{MY_WALLET}`\n\n⚠️ بعد التحويل، أرسل صورة الإثبات هنا 👇"
        bot.register_next_step_handler(bot.send_message(call.message.chat.id, msg, parse_mode="Markdown"), receive_proof)
    elif call.data.startswith("adm_"):
        p = call.data.split("_")
        if p[1] == "confirm":
            update_balance(int(p[3]), float(p[2]))
            bot.send_message(int(p[3]), f"✅ تم قبول طلبك وشحن {p[2]}$ في حسابك!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

def create_invoice(message):
    try:
        amt = float(message.text.strip())
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'lifeTime': 30}).json()
        url = res.get('payLink') or res.get('payUrl')
        if url:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 دفع الآن", url=url), types.InlineKeyboardButton("✅ تحقق", callback_data=f"check_{res.get('trackId')}_{amt}"))
            bot.send_message(message.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$:", reply_markup=markup)
    except: bot.send_message(message.chat.id, "⚠️ يرجى إدخال مبلغ صحيح.")

def receive_proof(message):
    if message.content_type == 'photo':
        uid = message.chat.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_confirm_5_{uid}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_confirm_10_{uid}"))
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📩 طلب شحن يدوي\nالآيدي: `{uid}`", reply_markup=markup)
        bot.send_message(uid, "⏳ تم إرسال الإثبات للمراجعة.")
    else: bot.send_message(message.chat.id, "⚠️ يرجى إرسال صورة الإثبات.")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_account_start(message):
    if get_balance(message.chat.id) <= 0:
        bot.send_message(message.chat.id, "❌ رصيدك 0$. اشحن أولاً لتتمكن من إضافة حسابات.")
        return
    bot.register_next_step_handler(bot.send_message(message.chat.id, "📱 أرسل رقم الهاتف مع رمز الدولة (+...):"), send_otp)

def send_otp(message):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def process():
        await client.connect()
        res = await client.send_code_request(phone)
        return res.phone_code_hash, client.session.save()
    try:
        h, s = asyncio.run(process())
        msg = bot.send_message(message.chat.id, "📩 أرسل الكود الآن:")
        bot.register_next_step_handler(msg, save_session, phone, h, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")
    finally:
        try: asyncio.run(client.disconnect())
        except: pass

def save_session(message, phone, h, s):
    otp = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def process():
        await client.connect()
        await client.sign_in(phone, otp, phone_code_hash=h)
        return client.session.save()
    try:
        fs = asyncio.run(process())
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ تم ربط الحساب بنجاح!")
    except SessionPasswordNeededError:
        bot.register_next_step_handler(bot.send_message(message.chat.id, "🔐 أرسل كلمة السر (2FA):"), save_session_2fa, phone, s)
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")
    finally:
        try: asyncio.run(client.disconnect())
        except: pass

def save_session_2fa(message, phone, s):
    pw = message.text.strip()
    client = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def process():
        await client.connect()
        await client.sign_in(password=pw)
        return client.session.save()
    try:
        fs = asyncio.run(process())
        conn = sqlite3.connect('mega_bot.db')
        conn.execute("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (message.chat.id, fs, phone))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ تم الربط!")
    except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")
    finally:
        try: asyncio.run(client.disconnect())
        except: pass

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def delete_menu_start(message):
    uid = message.chat.id
    conn = sqlite3.connect('mega_bot.db')
    accs = conn.execute("SELECT id, phone FROM user_accounts WHERE user_id=?", (uid,)).fetchall()
    conn.close()
    if not accs:
        bot.send_message(uid, "❌ ليس لديك حسابات.")
        return
    markup = types.InlineKeyboardMarkup()
    for aid, ph in accs:
        markup.add(types.InlineKeyboardButton(f"❌ حذف {ph}", callback_data=f"del_{aid}"))
    bot.send_message(uid, "اختر الحساب المراد حذفه:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (جيش الحسابات)")
def start_transfer_ui(message):
    msg = (
        "📝 **يرجى إرسال بيانات النقل بالترتيب التالي:**\n\n"
        "`رابط_المصدر رابط_الهدف العدد`\n\n"
        "💡 **مثال:**\n"
        "`t.me/source t.me/target 100`"
    )
    bot.register_next_step_handler(bot.send_message(message.chat.id, msg, parse_mode="Markdown"), run_transfer)
def run_transfer(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "⚠️ الصيغة: `المصدر الهدف العدد`")
            return
        src, dest, amount = parts[0], parts[1], int(parts[2])
        user_bal = get_balance(message.chat.id)
        cost = amount * PRICE_PER_MEMBER
        
        if user_bal < cost:
            possible = int(user_bal / PRICE_PER_MEMBER)
            bot.send_message(message.chat.id, f"❌ رصيدك لا يكفي!\n💰 التكلفة: {cost}$\n💵 رصيدك: {user_bal}$\n💡 يمكنك نقل {possible} فقط.")
            return

        conn = sqlite3.connect('mega_bot.db')
        sessions = [r[0] for r in conn.execute("SELECT session_string FROM user_accounts WHERE user_id=?", (message.chat.id,)).fetchall()]
        conn.close()
        
        if not sessions:
            bot.send_message(message.chat.id, "❌ أضف حسابات للجيش أولاً.")
            return

        update_balance(message.chat.id, -cost)
        
        # --- [ الرسالة المعتمدة ] ---
        conf_msg = (
            f"🚀 **تم استلام طلبك بنجاح!**\n\n"
            f"🔹 **القروب المصدر:** {src}\n"
            f"🔸 **القروب الهدف:** {dest}\n"
            f"👥 **عدد الاعضاء:** {amount}\n\n"
            f"💳 **التكلفة:** {cost}$\n"
            f"⏳ جاري بدء النقل الآن..."
        )
        bot.send_message(message.chat.id, conf_msg, parse_mode="Markdown")
        threading.Thread(target=transfer_thread, args=(sessions, src, dest, amount, message.chat.id)).start()
    except: bot.send_message(message.chat.id, "⚠️ صيغة خاطئة.")

def transfer_thread(sessions, src, dest, total, uid):
    success, fail = 0, 0
    async def task():
        nonlocal success, fail
        try:
            main = TelegramClient(StringSession(sessions[0]), MY_API_ID, MY_API_HASH)
            await main.connect()
            try:
                await main(JoinChannelRequest(src))
                await main(JoinChannelRequest(dest))
            except: pass
            
            src_e = await main.get_entity(src)
            found_users = set()
            async for msg in main.iter_messages(src_e, limit=1000):
                if msg.sender_id and getattr(msg.sender, 'username', None):
                    found_users.add(msg.sender)
                if len(found_users) >= total * 2: break
            
            users = list(found_users)
            await main.disconnect()
            
            if not users:
                bot.send_message(uid, "⚠️ لم نجد متفاعلين في المصدر.")
                return

            for i, user in enumerate(users):
                if success >= total: break
                cl = TelegramClient(StringSession(sessions[i % len(sessions)]), MY_API_ID, MY_API_HASH)
                try:
                    await cl.connect()
                    await cl(InviteToChannelRequest(await cl.get_entity(dest), [user]))
                    success += 1
                    await cl.disconnect()
                    if success % 5 == 0: bot.send_message(uid, f"📈 تم إضافة {success} عضو...")
                    await asyncio.sleep(20)
                except: fail += 1
            bot.send_message(uid, f"🏁 انتهى النقل!\n✅ نجاح: {success}\n❌ فشل: {fail}")
        except Exception as e: bot.send_message(uid, f"⚠️ خطأ: {e}")
    asyncio.run(task())

if __name__ == "__main__":
    init_db()
    print("🔥 دراجون شغال.. توكل على الله.")
    while True:
        try: bot.infinity_polling(timeout=20)
        except: time.sleep(5)
