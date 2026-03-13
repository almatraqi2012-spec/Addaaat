import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 26569209
MY_API_HASH = '1f52802d99787e2213a8089417032724'
ADMIN_ID = 6016547718

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 إدارة البيانات والذاكرة الفولاذية ] ================
def init_db():
    conn = sqlite3.connect('dragon_v55.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect('dragon_v55.db')
    res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amount):
    curr = get_balance(uid)
    conn = sqlite3.connect('dragon_v55.db')
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amount, 2)))
    conn.commit(); conn.close()

def get_army(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ ⚔️ محرك الاكتساح الهجين V55 ] ================

async def dragon_core_engine(army, src_user, trg_user, total, uid):
    success = 0
    bot.send_message(uid, "📡 **بدأ رادار دراجون باختراق المصدر...**")
    
    scout_sess = army[0].replace('.session','')
    client = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await client.connect()
        source = await client.get_entity(src_user)
        target = await client.get_entity(trg_user)
        
        targets = []
        # سحب المتفاعلين في آخر 2000 رسالة
        async for m in client.iter_messages(source, limit=2000):
            if len(targets) >= total: break
            if m.sender_id and isinstance(await m.get_sender(), tl_types.User):
                u = await m.get_sender()
                if not u.bot: targets.append(u)
        
        await client.disconnect()
        if not targets: return bot.send_message(uid, "❌ لم نجد أعضاء نشطين لسحبهم.")
        
        bot.send_message(uid, f"🔥 **تم قنص {len(targets)} هدف. جاري الجر القسري...**")

        for i, t in enumerate(targets):
            if success >= total: break
            acc = army[i % len(army)].replace('.session','')
            cl = TelegramClient(acc, MY_API_ID, MY_API_HASH)
            try:
                await cl.connect()
                await cl(InviteToChannelRequest(target, [t]))
                success += 1
                update_balance(uid, -PRICE_PER_MEMBER)
                bot.send_message(uid, f"✅ [{success}/{total}] تم جر: `@{t.username or t.id}`")
                await cl.disconnect()
                await asyncio.sleep(random.randint(20, 40))
            except: 
                await cl.disconnect(); continue

        bot.send_message(uid, f"🏁 **تمت المهمة!**\n✅ الأعضاء الجدد: `{success}`\n💰 الرصيد المتبقي: `{get_balance(uid)}$` ")
    except Exception as e:
        bot.send_message(uid, f"❌ فشل المحرك: {e}")

# ================= [ 📱 الواجهة البرمجية الكاملة ] ================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط دراجون الشامل)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 إحصائيات النظام", "🗑️ حذف حساب من الجيش")
    bot.send_message(m.chat.id, "🐲 **إمبراطورية دراجون V55 - النسخة النهائية**\nجاهز لسحق المنافسين واكتساح المصادر.", reply_markup=mk)

# --- نظام إضافة الحسابات الفولاذي ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_phone(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي (مثال: 9665...):**")
    bot.register_next_step_handler(msg, save_phone)

def save_phone(m):
    ph = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{ph}"
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def get_code():
        await cl.connect()
        try: return (await cl.send_code_request(ph)).phone_code_hash, "OK"
        except Exception as e: return str(e), "ERR"
        finally: await cl.disconnect()
    h, status = asyncio.run(get_code())
    if status == "OK":
        msg = bot.send_message(m.chat.id, "📩 **أرسل كود التحقق (OTP):**")
        bot.register_next_step_handler(msg, login_otp, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ خطأ تلجرام: {h}")

def login_otp(m, ph, h, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await cl.connect()
        try:
            await cl.sign_in(ph, m.text, phone_code_hash=h)
            return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await cl.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": 
        bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح في الجيش!**")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **الحساب محمي بـ 2FA. أرسل كلمة السر:**")
        bot.register_next_step_handler(msg, login_2fa, sess)
    else: bot.send_message(m.chat.id, f"❌ فشل الدخول: {res}")

def login_2fa(m, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign_2fa():
        await cl.connect()
        try:
            await cl.sign_in(password=m.text)
            return "OK"
        except Exception as e: return str(e)
        finally: await cl.disconnect()
    res = asyncio.run(sign_2fa())
    if res == "OK": 
        bot.send_message(m.chat.id, "✅ **تم فك الحماية وربط الحساب بنجاح!**")
    else: bot.send_message(m.chat.id, f"❌ كلمة السر خاطئة: {res}")

# --- نظام الهجوم المطور ---
@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط دراجون الشامل)")
def attack_1(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ! أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, attack_2, army)

def attack_2(m, army):
    src = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**")
    bot.register_next_step_handler(msg, attack_3, army, src)

def attack_3(m, army, src):
    trg = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, attack_final, army, src, trg)

def attack_final(m, army, src, trg):
    try:
        n = int(m.text)
        if get_balance(m.chat.id) < (n * PRICE_PER_MEMBER): return bot.send_message(m.chat.id, "❌ رصيدك لا يكفي.")
        threading.Thread(target=lambda: asyncio.run(dragon_core_engine(army, src, trg, n, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# --- نظام الشحن ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="auto"),
           types.InlineKeyboardButton("💳 شحن يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن المناسبة:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "auto")
def auto_oxa(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ المطلوب ($):**")
    bot.register_next_step_handler(msg, oxa_exec)

def oxa_exec(m):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {m.text}$", reply_markup=mk)
        else: bot.send_message(m.chat.id, "❌ خطأ في بوابة الدفع.")
    except: bot.send_message(m.chat.id, "⚠️ مبلغ غير صحيح.")

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def manual_p(c):
    bot.send_message(c.message.chat.id, f"💳 حول لعنوان المحفظة وأرسل الإيصال:\n`{MY_WALLET}`")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ شحن 10$", callback_data=f"adm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارِ التأكد من الإيصال...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_confirm(c):
    d = c.data.split('_'); update_balance(int(d[2]), float(d[1]))
    bot.send_message(int(d[2]), f"🎉 تم تفعيل {d[1]}$ لرصيدك!"); bot.edit_message_caption("✅ تم التأكيد", c.message.chat.id, c.message.message_id)

# --- إحصائيات وحساب ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    army = get_army(m.chat.id)
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 الجيش: `{len(army)}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def sys_stats(m):
    total_sess = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **إحصائيات الإمبراطورية:**\n📱 إجمالي الحسابات المربوطة: `{total_sess}`")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_menu(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army: mk.add(types.InlineKeyboardButton(f"❌ {s.split('_')[-1]}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_exec(c):
    f = c.data.replace("del_", ""); os.remove(f) if os.path.exists(f) else None
    bot.edit_message_text("✅ تم حذف الحساب نهائياً.", c.message.chat.id, c.message.message_id)

if __name__ == '__main__':
    init_db()
    print("🐲 دراجون V55 جاهز لسحق التحدي...")
    bot.infinity_polling()
