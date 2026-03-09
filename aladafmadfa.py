import telebot, threading, time, asyncio, requests, random, os
from telebot import types
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.errors import *

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAFU30-IOr522e_y1H7NW5V_hN4R3yXMExg"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN)

# ================= [ 🛠️ نظام إدارة البيانات المحلي (الذاكرة) ] ================

def get_balance(uid):
    if not os.path.exists(f"bal_{uid}.txt"): return 0.0
    with open(f"bal_{uid}.txt", 'r') as f: return float(f.read())

def update_balance(uid, amount):
    bal = get_balance(uid) + amount
    with open(f"bal_{uid}.txt", 'w') as f: f.write(str(round(bal, 2)))

def is_user_added(user_id):
    if not os.path.exists("history.txt"): return False
    with open("history.txt", 'r') as f: return str(user_id) in f.read().splitlines()

def save_user_history(user_id):
    with open("history.txt", 'a') as f: f.write(str(user_id) + '\n')

def get_army_sessions(uid):
    # جلب جميع ملفات الجلسات الخاصة بالمستخدم
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ 📱 واجهة الأوامر والأزرار ] ================

def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("⚔️ بدء الهجوم (الرادار العميق)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب من الجيش")
    m.add("📊 إحصائيات النظام", "🛠️ الدعم الفني")
    return m

@bot.message_handler(commands=['start'])
def start_bot(m):
    bot.send_message(m.chat.id, "🐲 **أهلاً بك في منصة دراجون V36 السيادية!**\n\nنظام الجر القسري السحابي، الرادار العميق، والشحن الآلي بالتتبع الذكي.", reply_markup=main_markup(), parse_mode="Markdown")

# ================= [ ⚔️ محرك الرادار والجر القسري ] ================

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (الرادار العميق)")
def attack_flow(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ **جيشك فارغ!** أضف حسابات أولاً لتبدأ الهجوم.")
    bot.send_message(m.chat.id, "📡 **أرسل يوزر المجموعة المصدر (الضحية):**")
    bot.register_next_step_handler(m, get_source_group)

def get_source_group(m):
    src = m.text.strip().replace('@','').split('/')[-1]
    bot.send_message(m.chat.id, "🎯 **أرسل يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(m, get_target_group, src)

def get_target_group(m, src):
    trg = m.text.strip().replace('@','').split('/')[-1]
    bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله:**")
    bot.register_next_step_handler(m, process_final, src, trg)

def process_final(m, src, trg):
    try:
        count = int(m.text)
        balance = get_balance(m.chat.id)
        if balance < (count * PRICE_PER_MEMBER):
            return bot.send_message(m.chat.id, f"❌ رصيدك غير كافي! تحتاج `{count * PRICE_PER_MEMBER}$` لتنفيذ هذه العملية.")
        
        bot.send_message(m.chat.id, "⚔️ **بدأ رادار دراجون... جاري اختراق الحماية وقنص المتفاعلين!**")
        army = get_army_sessions(m.chat.id)
        threading.Thread(target=lambda: asyncio.run(dragon_engine(army, src, trg, count, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

async def dragon_engine(army, src, trg, total, uid):
    found_targets = []
    # استخدام حساب عشوائي من الجيش ككشاف (رادار)
    scout_sess = random.choice(army).replace('.session', '')
    client = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await client.connect()
        # الرادار العميق - مسح 5000 رسالة لصيد المتفاعلين فعلياً
        async for msg in client.iter_messages(src, limit=5000):
            if len(found_targets) >= total: break
            if msg.sender_id and not is_user_added(msg.sender_id):
                sender = await msg.get_sender()
                if isinstance(sender, tl_types.User) and not sender.bot and sender.username:
                    found_targets.append(sender)
                    save_user_history(sender.id) # حجز العضو فوراً لمنع التكرار
        await client.disconnect()
    except Exception as e: return bot.send_message(uid, f"❌ خطأ في الرادار: {e}")

    if not found_targets: return bot.send_message(uid, "❌ لم يتم العثور على أهداف جديدة (المجموعة محمية أو خاملة).")

    bot.send_message(uid, f"🚀 تم قنص `{len(found_targets)}` هدف. بدأت الغزوة والجر القسري...")
    
    success = 0
    for i, target in enumerate(found_targets):
        sess_now = army[i % len(army)].replace('.session', '')
        cl = TelegramClient(sess_now, MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            # الانضمام للمجموعة الهدف إذا لزم الأمر
            try: await cl(JoinChannelRequest(trg))
            except: pass
            
            # الجر القسري (Invite)
            await cl(InviteToChannelRequest(trg, [target]))
            
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER) # الخصم عند النجاح الفعلي
            bot.send_message(uid, f"✅ [{success}] تم جر: `@{target.username}`")
            
            await cl.disconnect()
            await asyncio.sleep(random.randint(40, 75)) # حد الأمان لتخطي حماية التلجرام
        except (UserPrivacyRestrictedError, UserAlreadyParticipantError): continue
        except FloodWaitError: continue
        except Exception: continue
            
    bot.send_message(uid, f"🏁 **انتهت الغزوة!**\n✅ المضاف فعلياً: `{success}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$`")

# ================= [ 💰 نظام الشحن التلقائي بالتتبع ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (تتبع ذكي)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المفضلة:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data == "pay_auto")
def auto_pay_flow(call):
    msg = bot.send_message(call.message.chat.id, "💰 أدخل المبلغ المطلوب شحنه ($):")
    bot.register_next_step_handler(msg, process_oxapay)

def process_oxapay(m):
    try:
        amount = float(m.text)
        payload = {'merchant': OXAPAY_KEY, 'amount': amount, 'currency': 'USD', 'description': str(m.chat.id)}
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            track_id = res.get('trackId')
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع الآن", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بـ {amount}$:\nسيتم إضافة الرصيد تلقائياً بعد الدفع.", reply_markup=mk)
            threading.Thread(target=poll_oxapay, args=(track_id, m.chat.id, amount)).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل مبلغاً صحيحاً.")

def poll_oxapay(track_id, uid, amount):
    # فحص الحالة كل 30 ثانية لمدة 20 دقيقة
    for _ in range(40):
        time.sleep(30)
        try:
            status = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': track_id}).json()
            if status.get('status') in ['Paid', 'Confirmed']:
                update_balance(uid, amount)
                bot.send_message(uid, f"🎊 **مبروك!** تم تأكيد الدفع وإضافة `{amount}$` لرصيدك بنجاح.")
                break
        except: continue

@bot.callback_query_handler(func=lambda call: call.data == "pay_manual")
def manual_pay(call):
    bot.send_message(call.message.chat.id, f"📌 حول لعنوان المحفظة:\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا.")
    bot.register_next_step_handler(call.message, wait_receipt)

def wait_receipt(m):
    if m.photo:
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🔔 طلب شحن يدوي من: `{m.chat.id}`")
        bot.send_message(m.chat.id, "✅ تم إرسال الإيصال للإدارة، سيتم التفعيل قريباً.")

# ================= [ 📱 إدارة الجيش والحسابات ] ================

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    bal = get_balance(m.chat.id)
    army_count = len(get_army_sessions(m.chat.id))
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{bal}$`\n📱 قوة الجيش: `{army_count}` حساب.")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_army_start(m):
    bot.send_message(m.chat.id, "📱 أرسل الرقم مع رمز الدولة (مثلاً +967...):")
    bot.register_next_step_handler(m, step_phone)

def step_phone(m):
    phone = m.text.strip()
    sess_name = f"sess_{m.chat.id}_{phone.replace('+', '')}"
    cl = TelegramClient(sess_name, MY_API_ID, MY_API_HASH)
    async def get_hash():
        await cl.connect()
        r = await cl.send_code_request(phone)
        return r.phone_code_hash
    try:
        h = asyncio.run(get_hash())
        bot.send_message(m.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(m, step_otp, phone, h, sess_name)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_otp(m, phone, h, sess_name):
    otp = m.text.strip()
    cl = TelegramClient(sess_name, MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try:
            await cl.sign_in(phone, otp, phone_code_hash=h)
            return False # No 2FA needed
        except SessionPasswordNeededError: return True # Needs 2FA
    try:
        needs_2fa = asyncio.run(login())
        if needs_2fa:
            bot.send_message(m.chat.id, "🔐 الحساب محمي بكلمة سر (2FA)، أرسلها الآن:")
            bot.register_next_step_handler(m, step_2fa, sess_name)
        else:
            bot.send_message(m.chat.id, "✅ تم ربط الحساب بالجيش بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_2fa(m, sess_name):
    pw = m.text.strip()
    cl = TelegramClient(sess_name, MY_API_ID, MY_API_HASH)
    async def login_2fa():
        await cl.connect()
        await cl.sign_in(password=pw)
    try:
        asyncio.run(login_2fa())
        bot.send_message(m.chat.id, "✅ تم ربط الحساب (2FA) بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def delete_army_list(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات لحذفها.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        phone = s.split('_')[-1].replace('.session', '')
        mk.add(types.InlineKeyboardButton(f"🗑️ {phone}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر حساباً لحذفه من الجيش:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def process_deletion(call):
    sess_file = call.data.replace("del_", "")
    if os.path.exists(sess_file):
        os.remove(sess_file)
        bot.edit_message_text("✅ تم حذف الحساب بنجاح.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def system_stats(m):
    users = len([f for f in os.listdir('.') if f.startswith('bal_')])
    army_total = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **إحصائيات دراجون الحالية:**\n\n👥 عدد المشتركين: `{users}`\n📱 إجمالي الجيش: `{army_total}` حساب.")

if __name__ == "__main__":
    print("🐲 Dragon V36 (The Legend) is Active...")
    bot.infinity_polling()
