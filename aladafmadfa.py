import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718

# بياناتك المالية المعتمدة
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 إدارة البيانات والذاكرة ] ================
def init_db():
    conn = sqlite3.connect('dragon_final.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL)')
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect('dragon_final.db')
    res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amount):
    curr = get_balance(uid)
    conn = sqlite3.connect('dragon_final.db')
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amount, 2)))
    conn.commit(); conn.close()

def get_army(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

def save_mem(user_id):
    with open('memory.txt', 'a') as f: f.write(str(user_id) + '\n')

def get_mem():
    if not os.path.exists('memory.txt'): return []
    with open('memory.txt', 'r') as f: return f.read().splitlines()

# ================= [ ⚔️ محرك رادار سهم العميق ] ================
async def sahama_engine(army, src, trg, total, uid):
    success = 0
    mem_list = get_mem()
    bot.send_message(uid, "📡 **بدأ رادار سهم بمسح 5000 رسالة...**")
    
    targets = []
    scout = TelegramClient(army[0].replace('.session',''), MY_API_ID, MY_API_HASH)
    try:
        await scout.connect()
        async for m in scout.iter_messages(src, limit=5000):
            if len(targets) >= total * 2: break
            if m.sender_id and str(m.sender_id) not in mem_list:
                s = await m.get_sender()
                if isinstance(s, tl_types.User) and not s.bot:
                    if s.id not in [u.id for u in targets]: targets.append(s)
        await scout.disconnect()
    except Exception as e: return bot.send_message(uid, f"❌ خطأ في الرادار: {e}")

    if not targets: return bot.send_message(uid, "❌ لم أجد أهدافاً جديدة.")
    bot.send_message(uid, f"⚔️ **تم صيد {len(targets)} هدف. بدأ الجر...**")

    for i, t in enumerate(targets):
        if success >= total: break
        cl = TelegramClient(army[i % len(army)].replace('.session',''), MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            await cl(functions.channels.InviteToChannelRequest(trg, [t]))
            save_mem(t.id); success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total}] جر: `@{t.username or t.id}`")
            await cl.disconnect(); await asyncio.sleep(random.randint(30, 50))
        except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
            save_mem(t.id); await cl.disconnect(); continue
        except Exception: await cl.disconnect(); continue

    bot.send_message(uid, f"🏁 **اكتمل الهجوم!**\n✅ المضاف: `{success}`\n💰 رصيدك: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة والأزرار ] ================
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط سهم العميق)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي", "📊 إحصائيات النظام", "🗑️ حذف حساب من الجيش")
    bot.send_message(m.chat.id, "🐲 **إمبراطورية دراجون V43 المكتملة**\nببياناتك الرسمية ورادار سهم العميق.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط سهم العميق)")
def attack_init(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ!")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, get_trg)

def get_trg(m):
    src = m.text.strip()
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**")
    bot.register_next_step_handler(msg, get_num, src)

def get_num(m, src):
    trg = m.text.strip()
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, final_run, src, trg)

def final_run(m, src, trg):
    try:
        n = int(m.text)
        if get_balance(m.chat.id) < (n * PRICE_PER_MEMBER): return bot.send_message(m.chat.id, "❌ رصيدك لا يكفي.")
        threading.Thread(target=lambda: asyncio.run(sahama_engine(get_army(m.chat.id), src, trg, n, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# ================= [ 💰 نظام الشحن ] ================
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ آلي (Oxapay)", callback_data="auto"),
           types.InlineKeyboardButton("💳 يدوي (إيصال)", callback_data="manual"))
    bot.send_message(m.chat.id, "وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "auto")
def auto_pay(c):
    msg = bot.send_message(c.message.chat.id, "💵 **المبلغ بالدولار ($):**")
    bot.register_next_step_handler(msg, oxa_exec)

def oxa_exec(m):
    try:
        amt = float(m.text)
        r = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if r.get('payLink'):
            bot.send_message(m.chat.id, f"✅ اتبع الرابط للدفع: {r['payLink']}")
    except: bot.send_message(m.chat.id, "⚠️ خطأ.")

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def manual_pay(c):
    bot.send_message(c.message.chat.id, f"💳 حول للمحفظة وأرسل الإيصال:\n`{MY_WALLET}`")

@bot.message_handler(content_types=['photo'])
def receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ شحن 5$", callback_data=f"adm_5_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارِ المراجعة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def adm_confirm(c):
    d = c.data.split('_'); update_balance(int(d[2]), float(d[1]))
    bot.send_message(int(d[2]), f"🎉 تم شحن {d[1]}$!"); bot.edit_message_caption("✅ تم", c.message.chat.id, c.message.message_id)

# ================= [ 🛡️ إضافة وحذف الحسابات ] ================
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم بالمفتاح الدولي:**")
    bot.register_next_step_handler(msg, ph_step)

def ph_step(m):
    ph = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{ph}"
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def get_c():
        await client.connect()
        try: return (await client.send_code_request(ph)).phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    h, ok = asyncio.run(get_c())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
        bot.register_next_step_handler(msg, otp_step, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ {h}")

def otp_step(m, ph, h, sess):
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try: await client.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة السر:**")
        bot.register_next_step_handler(msg, lambda m2: bot.send_message(m.chat.id, asyncio.run(sign_2fa(sess, m2.text))))

async def sign_2fa(sess, pw):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH); await cl.connect()
    try: await cl.sign_in(password=pw); return "✅ تم!"
    except Exception as e: return f"❌ {e}"
    finally: await cl.disconnect()

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_menu(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        p = s.split('_')[-1].replace('.session','')
        mk.add(types.InlineKeyboardButton(f"❌ {p}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_exec(c):
    file = c.data.replace("del_", "")
    if os.path.exists(file): os.remove(file)
    bot.edit_message_text("✅ تم الحذف.", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    bot.send_message(m.chat.id, f"👤 **رصيدك:** `{get_balance(m.chat.id)}$`\n📱 **جيشك:** `{len(get_army(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def stats(m):
    s = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **الحسابات الكلية في البوت:** `{s}`")

init_db()
bot.infinity_polling()
