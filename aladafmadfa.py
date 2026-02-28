import telebot
from telebot import types
import sqlite3, threading, time, asyncio, requests, random
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantRequest
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserPrivacyRestrictedError, PeerFloodError

# ================= [ ⚙️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFU30-IOr522e_y1H7NW5V_hN4R3yXMExg"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.01  # السعر للعضو الواحد
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- [ قاعدة البيانات ] ---
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

def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء النقل (نظام دراجون)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي")
    m.add("🗑️ حذف حساب من الجيش")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🐲 **مرحباً بكم في بوت دراجون المطور!**\n\nاسحب الأعضاء من أي مجموعة وضعهم في مجموعتك بضغطة زر.", reply_markup=main_markup(), parse_mode="Markdown")

# --- [ محرك السحب والجر القسري المعدل ] ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (نظام دراجون)")
def dragon_flow(m):
    bot.send_message(m.chat.id, "📡 **أرسل يوزر المجموعة المصدر (بدون @):**")
    bot.register_next_step_handler(m, get_source)

def get_source(m):
    src = m.text.strip().replace('@','')
    bot.send_message(m.chat.id, "🎯 **أرسل يوزر مجموعتك المستهدفة (بدون @):**")
    bot.register_next_step_handler(m, get_target, src)

def get_target(m, src):
    trg = m.text.strip().replace('@','')
    bot.send_message(m.chat.id, "🔢 **كم عدد الأعضاء المطلوب نقلهم؟**")
    bot.register_next_step_handler(m, final_check, src, trg)

def final_check(m, src, trg):
    try:
        count = int(m.text)
        balance = get_balance(m.chat.id)
        # لا نخصم الآن، سنخصم عند النجاح الحقيقي فقط
        
        sessions = [r[0] for r in db_exec("SELECT session_string FROM user_accounts WHERE user_id=?", (m.chat.id,), True)]
        if not sessions:
            return bot.send_message(m.chat.id, "❌ جيشك خالي! أضف حسابات (Sessions) أولاً.")

        bot.send_message(m.chat.id, f"⚔️ **بدأ الهجوم الآن...**\nسأحاول سحب `{count}` عضو.")
        threading.Thread(target=lambda: asyncio.run(run_dragon(sessions, src, trg, count, m.chat.id))).start()
    except ValueError:
        bot.send_message(m.chat.id, "⚠️ يرجى إدخال رقم صحيح.")

async def run_dragon(sessions, src, trg, total, uid):
    # استخدام حساب عشوائي للقنص
    hunter_session = random.choice(sessions)
    cl_hunter = TelegramClient(StringSession(hunter_session), MY_API_ID, MY_API_HASH)
    found = []
    
    try:
        await cl_hunter.connect()
        # قنص الأعضاء المتفاعلين فقط لضمان الجودة
        async for user in cl_hunter.iter_participants(src, limit=total*2):
            if len(found) >= total: break
            if user.username and not user.bot:
                found.append(user)
        await cl_hunter.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ فشل في قنص الأهداف: {e}")

    if not found:
        return bot.send_message(uid, "❌ لم يتم العثور على أعضاء متاحين للسحب.")

    bot.send_message(uid, f"🚀 تم قنص `{len(found)}` هدف. جاري الجر القسري بالجيش...")
    
    success_count = 0
    current_session_idx = 0
    
    for target in found:
        if success_count >= total: break
        
        # التأكد من الرصيد قبل كل إضافة
        if get_balance(uid) < PRICE_PER_MEMBER:
            bot.send_message(uid, "⚠️ توقف الهجوم! رصيدك نفد.")
            break

        # تبديل الحسابات (Rotation) لتجنب الحظر
        session_str = sessions[current_session_idx % len(sessions)]
        cl = TelegramClient(StringSession(session_str), MY_API_ID, MY_API_HASH)
        
        try:
            await cl.connect()
            # محاولة الإضافة
            await cl(InviteToChannelRequest(channel=trg, users=[target.username]))
            
            # --- [ الفحص الحقيقي ] ---
            # نتأكد من وجود العضو في القروب قبل طباعة النجاح
            try:
                await cl(GetParticipantRequest(channel=trg, participant=target.username))
                # إذا وصلنا هنا، العضو انضاف فعلاً
                success_count += 1
                db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                bot.send_message(uid, f"✅ [{success_count}] تم سحب وإضافة: `@{target.username}`")
            except:
                # العضو لم ينضف فعلياً (بسبب الخصوصية أو الحماية)
                pass
            
            await cl.disconnect()
            current_session_idx += 1
            await asyncio.sleep(8) # فاصل زمني للأمان
            
        except (UserPrivacyRestrictedError, PeerFloodError, FloodWaitError):
            current_session_idx += 1 # تغيير الحساب فوراً عند مواجهة مشكلة
            continue
        except Exception:
            continue
    
    bot.send_message(uid, f"🏁 **انتهت الغزوة!**\n✅ الإجمالي المضاف فعلياً: `{success_count}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$`")

# --- [ أزرار الإدارة والشحن والحساب ] ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    accs = db_exec("SELECT phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n\n🆔 الآيدي: `{m.chat.id}`\n💰 رصيدك: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(accs)}` حساب جاهز.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc(m):
    accs = db_exec("SELECT id, phone FROM user_accounts WHERE user_id=?", (m.chat.id,), True)
    if not accs: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات مرتبطة.")
    mk = types.InlineKeyboardMarkup()
    for aid, ph in accs: mk.add(types.InlineKeyboardButton(f"🗑️ {ph}", callback_data=f"del_{aid}"))
    bot.send_message(m.chat.id, "اختر الحساب المراد حذفه من الجيش:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="pay_auto"), 
           types.InlineKeyboardButton("💳 شحن يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة شحن الرصيد:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data.startswith("del_"):
        db_exec("DELETE FROM user_accounts WHERE id=?", (call.data.split("_")[1],))
        bot.edit_message_text("✅ تم حذف الحساب بنجاح.", uid, call.message.message_id)
    elif call.data == "pay_auto":
        msg = bot.send_message(uid, "💵 أدخل المبلغ الذي تريد شحنه بالدولار:")
        bot.register_next_step_handler(msg, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول المبلغ لعنوان USDT TRC20:\n`{MY_WALLET}`\n\nأرسل صورة الإيصال هنا للمراجعة.")
    elif call.data.startswith("adm_confirm_"):
        _, _, amt, tid = call.data.split("_")
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (float(amt), int(tid)))
        bot.send_message(int(tid), f"✅ تم تفعيل رصيدك بمبلغ {amt}$ بنجاح!")
        bot.edit_message_caption("✅ تم تفعيل الطلب.", call.message.chat.id, call.message.message_id)

def create_invoice(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("💳 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"تم إنشاء فاتورة بقيمة {amt}$:", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ يرجى إدخال مبلغ صحيح.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ تفعيل 5$", callback_data=f"adm_confirm_5_{m.chat.id}"),
               types.InlineKeyboardButton("✅ تفعيل 10$", callback_data=f"adm_confirm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"وصل إيصال شحن من:\nID: `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "✅ تم إرسال الإيصال للإدارة، سيتم التفعيل قريباً.")

# --- [ إضافة حسابات للجيش ] ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    bot.send_message(m.chat.id, "📱 أرسل رقم الهاتف مع مفتاح الدولة (مثال: +9677...):")
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
        bot.send_message(m.chat.id, "📩 أرسل كود التحقق الذي وصلك:")
        bot.register_next_step_handler(m, step_otp, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ حدث خطأ: {e}")

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
        ns, n2fa = asyncio.run(login())
        if n2fa:
            bot.send_message(m.chat.id, "🔐 الحساب محمي بكلمة سر، أرسلها الآن:")
            bot.register_next_step_handler(m, step_2fa, phone, ns)
        else:
            db_exec("INSERT INTO user_accounts (user_id, session_string, phone) VALUES (?, ?, ?)", (m.chat.id, ns, phone))
            bot.send_message(m.chat.id, f"✅ تم ربط الحساب ({phone}) بجيشك بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ كود خاطئ أو منتهي: {e}")

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
        bot.send_message(m.chat.id, "✅ تم فك التشفير وربط الحساب بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ كلمة السر خاطئة: {e}")

if __name__ == "__main__":
    print("🐲 دراجون المطور بدأ الغزو...")
    bot.infinity_polling()
