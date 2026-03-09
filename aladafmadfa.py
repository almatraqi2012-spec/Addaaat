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

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 🛠️ نظام إدارة البيانات المحلي ] ================

def get_balance(uid):
    file = f"bal_{uid}.txt"
    if not os.path.exists(file): return 0.0
    with open(file, 'r') as f: return float(f.read())

def update_balance(uid, amount):
    bal = get_balance(uid) + amount
    with open(f"bal_{uid}.txt", 'w') as f: f.write(str(round(bal, 2)))

def is_user_added(user_id):
    if not os.path.exists("history.txt"): return False
    with open("history.txt", 'r') as f: return str(user_id) in f.read().splitlines()

def save_user_history(user_id):
    with open("history.txt", 'a') as f: f.write(str(user_id) + '\n')

def get_army_sessions(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ 📱 واجهة المستخدم الرئيسية ] ================

def main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("⚔️ بدء الهجوم (الرادار العميق)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب من الجيش")
    m.add("📊 إحصائيات النظام", "🛠️ الدعم الفني")
    return m

@bot.message_handler(commands=['start'])
def start_bot(m):
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في منصة دراجون V36 الأسطورية!**\nأقوى نظام جر وقنص سحابي يعمل بنظام الرادار العميق وتتبع الدفع الذكي.", reply_markup=main_markup())

# ================= [ 🛡️ محرك إضافة الجيش (إصلاح التجمد) ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_army_init(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع رمز الدولة (مثلاً +213...):**")
    bot.register_next_step_handler(msg, step_phone)

def step_phone(m):
    phone = m.text.strip().replace(' ', '')
    sess_name = f"sess_{m.chat.id}_{phone.replace('+', '')}"
    client = TelegramClient(sess_name, MY_API_ID, MY_API_HASH)
    
    async def get_code():
        await client.connect()
        try:
            res = await client.send_code_request(phone)
            return res.phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    h, success = loop.run_until_complete(get_code())
    
    if success:
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود الذي وصلك الآن:**")
        bot.register_next_step_handler(msg, step_otp, phone, h, sess_name)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {h}")

def step_otp(m, phone, h, sess_name):
    otp = m.text.strip()
    client = TelegramClient(sess_name, MY_API_ID, MY_API_HASH)
    
    async def login():
        await client.connect()
        try:
            await client.sign_in(phone, otp, phone_code_hash=h)
            return "OK", False
        except SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    status, needs_2fa = loop.run_until_complete(login())

    if status == "OK": bot.send_message(m.chat.id, "✅ **تم ربط الحساب بجيشك السحابي بنجاح!**")
    elif needs_2fa:
        msg = bot.send_message(m.chat.id, "🔐 **الحساب محمي بـ (2FA)، أرسل كلمة السر:**")
        bot.register_next_step_handler(msg, step_2fa, phone, sess_name)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {status}")

def step_2fa(m, phone, sess_name):
    pw = m.text.strip()
    client = TelegramClient(sess_name, MY_API_ID, MY_API_HASH)
    async def login_2fa():
        await client.connect()
        try:
            await client.sign_in(password=pw)
            return True, "✅ تم الربط بنجاح!"
        except Exception as e: return False, str(e)
        finally: await client.disconnect()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ok, res = loop.run_until_complete(login_2fa())
    bot.send_message(m.chat.id, res)

# ================= [ ⚔️ محرك الرادار والجر القسري ] ================

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (الرادار العميق)")
def attack_flow(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ **جيشك فارغ!** أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المجموعة المصدر (الضحية):**")
    bot.register_next_step_handler(msg, get_src)

def get_src(m):
    src = m.text.strip().replace('@','').split('/')[-1]
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(msg, get_trg, src)

def get_trg(m, src):
    trg = m.text.strip().replace('@','').split('/')[-1]
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله:**")
    bot.register_next_step_handler(msg, run_attack, src, trg)

def run_attack(m, src, trg):
    try:
        count = int(m.text)
        if get_balance(m.chat.id) < (count * PRICE_PER_MEMBER):
            return bot.send_message(m.chat.id, f"❌ رصيدك لا يكفي! تحتاج `{count * PRICE_PER_MEMBER}$`")
        
        bot.send_message(m.chat.id, "⚔️ **بدأ رادار دراجون... جاري قنص الأهداف!**")
        threading.Thread(target=lambda: asyncio.run(dragon_core(get_army_sessions(m.chat.id), src, trg, count, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

async def dragon_core(army, src, trg, total, uid):
    found = []
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    try:
        await scout.connect()
        async for msg in scout.iter_messages(src, limit=5000):
            if len(found) >= total: break
            if msg.sender_id and not is_user_added(msg.sender_id):
                u = await msg.get_sender()
                if isinstance(u, tl_types.User) and u.username and not u.bot:
                    found.append(u); save_user_history(u.id)
        await scout.disconnect()
    except Exception as e: return bot.send_message(uid, f"❌ خطأ رادار: {e}")

    if not found: return bot.send_message(uid, "❌ لم يتم العثور على أهداف جديدة.")
    
    bot.send_message(uid, f"🚀 تم قنص `{len(found)}` هدف. جاري الجر القسري...")
    success = 0
    for i, target in enumerate(found):
        cl_sess = army[i % len(army)].replace('.session','')
        cl = TelegramClient(cl_sess, MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            try: await cl(JoinChannelRequest(trg))
            except: pass
            await cl(InviteToChannelRequest(trg, [target]))
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}] تم جر: `@{target.username}`")
            await cl.disconnect()
            await asyncio.sleep(random.randint(50, 80))
        except: continue
    bot.send_message(uid, f"🏁 **انتهت المهمة!**\n✅ المضاف: `{success}`\n💰 رصيدك: `{get_balance(uid)}$`")

# ================= [ 💰 نظام الشحن ولوحة تحكم المالك ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (تتبع)", callback_data="pay_auto"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data == "pay_auto")
def oxa_init(call):
    msg = bot.send_message(call.message.chat.id, "💰 أدخل المبلغ بالدولار ($):")
    bot.register_next_step_handler(msg, process_oxa)

def process_oxa(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            track_id = res.get('trackId')
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 دفع الآن", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ فاتورة بـ {amt}$\n⏳ جاري تتبع الدفع...", reply_markup=mk)
            threading.Thread(target=poll_oxa, args=(track_id, m.chat.id, amt)).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

def poll_oxa(tid, uid, amt):
    for _ in range(40):
        time.sleep(30)
        try:
            r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
            if r.get('status') in ['Paid', 'Confirmed']:
                update_balance(uid, amt); bot.send_message(uid, f"🎊 تم شحن `{amt}$` بنجاح!"); break
        except: continue

@bot.callback_query_handler(func=lambda call: call.data == "pay_manual")
def manual_init(call):
    bot.send_message(call.message.chat.id, f"📌 حول لـ: `{MY_WALLET}` وارسل صورة الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_receipts(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_5_{m.chat.id}"),
               types.InlineKeyboardButton("✅ 10$", callback_data=f"adm_10_{m.chat.id}"))
        mk.add(types.InlineKeyboardButton("✏️ مبلغ مخصص", callback_data=f"adm_cus_{m.chat.id}"),
               types.InlineKeyboardButton("❌ رفض", callback_data=f"adm_den_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"🔔 إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ تم إرسال إيصالك للمراجعة.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_actions(call):
    d = call.data.split('_')
    uid = int(d[2])
    if d[1] == "den":
        bot.send_message(uid, "❌ نعتذر، تم رفض إيصالك.")
        bot.edit_message_caption("❌ تم الرفض", call.message.chat.id, call.message.message_id)
    elif d[1] == "cus":
        msg = bot.send_message(ADMIN_ID, f"🔢 أرسل المبلغ المراد شحنه لـ `{uid}`:")
        bot.register_next_step_handler(msg, lambda m: [update_balance(uid, float(m.text)), bot.send_message(uid, f"🎁 تم شحن `{m.text}$` لرصيدك!"), bot.send_message(ADMIN_ID, "✅ تم!")])
    else:
        amt = float(d[1])
        update_balance(uid, amt)
        bot.send_message(uid, f"🎁 تم شحن `{amt}$` لرصيدك بنجاح!")
        bot.edit_message_caption(f"✅ تم شحن {amt}$", call.message.chat.id, call.message.message_id)

# ================= [ ⚙️ بقية الأزرار والإحصائيات ] ================

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(get_army_sessions(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_army(m):
    army = get_army_sessions(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        p = s.split('_')[-1].replace('.session','')
        mk.add(types.InlineKeyboardButton(f"🗑️ {p}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر حساباً لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def del_proc(call):
    s = call.data.replace("del_","")
    if os.path.exists(s): os.remove(s)
    bot.edit_message_text("✅ تم الحذف.", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def stats(m):
    u = len([f for f in os.listdir('.') if f.startswith('bal_')])
    a = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **إحصائيات دراجون:**\n👥 المشتركين: `{u}`\n📱 إجمالي الجيش: `{a}`")

if __name__ == "__main__":
    print("🐲 Dragon V36 (Absolute Edition) is Active...")
    bot.infinity_polling()
