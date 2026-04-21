import telebot, threading, time, asyncio, requests, random, os
from telebot import types
from flask import Flask, request
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from supabase import create_client, Client

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.007
REFERRAL_GIFT = 0.05

# --- [ 🔐 الربط السحابي Supabase ] ---
SUPABASE_URL = "https://idfbpnhadhcekzzagmmn.supabase.co"
SUPABASE_KEY = "sb_secret_C3a3Phhj4NxOdx4c-L8G6Q_GPoOoTS5"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}
app = Flask(__name__)

# ================= [ 🌐 إصلاحات السيرفر والويب ] ================

@app.route('/')
def home(): return "Dragon V73 is Online!", 200

@app.route('/oxa_callback', methods=['POST'])
def oxa_cb():
    data = request.json
    if data.get('status') == 'confirmed':
        uid = int(data.get('description'))
        amt = float(data.get('amount'))
        update_balance(uid, amt)
        try: bot.send_message(uid, f"✅ **تم الشحن التلقائي:** دخل حسابك `{amt}$` بنجاح!")
        except: pass
    return "OK", 200

# ================= [ 💾 إدارة البيانات السحابية ] ================

def get_balance(uid):
    try:
        res = supabase.table("users").select("balance").eq("uid", uid).execute()
        if not res.data:
            supabase.table("users").insert({"uid": uid, "balance": 0.0}).execute()
            return 0.0
        return round(float(res.data[0]['balance']), 3)
    except: return 0.0

def update_balance(uid, amt):
    try:
        curr = get_balance(uid)
        new_bal = round(curr + amt, 3)
        supabase.table("users").upsert({"uid": uid, "balance": new_bal}).execute()
        return True
    except: return False

def save_user_memory(target_id):
    try: supabase.table("memory").upsert({"target_id": str(target_id)}).execute()
    except: pass

def get_memory():
    try:
        res = supabase.table("memory").select("target_id").execute()
        return [row['target_id'] for row in res.data]
    except: return []

# ================= [ ⚔️ محرك سهم V73 - الاكتساح الذكي ] ================

async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **تفعيل رادار سهم... جاري كشف المخفي والمتفاعل.**")
    
    for session_file in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER: break
        added_list = get_memory()
        s_name = session_file.replace('.session','')
        client = TelegramClient(s_name, MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            if not await client.is_user_authorized():
                bot.send_message(uid, f"❌ الحساب `{s_name}` غير مسجل.")
                continue

            try: await client(JoinChannelRequest(src))
            except: pass
            try: await client(JoinChannelRequest(trg))
            except: pass

            targets = []
            async for m in client.iter_messages(src, limit=4000):
                if len(targets) >= 150: break
                if m.sender_id and str(m.sender_id) not in added_list:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)

            count = 0
            for t in targets:
                if success >= total or count >= 45 or get_balance(uid) < PRICE_PER_MEMBER: break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1; count += 1
                    bot.send_message(uid, f"✅ الحساب `{s_name}`\n➕ أضاف: [{t.first_name}](tg://user?id={t.id})")
                    await asyncio.sleep(random.randint(35, 55))
                except errors.FloodWaitError as e:
                    bot.send_message(uid, f"⚠️ الحساب `{s_name}` مقيد لـ {e.seconds} ثانية.")
                    break
                except: continue
            await client.disconnect()
        except: continue
    bot.send_message(uid, f"🏁 **تمت المهمة!**\n✅ الإضافة: `{success}`\n💰 الرصيد: `{get_balance(uid)}$` ")

# ================= [ 📱 القوائم والأوامر ] ================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.chat.id
    get_balance(uid) # لضمان تسجيله في السحاب
    params = m.text.split()
    if len(params) > 1 and params[1].isdigit():
        ref_id = int(params[1])
        if ref_id != uid:
            update_balance(ref_id, REFERRAL_GIFT)
            try: bot.send_message(ref_id, f"🎊 **هدية!** حصلت على `{REFERRAL_GIFT}$` من إحالة.")
            except: pass

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الأضافه", "➕ إضافة حساب")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب", "🎁 رصيد مجاني")
    if uid == ADMIN_ID: mk.add("💎 لوحة المالك")
    bot.send_message(uid, "🐲 **دراجون V73** جاهز للاكتساح السحابي.", reply_markup=mk)

# --- [ قسم شحن الرصيد ] ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="pay_oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_man"))
    bot.send_message(m.chat.id, f"💰 رصيدك: `{get_balance(m.chat.id)}$`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_start(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل مبلغ الشحن بالدولار:**")
    bot.register_next_step_handler(msg, oxa_process)

def oxa_process(m):
    try:
        amt = float(m.text)
        payload = {
            'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD',
            'description': str(m.chat.id), 'callbackUrl': f"https://{request.host}/oxa_callback"
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, f"✅ رابط الدفع لـ {amt}$:", 
                           reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("اضغط هنا للدفع 🔗", url=res['payLink'])))
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def manual_pay(c):
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(c.message.chat.id, f"💳 المحفظة:\n`{MY_WALLET}`\n📸 أرسل صورة الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5_{m.chat.id}"), 
            types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارٍ المراجعة..."); user_states[m.chat.id] = None

# --- [ لوحة المالك ] ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    _, amt, target_uid = c.data.split('_')
    if update_balance(int(target_uid), float(amt)):
        bot.send_message(int(target_uid), f"🎊 تم شحن `{amt}$` في حسابك!")
        bot.edit_message_caption(f"✅ تم الشحن لـ {target_uid}", c.message.chat.id, c.message.message_id)

# --- [ إدارة الحسابات ] ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل الرقم مع المفتاح:")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    ph = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{ph}"
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def connect():
        await cl.connect()
        try: h = await cl.send_code_request(ph); return h.phone_code_hash, "OK"
        except Exception as e: return str(e), "ERR"
        finally: await cl.disconnect()
    res, status = loop.run_until_complete(connect())
    if status == "OK":
        msg = bot.send_message(m.chat.id, "📩 أرسل الكود:")
        bot.register_next_step_handler(msg, process_code, ph, res, sess)
    else: bot.send_message(m.chat.id, f"❌ {res}")

def process_code(m, ph, h, sess):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(ph, m.text, phone_code_hash=h); return "OK"
        except errors.SessionPasswordNeededError: return "2FA"
        except Exception as e: return str(e)
        finally: await cl.disconnect()
    res = loop.run_until_complete(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم الربط!")
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 أرسل كلمة السر:")
        bot.register_next_step_handler(msg, process_2fa, sess, ph)
    else: bot.send_message(m.chat.id, f"❌ {res}")

def process_2fa(m, sess, ph):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign_p():
        await cl.connect()
        try: await cl.sign_in(password=m.text); return "OK"
        except: return "ERR"
        finally: await cl.disconnect()
    if loop.run_until_complete(sign_p()) == "OK": bot.send_message(m.chat.id, "✅ تم الربط!")
    else: bot.send_message(m.chat.id, "❌ خطأ.")

# --- [ بدء الإضافة ] ---
@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_add_flow(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    msg = bot.send_message(m.chat.id, "📡 يوزر المصدر:")
    bot.register_next_step_handler(msg, get_trg, army)

def get_trg(m, army):
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 يوزر مجموعتك:")
    bot.register_next_step_handler(msg, get_num, army, src)

def get_num(m, army, src):
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 العدد:")
    bot.register_next_step_handler(msg, final_run, army, src, trg)

def final_run(m, army, src, trg):
    try:
        num = int(m.text)
        threading.Thread(target=lambda: asyncio.run(run_sahm_v73(army, src, trg, num, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ رقم فقط.")

# ================= [ 🚀 التشغيل النهائي ] ================

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    bot.remove_webhook()
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ نظام دراجون V73 الشامل يعمل الآن...")
    bot.infinity_polling(timeout=60, skip_pending=True)
