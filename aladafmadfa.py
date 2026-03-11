import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors

# ================= [ ⚙️ الإعدادات المركزية - تم التثبيت ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718

# بياناتك المالية (ركزت عليها هنا)
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" # مفتاح التاجر الخاص بك
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # محفظتك للاستلام اليدوي
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# [ وظائف الذاكرة لمنع التكرار - نمط سهم ]
def get_added_users():
    if not os.path.exists('memory.txt'): return []
    with open('memory.txt', 'r') as f: return f.read().splitlines()

def save_user_to_memory(user_id):
    with open('memory.txt', 'a') as f: f.write(str(user_id) + '\n')

# [ إدارة الرصيد - قاعدة بيانات SQL ]
def init_db():
    conn = sqlite3.connect('dragon_v42.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL)')
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect('dragon_v42.db')
    res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amount):
    curr = get_balance(uid)
    conn = sqlite3.connect('dragon_v42.db')
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amount, 2)))
    conn.commit(); conn.close()

def get_army(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ ⚔️ محرك رادار سهم (الجر العميق من الرسائل) ] ================

async def sahama_radar_engine(army, src_group, to_group, total_needed, uid):
    success = 0
    added_list = get_added_users()
    bot.send_message(uid, "📡 **جاري تفعيل رادار سهم.. مسح 5000 رسالة لاصطياد الأهداف...**")

    targets = []
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await scout.connect()
        async for message in scout.iter_messages(src_group, limit=5000):
            if len(targets) >= (total_needed * 3): break
            if message.sender_id and str(message.sender_id) not in added_list:
                sender = await message.get_sender()
                if isinstance(sender, tl_types.User) and not sender.bot:
                    if sender.id not in [u.id for u in targets]:
                        targets.append(sender)
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ فشل الرادار: {e}")

    if not targets: return bot.send_message(uid, "❌ لم يتم العثور على أهداف جديدة.")

    bot.send_message(uid, f"⚔️ **تم قنص {len(targets)} هدف. بدأ الجر القسري...**")

    for i, target in enumerate(targets):
        if success >= total_needed: break
        sess_now = army[i % len(army)].replace('.session','')
        client = TelegramClient(sess_now, MY_API_ID, MY_API_HASH)
        try:
            await client.connect()
            await client(functions.channels.InviteToChannelRequest(to_group, [target]))
            save_user_to_memory(target.id) # حفظ في الذاكرة لمنع التكرار
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total_needed}] تم جر: `@{target.username or target.id}`")
            await client.disconnect()
            await asyncio.sleep(random.randint(30, 60))
        except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
            save_user_to_memory(target.id); await client.disconnect(); continue
        except Exception: await client.disconnect(); continue

    bot.send_message(uid, f"🏁 **اكتملت المهمة!**\n✅ مضاف فعلياً: `{success}`\n💰 رصيدك: `{get_balance(uid)}$` ")

# ================= [ 💰 نظام الشحن (آلي Oxapay + يدوي) ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="auto_p"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="manual_p"))
    bot.send_message(m.chat.id, "⬇️ اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "auto_p")
def auto_oxa(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ المطلوب ($):**")
    bot.register_next_step_handler(msg, oxa_process)

def oxa_process(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع الآمن", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {amt}$", reply_markup=mk)
            threading.Thread(target=watch_oxa, args=(res.get('trackId'), m.chat.id, amt)).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

def watch_oxa(tid, uid, amt):
    for _ in range(30): # مراقبة لمدة 30 دقيقة
        time.sleep(60)
        try:
            r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
            if r.get('status') in ['Paid', 'Confirmed']:
                update_balance(uid, amt); bot.send_message(uid, f"🎉 تم شحن `{amt}$` بنجاح!"); break
        except: continue

@bot.callback_query_handler(func=lambda c: c.data == "manual_p")
def manual_instr(c):
    bot.send_message(c.message.chat.id, f"💳 **الشحن اليدوي:**\n\nقم بالتحويل للمحفظة:\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ شحن 5$", callback_data=f"adm_5_{m.chat.id}"),
                                             types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ تم إرسال الإيصال للمراجعة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_p(c):
    d = c.data.split('_'); update_balance(int(d[2]), float(d[1]))
    bot.send_message(int(d[2]), f"🎁 تم شحن {d[1]}$ لرصيدك!"); bot.edit_message_caption("✅ تم الشحن", c.message.chat.id, c.message.message_id)

# ================= [ 📱 الأزرار والواجهة الكاملة ] ================

@bot.message_handler(commands=['start'])
def start_bot(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط سهم العميق)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 إحصائيات النظام", "🗑️ حذف حساب")
    bot.send_message(m.chat.id, "🐲 **إمبراطورية دراجون V42 جاهزة!**\nكل الميزات مفعلة ببياناتك الرسمية.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط سهم العميق)")
def start_war(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ!")
    msg = bot.send_message(m.chat.id, "🎯 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "📥 **يوزر مجموعتك (بدون @):**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**"), lambda n: run_sahama_war(s, t, n))))

def run_sahama_war(s, t, n):
    try:
        count = int(n.text)
        if get_balance(n.chat.id) < (count * PRICE_PER_MEMBER): return bot.send_message(n.chat.id, "❌ رصيدك ناقص.")
        threading.Thread(target=lambda: asyncio.run(sahama_radar_engine(get_army(n.chat.id), s.text.strip(), t.text.strip(), count, n.chat.id))).start()
    except: bot.send_message(n.chat.id, "⚠️ خطأ في البيانات.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 الجيش: `{len(get_army(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def stats(m):
    u = len([f for f in os.listdir('.') if 'bal_' in f or 'db' in f])
    s = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **الإحصائيات:**\n👥 مستخدمين: `{u}`\n📱 حسابات: `{s}`")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    phone = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{phone}"
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def get_c():
        await client.connect()
        try: return (await client.send_code_request(phone)).phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    h, ok = asyncio.run(get_c())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 **أرسل كود التحقق:**")
        bot.register_next_step_handler(msg, process_otp, phone, h, sess)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {h}")

def process_otp(m, ph, h, sess):
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def log():
        await client.connect()
        try: await client.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    res, n2fa = asyncio.run(log())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم ربط الحساب!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **كلمة سر 2FA:**")
        bot.register_next_step_handler(msg, lambda m2: bot.send_message(m.chat.id, asyncio.run(login_2fa(sess, m2.text))))
    else: bot.send_message(m.chat.id, f"❌ فشل: {res}")

async def login_2fa(sess, pw):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH); await cl.connect()
    try: await cl.sign_in(password=pw); return "✅ تم بنجاح!"
    except Exception as e: return f"❌ خطأ: {e}"
    finally: await cl.disconnect()

init_db()
bot.infinity_polling()
