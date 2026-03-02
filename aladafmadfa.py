import telebot
from telebot import types
import pymongo, threading, time, asyncio, requests, random
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import *

# ================= [ ⚙️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAFU30-IOr522e_y1H7NW5V_hN4R3yXMExg"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04

# --- [ إعداد القاعدة السحابية MongoDB لضمان عدم المسح ] ---
# ضع رابط MongoDB Atlas الخاص بك هنا
MONGO_URL = "mongodb+srv://USER:PASS@cluster.mongodb.net/dragon" 
m_client = pymongo.MongoClient(MONGO_URL)
db = m_client['dragon_bot_db']
users_col = db['users']
accs_col = db['accounts']
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)

# --- [ دوال القاعدة السحابية الجديدة ] ---
def get_balance(uid):
    user = users_col.find_one({"user_id": uid})
    if not user:
        users_col.insert_one({"user_id": uid, "balance": 0.0})
        return 0.0
    return round(user.get('balance', 0.0), 2)

def update_balance(uid, amount):
    users_col.update_one({"user_id": uid}, {"$inc": {"balance": amount}}, upsert=True)

def get_main_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔄 بدء النقل (نظام دراجون)", "➕ إضافة حساب للجيش")
    m.add("💰 شحن الرصيد", "👤 حسابي", "🗑️ حذف حساب من الجيش")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🐲 **مرحباً بكم في بوت دراجون الأصلي - نظام الجر القسري السحابي!**", reply_markup=get_main_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    count = accs_col.count_documents({"user_id": m.chat.id})
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n\n🆔 الآيدي: `{m.chat.id}`\n💰 رصيدك: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{count}` حساب.", parse_mode="Markdown")

# --- [ محرك دراجون المطور - دقة الخصم وبقاء البيانات ] ---
@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل (نظام دراجون)")
def dragon_flow(m):
    bot.send_message(m.chat.id, "📡 **يوزر المجموعة المصدر (الضحية):**")
    bot.register_next_step_handler(m, get_source)

def get_source(m):
    src = m.text.strip().replace('@','').split('/')[-1]
    bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (الهدف):**")
    bot.register_next_step_handler(m, get_target, src)

def get_target(m, src):
    trg = m.text.strip().replace('@','').split('/')[-1]
    bot.send_message(m.chat.id, "🔢 **العدد المطلوب نقله:**")
    bot.register_next_step_handler(m, final_check, src, trg)

def final_check(m, src, trg):
    try:
        count = int(m.text)
        balance = get_balance(m.chat.id)
        if balance < (count * PRICE_PER_MEMBER):
            return bot.send_message(m.chat.id, f"❌ رصيدك غير كافي! تحتاج لـ {count * PRICE_PER_MEMBER}$")
        
        accs = list(accs_col.find({"user_id": m.chat.id}))
        if not accs:
            return bot.send_message(m.chat.id, "❌ أضف حسابات لجيشك أولاً لتبدأ الهجوم.")

        sessions = [a['session_string'] for a in accs]
        bot.send_message(m.chat.id, f"⚔️ **بدأ هجوم دراجون... جاري اختراق الحماية وقنص المتفاعلين!**")
        threading.Thread(target=lambda: asyncio.run(run_dragon(sessions, src, trg, count, m.chat.id))).start()
    except:
        bot.send_message(m.chat.id, "⚠️ أدخل رقم صحيح.")

async def run_dragon(sessions, src, trg, total, uid):
    found_targets = {}
    hunter_session = random.choice(sessions)
    cl_hunter = TelegramClient(StringSession(hunter_session), MY_API_ID, MY_API_HASH)
    
    try:
        await cl_hunter.connect()
        try: await cl_hunter(JoinChannelRequest(src))
        except: pass
        
        history = await cl_hunter(GetHistoryRequest(peer=src, limit=1000, offset_id=0, offset_date=None, add_offset=0, max_id=0, min_id=0, hash=0))
        
        for msg in history.messages:
            if len(found_targets) >= total: break
            if isinstance(msg.from_id, tl_types.PeerUser):
                u_id = msg.from_id.user_id
                if u_id not in found_targets:
                    user = await cl_hunter.get_entity(u_id)
                    if user.username and not user.bot:
                        found_targets[u_id] = user
        await cl_hunter.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ خطأ في القنص: {e}")

    if not found_targets:
        return bot.send_message(uid, "❌ لم يتم قنص متفاعلين (المجموعة محمية أو خاملة).")

    success = 0
    bot.send_message(uid, f"🚀 تم قنص `{len(found_targets)}` هدف. جاري الجر القسري والخصم بدقة...")
    
    targets_list = list(found_targets.values())
    for i, target in enumerate(targets_list):
        if success >= total: break
        s_str = sessions[i % len(sessions)]
        cl = TelegramClient(StringSession(s_str), MY_API_ID, MY_API_HASH)
        try:
            await cl.connect()
            try: await cl(JoinChannelRequest(trg))
            except: pass
            
            # محاولة الجر القسري
            await cl(InviteToChannelRequest(channel=trg, users=[target]))
            
            # --- التعديل الجوهري: الخصم والعد فقط عند النجاح الفعلي ---
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}] تم إضافة: `@{target.username}`")
            # -------------------------------------------------------
            
            await cl.disconnect()
            await asyncio.sleep(8)
        except:
            continue
            
    bot.send_message(uid, f"🏁 **انتهت الغزوة!**\n✅ المضاف فعلياً: `{success}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$`")

# --- [ باقي الميزات بنفس الكفاءة والقاعدة السحابية ] ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data.startswith("del_"):
        acc_id = call.data.split("_")[1]
        accs_col.delete_one({"_id": pymongo.ObjectId(acc_id)})
        bot.edit_message_text("✅ تم حذف الحساب من الجيش.", uid, call.message.message_id)
    elif call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ ($):")
        bot.register_next_step_handler(msg, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 عنوان محفظتنا USDT TRC20 لـ: `{MY_WALLET}` ثم أرسل الصورة.")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    elif call.data.startswith("adm_confirm_"):
        _, _, amt, tid = call.data.split("_")
        update_balance(int(tid), float(amt))
        bot.send_message(int(tid), f"✅ تم تفعيل شحن بـ {amt}$!")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ آلي", callback_data="pay_auto"), types.InlineKeyboardButton("💳 يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=mk)

def create_invoice(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"فاتورة بـ {amt}$:", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ خطأ في معالجة المبلغ.")

def wait_for_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"✅ تفعيل", callback_data=f"adm_confirm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"طلب شحن من {m.chat.id}", reply_markup=mk)
        bot.send_message(m.chat.id, "✅ تم الإرسال للمراجعة.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc(m):
    accs = list(accs_col.find({"user_id": m.chat.id}))
    if not accs: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for a in accs: 
        mk.add(types.InlineKeyboardButton(f"🗑️ {a['phone']}", callback_data=f"del_{a['_id']}"))
    bot.send_message(m.chat.id, "اختر حساباً لحذفه:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    bot.send_message(m.chat.id, "📱 أرسل الرقم مع رمز الدولة (مثلاً +967...):")
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
        bot.send_message(m.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(m, step_otp, phone, h, s)
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_otp(m, phone, h, s):
    otp = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login():
        await cl.connect()
        try: await cl.sign_in(phone, otp, phone_code_hash=h); return cl.session.save(), False
        except SessionPasswordNeededError: return cl.session.save(), True
    try:
        ns, n2fa = asyncio.run(login())
        if n2fa:
            bot.send_message(m.chat.id, "🔐 أرسل كلمة السر (2FA):")
            bot.register_next_step_handler(m, step_2fa, phone, ns)
        else:
            accs_col.insert_one({"user_id": m.chat.id, "session_string": ns, "phone": phone})
            bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

def step_2fa(m, phone, s):
    pw = m.text.strip()
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def login_2fa(): await cl.connect(); await cl.sign_in(password=pw); return cl.session.save()
    try:
        fs = asyncio.run(login_2fa())
        accs_col.insert_one({"user_id": m.chat.id, "session_string": fs, "phone": phone})
        bot.send_message(m.chat.id, "✅ تم ربط الحساب (2FA)!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")

if __name__ == "__main__":
    bot.infinity_polling()
