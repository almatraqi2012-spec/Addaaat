import telebot, pymongo, threading, time, asyncio, requests, random
from flask import Flask, request, jsonify
from telebot import types
from telethon import TelegramClient, functions, types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import *

# ================= [ ⚙️ الإعدادات ] =================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# السعر الجديد: 1000 عضو = 8 دولار (العضو بـ 0.008)
PRICE_PER_MEMBER = 0.008

# رابط السيرفر الخاص بك لاستقبال تأكيد الدفع (Webhook)
# استبدل هذا الرابط برابط سيرفرك (مثلاً من Render أو VPS)
WEBHOOK_URL = "https://your-server-link.com/webhook/oxapay"

MONGO_URL = "mongodb+srv://USER:PASS@cluster.mongodb.net/dragon"
m_client = pymongo.MongoClient(MONGO_URL)
db = m_client['dragon_bot_db']
users_col = db['users']
accs_col = db['accounts']
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- [ سيرفر Webhook للشحن التلقائي ] ---
@app.route('/webhook/oxapay', methods=['POST'])
def oxapay_callback():
    data = request.json
    if data.get('status') == 'Paid':
        uid = int(data.get('description')) # استخراج آيدي المستخدم من الوصف
        amount = float(data.get('amount'))
        update_balance(uid, amount)
        bot.send_message(uid, f"✅ **تم شحن حسابك تلقائياً بـ {amount}$!**\nشكراً لثقتك بنظام دراجون.")
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_flask).start()

# --- [ دوال القاعدة السحابية ] ---
def is_already_added(user_id):
    return db['added_users'].find_one({"u_id": str(user_id)})

def mark_as_added(user_id):
    db['added_users'].insert_one({"u_id": str(user_id)})

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
    welcome_text = (
        "🐲 **مرحباً بك في بوت دراجون V33 المرعب!**\n\n"
        "🚀 **قوة البوت:** لدينا نظام 'الرادار العميق' الذي يجر لك المتفاعلين قسراً من أي جروب تريده (حتى لو كان محمياً).\n\n"
        "💸 **الأسعار:** نظامنا هو الأرخص!\n"
        "🔹 1000 عضو متفاعل = **8$ فقط**\n"
        "🔹 الدفع آلي والشحن فوري بدون تدخل بشري.\n\n"
        "⚠️ أضف حسابات لجيشك وابدأ الهجوم الآن!"
    )
    bot.send_message(m.chat.id, welcome_text, reply_markup=get_main_markup(), parse_mode="Markdown")

# --- [ محرك النقل والخصم التلقائي ] ---
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
        cost = count * PRICE_PER_MEMBER
        balance = get_balance(m.chat.id)
        if balance < cost:
            return bot.send_message(m.chat.id, f"❌ رصيدك غير كافي! تحتاج لـ {round(cost, 2)}$")

        accs = list(accs_col.find({"user_id": m.chat.id}))
        if not accs:
            return bot.send_message(m.chat.id, "❌ أضف حسابات لجيشك أولاً.")

        sessions = [a['session_string'] for a in accs]
        bot.send_message(m.chat.id, f"⚔️ **بدأ هجوم دراجون... جاري سحب المتفاعلين وفلترة البوتات!**")
        threading.Thread(target=lambda: asyncio.run(run_dragon_v33(sessions, src, trg, count, m.chat.id))).start()
    except:
        bot.send_message(m.chat.id, "⚠️ أدخل رقم صحيح.")

async def run_dragon_v33(sessions, src, trg, total, uid):
    found_targets = []
    hunter_session = random.choice(sessions)
    cl_hunter = TelegramClient(StringSession(hunter_session), MY_API_ID, MY_API_HASH)

    try:
        await cl_hunter.connect()
        try: await cl_hunter(JoinChannelRequest(src))
        except: pass

        # الرادار العميق: سحب المتفاعلين من 5000 رسالة
        async for msg in cl_hunter.iter_messages(src, limit=5000):
            if len(found_targets) >= total: break
            if msg.sender_id and not is_already_added(msg.sender_id):
                sender = await msg.get_sender()
                if isinstance(sender, tl_types.User) and not sender.bot and not sender.deleted:
                    if sender.id not in [u.id for u in found_targets]:
                        found_targets.append(sender)
        await cl_hunter.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ خطأ في الرادار: {e}")

    if not found_targets:
        return bot.send_message(uid, "❌ لم نجد متفاعلين (المجموعة خاملة جداً).")

    success = 0
    bot.send_message(uid, f"🚀 تم صيد `{len(found_targets)}` هدف. جاري الجر القسري والخصم التلقائي...")

    for i, target in enumerate(found_targets):
        if success >= total: break
        s_str = sessions[i % len(sessions)]
        cl = TelegramClient(StringSession(s_str), MY_API_ID, MY_API_HASH)

        try:
            await cl.connect()
            try: await cl(JoinChannelRequest(trg))
            except: pass

            await cl(InviteToChannelRequest(channel=trg, users=[target]))

            # خصم تلقائي عند النجاح
            success += 1
            mark_as_added(target.id)
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}] جر: `@{target.username or target.id}`")

            await cl.disconnect()
            await asyncio.sleep(random.randint(40, 80)) # فاصل حماية

        except (UserPrivacyRestrictedError, UserAlreadyParticipantError):
            mark_as_added(target.id)
            continue
        except Exception:
            continue

    bot.send_message(uid, f"🏁 **انتهت العملية!**\n✅ المضاف: `{success}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$`")

# --- [ الشحن التلقائي OxaPay ] ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي فوري", callback_data="pay_auto"))
    bot.send_message(m.chat.id, "💳 نظام الشحن لدينا تلقائي 100% عبر OxaPay:", reply_markup=mk)

def create_invoice(m):
    try:
        amt = float(m.text)
        payload = {
            'merchant': OXAPAY_KEY,
            'amount': amt,
            'currency': 'USD',
            'description': str(m.chat.id), # نرسل الآيدي ليعود لنا في الويب هوك
            'callbackUrl': WEBHOOK_URL
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بـ {amt}$:\n(بمجرد الدفع سيضاف الرصيد تلقائياً)", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ خطأ في معالجة الطلب.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "pay_auto":
        msg = bot.send_message(call.message.chat.id, "💰 أدخل المبلغ الذي تريد شحنه ($):")
        bot.register_next_step_handler(msg, create_invoice)
    # باقي الـ Callbacks للحذف وغيرها...

# [إضافة بقية الدوال: step_phone, step_otp, step_2fa, del_acc من الكود السابق]

if __name__ == "__main__":
    bot.infinity_polling()
