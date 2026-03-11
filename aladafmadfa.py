import telebot, threading, time, asyncio, requests, random, os
from telebot import types
from telethon import TelegramClient, functions, types as tl_types
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import UserStatusRecently, UserStatusOnline, UserStatusOffline
from telethon.errors import *

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAE39BjBYZbk8ps5dg3Ix9yIVC7cIx5B_cg"
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
    m.add("⚔️ بدء الهجوم (الخوارزمية القاصفة)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي")
    m.add("🗑️ حذف حساب من الجيش", "📊 إحصائيات النظام")
    return m

@bot.message_handler(commands=['start'])
def start_bot(m):
    bot.clear_step_handler_by_chat_id(chat_id=m.chat.id)
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في دراجون V36 الأسطورية!**\nتم دمج خوارزميات التحدي مع نظام الإدارة الكامل.", reply_markup=main_markup())

# ================= [ ⚔️ خوارزمية التحدي: الجر القسري الفعلي ] ================

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (الخوارزمية القاصفة)")
def attack_init(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ! أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **أرسل يوزر المجموعة المصدر (الضحية):**")
    bot.register_next_step_handler(msg, get_source)

def get_source(m):
    src = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🎯 **أرسل يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(msg, get_target, src)

def get_target(m, src):
    trg = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله (فعلياً):**")
    bot.register_next_step_handler(msg, process_attack, src, trg)

def process_attack(m, src, trg):
    try:
        count = int(m.text)
        if get_balance(m.chat.id) < (count * PRICE_PER_MEMBER):
            return bot.send_message(m.chat.id, "❌ رصيدك لا يكفي لهذه العملية.")
        bot.send_message(m.chat.id, f"⚔️ **بدأ هجوم التحدي.. جاري قنص {count} عضو وإضافتهم قسراً!**")
        threading.Thread(target=lambda: asyncio.run(dragon_core_engine(get_army_sessions(m.chat.id), src, trg, count, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

async def dragon_core_engine(army, src, trg, total_needed, uid):
    success = 0
    scout = TelegramClient(army[0].replace('.session',''), MY_API_ID, MY_API_HASH)
    
    # مرحلة الرادار: سحب قائمة ضخمة للفلترة
    found_users = []
    try:
        await scout.connect()
        async for user in scout.iter_participants(src, limit=total_needed * 40):
            if user.username and not user.bot:
                if isinstance(user.status, (UserStatusRecently, UserStatusOnline)):
                    found_users.append(user)
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ خطأ في رادار السحب: {e}")

    if not found_users:
        return bot.send_message(uid, "❌ لم يتم العثور على أعضاء نشطين في المصدر.")

    # حلقة الجر القسري: لا تتوقف حتى اكتمال العدد أو انتهاء القائمة
    for target in found_users:
        if success >= total_needed:
            break
            
        sess_now = army[success % len(army)].replace('.session','')
        cl = TelegramClient(sess_now, MY_API_ID, MY_API_HASH)
        
        try:
            await cl.connect()
            try: await cl(JoinChannelRequest(trg))
            except: pass
            
            # محاولة الإضافة الفعلية
            await cl(InviteToChannelRequest(trg, [target]))
            
            # نجاح الإضافة
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total_needed}] تم اختراق وجر: `@{target.username}`")
            
            await cl.disconnect()
            await asyncio.sleep(random.randint(20, 40)) # حماية ذكية للحسابات
            
        except (UserPrivacyRestrictedError, UserAlreadyParticipantError, UserBannedInChannelError):
            await cl.disconnect()
            continue # تجاوز الخصوصية بصمت والانتقال لليوزر التالي فوراً
        except PeerFloodError:
            await cl.disconnect()
            continue # تخطي الحساب المتعب
        except Exception:
            await cl.disconnect()
            continue

    bot.send_message(uid, f"🏁 **انتهت الملحمة!**\n✅ المضاف فعلياً داخل القروب: `{success}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$`")

# ================= [ 🛡️ نظام إضافة الحسابات للجيش ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_army_start(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل رقم الهاتف مع رمز الدولة (مثال: +967...):**")
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
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    h, ok = loop.run_until_complete(get_h())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 **أرسل كود التحقق الآن:**")
        bot.register_next_step_handler(msg, process_otp, phone, h, sess_id)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {h}")

def process_otp(m, phone, h, sess):
    otp = m.text.strip()
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try:
            await client.sign_in(phone, otp, phone_code_hash=h)
            return "OK", False
        except SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res, needs_2fa = loop.run_until_complete(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ **تم إضافة الحساب لجيشك بنجاح!**")
    elif needs_2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أدخل كلمة السر (التحقق بخطوتين):**")
        bot.register_next_step_handler(msg, process_2fa, sess)
    else: bot.send_message(m.chat.id, f"❌ فشل: {res}")

def process_2fa(m, sess):
    pw = m.text.strip()
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign_2fa():
        await client.connect()
        try:
            await client.sign_in(password=pw)
            return "✅ تم الربط بنجاح!"
        except Exception as e: return f"❌ خطأ: {str(e)}"
        finally: await client.disconnect()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot.send_message(m.chat.id, loop.run_until_complete(sign_2fa()))

# ================= [ 💰 نظام الشحن المعدل ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="auto_p"),
        types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="manual_p")
    )
    bot.send_message(m.chat.id, "⬇️ اختر وسيلة الشحن المناسبة:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data in ["auto_p", "manual_p"])
def handle_payment_choice(call):
    bot.answer_callback_query(call.id)
    if call.data == "auto_p":
        msg = bot.send_message(call.message.chat.id, "💰 **أدخل المبلغ المطلوب بالدولار ($):**")
        bot.register_next_step_handler(msg, oxa_execute)
    elif call.data == "manual_p":
        instruction = (
            "💳 **قسم الشحن اليدوي:**\n\n"
            "1️⃣ قم بتحويل المبلغ للمحفظة التالية:\n"
            f"`{MY_WALLET}`\n\n"
            "2️⃣ بعد التحويل، **أرسل صورة الإيصال** هنا مباشرة.\n\n"
            "⚠️ سيقوم الأدمن بمراجعة الإيصال وتفعيل رصيدك."
        )
        bot.send_message(call.message.chat.id, instruction)

def oxa_execute(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اذهب لصفحة الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بـ {amt}$\nجاري المراقبة التلقائية...", reply_markup=mk)
            threading.Thread(target=watch_oxa, args=(res.get('trackId'), m.chat.id, amt)).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

def watch_oxa(tid, uid, amt):
    for _ in range(20):
        time.sleep(60)
        try:
            r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
            if r.get('status') in ['Paid', 'Confirmed']:
                update_balance(uid, amt)
                bot.send_message(uid, f"🎉 مبروك! تم تأكيد الدفع وشحن `{amt}$` آلياً.")
                break
        except: continue

@bot.message_handler(content_types=['photo'])
def manual_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_5_{m.chat.id}"),
               types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10_{m.chat.id}"))
        mk.add(types.InlineKeyboardButton("✏️ مخصص", callback_data=f"adm_cus_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال جديد من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ تم إرسال إيصالك للمراجعة من قبل الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_confirm(c):
    bot.answer_callback_query(c.id)
    d = c.data.split('_')
    uid = int(d[2])
    if d[1] == "cus":
        msg = bot.send_message(ADMIN_ID, f"🔢 أدخل المبلغ المراد شحنه لـ `{uid}`:")
        bot.register_next_step_handler(msg, lambda m: custom_charge(m, uid))
    else:
        amt = float(d[1])
        update_balance(uid, amt)
        bot.send_message(uid, f"🎁 تم شحن `{amt}$` لرصيدك بنجاح!")
        bot.edit_message_caption(f"✅ تم شحن {amt}$ لـ {uid}", c.message.chat.id, c.message.message_id)

def custom_charge(m, uid):
    try:
        amt = float(m.text)
        update_balance(uid, amt)
        bot.send_message(uid, f"🎁 تم إضافة `{amt}$` لرصيدك بنجاح!")
        bot.send_message(ADMIN_ID, "✅ تم الشحن بنجاح.")
    except: bot.send_message(ADMIN_ID, "❌ رقم غير صحيح.")

# ================= [ 📊 الحساب والإحصائيات ] ================

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n💰 الرصيد الحالي: `{get_balance(m.chat.id)}$`\n📱 قوة الجيش: `{len(get_army_sessions(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def stats(m):
    total_u = len([f for f in os.listdir('.') if f.startswith('bal_')])
    total_s = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **إحصائيات دراجون العميقة:**\n👥 عدد المستخدمين: `{total_u}`\n📱 إجمالي الحسابات: `{total_s}`")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_army_menu(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا تملك حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        p = s.split('_')[-1].replace('.session','')
        mk.add(types.InlineKeyboardButton(f"🗑️ {p}", callback_data=f"remove_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_"))
def del_army_exec(call):
    s = call.data.replace("remove_","")
    if os.path.exists(s): os.remove(s)
    bot.edit_message_text("✅ تم الحذف.", call.message.chat.id, call.message.message_id)

# ================= [ 🚀 التشغيل النهائي ] ================

if __name__ == "__main__":
    print("🐲 Dragon V36 (Challenge Mode) is Now Active!")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Error: {e}")
