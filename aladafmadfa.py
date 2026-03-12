import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from telethon.tl.types import UserStatusRecently, UserStatusOnline

# ================= [ ⚙️ الإعدادات المركزية - بياناتك الرسمية ] ===============
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 26569209
MY_API_HASH = '1f52802d99787e2213a8089417032724'
ADMIN_ID = 6016547718

# بياناتك المالية
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 إدارة البيانات والذاكرة الفولاذية ] ================
def init_db():
    conn = sqlite3.connect('dragon_final_v45.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL)')
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect('dragon_final_v45.db')
    res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amount):
    curr = get_balance(uid)
    conn = sqlite3.connect('dragon_final_v45.db')
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amount, 2)))
    conn.commit(); conn.close()

def save_mem(uid):
    with open('memory.txt', 'a') as f: f.write(str(uid) + '\n')

def get_mem():
    return open('memory.txt', 'r').read().splitlines() if os.path.exists('memory.txt') else []

def get_army(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ ⚔️ محرك الاكتساح الهجين (رادار سهم + دراجون) ] ================

async def dragon_core_v45(army, src, trg, total, uid):
    success = 0
    mem_list = get_mem()
    bot.send_message(uid, "📡 **جاري اختراق المصدر بـ (الرادار العميق)...**")
    
    targets = []
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await scout.connect()
        # محاولة الانضمام لفك التشفير
        try: await scout(JoinChannelRequest(src))
        except: pass
        
        # 1. صيد المتفاعلين من الرسائل (آخر 2000 رسالة)
        async for m in scout.iter_messages(src, limit=2000):
            if len(targets) >= total * 1.5: break
            if m.sender_id and str(m.sender_id) not in mem_list:
                s = await m.get_sender()
                if isinstance(s, tl_types.User) and not s.bot:
                    if s.id not in [u.id for u in targets]: targets.append(s)
        
        # 2. دعم السحب من قائمة الأعضاء النشطين (إذا نقص العدد)
        if len(targets) < total:
            async for u in scout.iter_participants(src, limit=1000):
                if len(targets) >= total * 2: break
                if str(u.id) not in mem_list and not u.bot:
                    if isinstance(u.status, (UserStatusRecently, UserStatusOnline)):
                        targets.append(u)
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ فشل الرادار: {e}")

    if not targets: return bot.send_message(uid, "❌ المصدر محمي أو فارغ.")
    bot.send_message(uid, f"⚔️ **تم قنص {len(targets)} هدف متفاعل. بدأ الجر القسري!**")

    # [ عملية الإضافة - تدوير الجيش ]
    for i, target in enumerate(targets):
        if success >= total: break
        
        sess_now = army[i % len(army)].replace('.session','')
        client = TelegramClient(sess_now, MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            # الانضمام للهدف لضمان الصلاحية
            try: await client(JoinChannelRequest(trg))
            except: pass
            
            await client(InviteToChannelRequest(trg, [target]))
            save_mem(target.id)
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total}] تم جر: `@{target.username or target.id}`")
            await client.disconnect()
            await asyncio.sleep(random.randint(25, 45))
            
        except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
            save_mem(target.id); await client.disconnect(); continue
        except Exception:
            await client.disconnect(); continue

    bot.send_message(uid, f"🏁 **اكتمل الهجوم!**\n✅ المضاف: `{success}`\n💰 الرصيد: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة البرمجية الكاملة ] ================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط دراجون الشامل)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي", "📊 إحصائيات النظام", "🗑️ حذف حساب من الجيش")
    bot.send_message(m.chat.id, "🐲 **إمبراطورية دراجون V45 - النسخة النهائية**\nجاهز للاكتساح وتحطيم التحديات.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط دراجون الشامل)")
def attack_step1(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ! أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, attack_step2)

def attack_step2(m):
    src = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**")
    bot.register_next_step_handler(msg, attack_step3, src)

def attack_step3(m, src):
    trg = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, attack_final, src, trg)

def attack_final(m, src, trg):
    try:
        n = int(m.text)
        if get_balance(m.chat.id) < (n * PRICE_PER_MEMBER): return bot.send_message(m.chat.id, "❌ رصيدك ناقص.")
        threading.Thread(target=lambda: asyncio.run(dragon_core_v45(get_army(m.chat.id), src, trg, n, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقم صحيح.")

# [ نظام إضافة الحسابات مع 2FA ]
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_phone(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, save_phone)

def save_phone(m):
    ph = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{ph}"
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def get_code():
        await client.connect()
        try: return (await client.send_code_request(ph)).phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    h, ok = asyncio.run(get_code())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
        bot.register_next_step_handler(msg, login_otp, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ {h}")

def login_otp(m, ph, h, sess):
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try: await client.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم ربط الحساب!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر (2FA):**")
        bot.register_next_step_handler(msg, login_2fa, sess)
    else: bot.send_message(m.chat.id, f"❌ {res}")

async def login_2fa(m, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH); await cl.connect()
    try: await cl.sign_in(password=m.text); bot.send_message(m.chat.id, "✅ تم الربط بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")
    finally: await cl.disconnect()

# [ نظام الشحن والمحفظة ]
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="auto"),
           types.InlineKeyboardButton("💳 شحن يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "auto")
def oxa_pay(c):
    msg = bot.send_message(c.message.chat.id, "💵 **المبلغ ($):**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"✅ الفاتورة: {requests.post('https://api.oxapay.com/merchants/request', json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD', 'description': str(m.chat.id)}).json().get('payLink', 'خطأ')}"))

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def man_pay(c):
    bot.send_message(c.message.chat.id, f"💳 حول هنا وأرسل الإيصال:\n`{MY_WALLET}`")

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ شحن 5$", callback_data=f"adm_5_{m.chat.id}"),
                                             types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من `{m.chat.id}`", reply_markup=mk); bot.reply_to(m, "⏳ جارِ المراجعة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def adm_pay(c):
    d = c.data.split('_'); update_balance(int(d[2]), float(d[1]))
    bot.send_message(int(d[2]), f"🎁 تم شحن {d[1]}$!"); bot.edit_message_caption("✅ تم التأكيد", c.message.chat.id, c.message.message_id)

# [ الحذف والإحصائيات ]
@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army: mk.add(types.InlineKeyboardButton(f"❌ {s.split('_')[-1]}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_confirm(c):
    f = c.data.replace("del_", "")
    if os.path.exists(f): os.remove(f)
    bot.edit_message_text("✅ تم الحذف.", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 الجيش: `{len(get_army(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def stats(m):
    s = len([f for f in os.listdir('.') if f.endswith('.session')])
    u = len([f for f in os.listdir('.') if 'db' in f or 'bal_' in f])
    bot.send_message(m.chat.id, f"📊 **إحصائيات:**\n👥 مستخدمين: `{u}`\n📱 حسابات كلية: `{s}`")

init_db()
bot.infinity_polling()
