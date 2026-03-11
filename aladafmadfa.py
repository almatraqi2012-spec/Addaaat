import telebot, threading, time, asyncio, requests, random, os
from telebot import types
from telethon import TelegramClient, functions, types as tl_types
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import UserStatusRecently, UserStatusOnline
from telethon.errors import *

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 🛠️ إدارة البيانات والرصيد ] ================

def get_balance(uid):
    file = f"bal_{uid}.txt"
    if not os.path.exists(file): return 0.0
    with open(file, 'r') as f:
        try: return float(f.read())
        except: return 0.0

def update_balance(uid, amount):
    bal = get_balance(uid) + amount
    with open(f"bal_{uid}.txt", 'w') as f: f.write(str(round(bal, 2)))

def get_army_sessions(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ 📱 واجهة الأزرار الكاملة ] ================

def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("⚔️ بدء الهجوم (قوة التحدي الفعلي)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي")
    m.add("🗑️ حذف حساب من الجيش", "📊 إحصائيات النظام")
    return m

@bot.message_handler(commands=['start'])
def start_bot(m):
    bot.clear_step_handler_by_chat_id(chat_id=m.chat.id)
    bot.send_message(m.chat.id, "🐲 **إمبراطورية دراجون V39 جاهزة!**\nنظام الجر القسري + كامل صلاحيات الإدارة نشط الآن.", reply_markup=main_markup())

# ================= [ ⚔️ محرك التحدي: الجر القسري والفلترة ] ================

async def dragon_core_challenge(army, src, trg, total_needed, uid):
    success = 0
    attempt_idx = 0
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await scout.connect()
        targets = []
        # رادار يسحب 1500 عضو لضمان إيجاد العدد الصافي المطلق
        async for u in scout.iter_participants(src, limit=1500):
            if u.username and not u.bot:
                if isinstance(u.status, (UserStatusRecently, UserStatusOnline)):
                    targets.append(u)
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ خطأ في السحب: {e}")

    if not targets: return bot.send_message(uid, "❌ المصدر محمي أو لا يحتوي أعضاء نشطين.")

    bot.send_message(uid, f"⚔️ **بدأ الجر القسري.. لن أتوقف حتى أكمل {total_needed} عضو في قروبك!**")

    # حلقة التحدي: محاولات لا تنتهي حتى اكتمال العدد الفعلي
    for target in targets:
        if success >= total_needed: break
        
        sess_now = army[attempt_idx % len(army)].replace('.session','')
        client = TelegramClient(sess_now, MY_API_ID, MY_API_HASH)
        attempt_idx += 1
        
        try:
            await client.connect()
            try: await client(JoinChannelRequest(trg))
            except: pass
            
            # محاولة الجر الفعلي
            await client(InviteToChannelRequest(trg, [target]))
            
            # احتساب النجاح والخصم فقط عند الدخول الفعلي
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total_needed}] تم جر: `@{target.username}`")
            
            await client.disconnect()
            await asyncio.sleep(random.randint(20, 35)) # حماية ذكية
            
        except (UserPrivacyRestrictedError, UserAlreadyParticipantError, UserBannedInChannelError):
            await client.disconnect(); continue # تخطي الخصوصية فوراً
        except PeerFloodError:
            await client.disconnect(); continue # تبديل الحساب
        except Exception:
            await client.disconnect(); continue

    bot.send_message(uid, f"🏁 **اكتمل التحدي!**\n✅ المضاف فعلياً: `{success}`\n💰 رصيدك: `{get_balance(uid)}$` ")

# ================= [ 🛡️ إضافة الحسابات + التحقق 2FA ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_army_start(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل رقم الهاتف (مثال: +967...):**")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    phone = m.text.strip().replace(' ', '')
    sess_id = f"sess_{m.chat.id}_{phone.replace('+', '')}"
    client = TelegramClient(sess_id, MY_API_ID, MY_API_HASH)
    async def get_h():
        await client.connect()
        try:
            res = await client.send_code_request(phone)
            return res.phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    
    h, ok = asyncio.run(get_h())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 **أرسل كود التحقق:**")
        bot.register_next_step_handler(msg, process_otp, phone, h, sess_id)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {h}")

def process_otp(m, ph, h, sess):
    otp = m.text.strip()
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try:
            await client.sign_in(ph, otp, phone_code_hash=h)
            return "OK", False
        except SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()

    res, need_2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ **تم الربط بنجاح!**")
    elif need_2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أدخل كلمة السر (2FA):**")
        bot.register_next_step_handler(msg, process_2fa, sess)
    else: bot.send_message(m.chat.id, f"❌ فشل: {res}")

def process_2fa(m, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def s2():
        await cl.connect()
        try: await cl.sign_in(password=m.text.strip()); return "✅ تم بنجاح"
        except Exception as e: return f"❌ خطأ: {e}"
        finally: await cl.disconnect()
    bot.send_message(m.chat.id, asyncio.run(s2()))

# ================= [ 💰 نظام الشحن (آلي + يدوي + لوحة أدمن) ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="auto"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ["auto", "manual"])
def pay_choice(c):
    if c.data == "auto":
        msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
        bot.register_next_step_handler(msg, oxa_go)
    else:
        bot.send_message(c.message.chat.id, f"💳 **المحفظة:**\n`{MY_WALLET}`\n\nأرسل صورة الإيصال هنا.")

def oxa_go(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بـ {amt}$", reply_markup=mk)
            threading.Thread(target=watch_oxa, args=(res.get('trackId'), m.chat.id, amt)).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

def watch_oxa(tid, uid, amt):
    for _ in range(20):
        time.sleep(60)
        try:
            r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
            if r.get('status') in ['Paid', 'Confirmed']:
                update_balance(uid, amt); bot.send_message(uid, f"🎉 تم الشحن آلياً!"); break
        except: continue

@bot.message_handler(content_types=['photo'])
def receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"a_5_{m.chat.id}"),
               types.InlineKeyboardButton("✅ 10$", callback_data=f"a_10_{m.chat.id}"),
               types.InlineKeyboardButton("✏️ مخصص", callback_data=f"a_c_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ تم الإرسال للأدمن...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("a_"))
def adm_res(c):
    d = c.data.split('_'); uid = int(d[2])
    if d[1] == "c":
        msg = bot.send_message(ADMIN_ID, "المبلغ:")
        bot.register_next_step_handler(msg, lambda m: [update_balance(uid, float(m.text)), bot.send_message(uid, f"🎁 تم شحن {m.text}$!")])
    else:
        update_balance(uid, float(d[1])); bot.send_message(uid, f"🎁 تم شحن {d[1]}$!")
    bot.edit_message_caption("✅ تم الشحن", c.message.chat.id, c.message.message_id)

# ================= [ 📊 الميزات التكميلية (حسابي، حذف، إحصاء) ] ================

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 الجيش: `{len(get_army_sessions(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def stats(m):
    u = len([f for f in os.listdir('.') if f.startswith('bal_')])
    s = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **إحصائيات دراجون:**\n👥 مستخدمين: `{u}`\n📱 حسابات: `{s}`")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_army(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army: mk.add(types.InlineKeyboardButton(f"🗑️ {s}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def rm_ex(c):
    s = c.data.replace("rm_","")
    if os.path.exists(s): os.remove(s)
    bot.edit_message_text("✅ تم الحذف.", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (قوة التحدي الفعلي)")
def start_h(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ!")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, get_s)

def get_s(m):
    s = m.text.strip().replace('@',''); msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**")
    bot.register_next_step_handler(msg, get_t, s)

def get_t(m, s):
    t = m.text.strip().replace('@',''); msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, lambda mn: run_fin(mn, s, t))

def run_fin(m, s, t):
    try:
        n = int(m.text)
        if get_balance(m.chat.id) < (n * PRICE_PER_MEMBER): return bot.send_message(m.chat.id, "❌ رصيد ناقص.")
        threading.Thread(target=lambda: asyncio.run(dragon_core_challenge(get_army_sessions(m.chat.id), s, t, n, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ بيانات.")

if __name__ == "__main__":
    bot.delete_webhook(drop_pending_updates=True)
    bot.infinity_polling()
