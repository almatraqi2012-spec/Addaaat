# =============================================================
# 🐲 دراجون المطور V73 - نسخة الإمبراطور راوف (الأرشفة السحابية) 🇾🇪
# نظام سهم الجبار الكامل - تحدي أي قروب في السحب والإضافة
# الإصدار المعتمد لبيئة Render - أمان كامل للرصيد والبيانات
# ============================================================

import telebot, threading, time, asyncio, requests, random, os
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from flask import Flask, request
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

# --- [ 🔐 الربط السحابي الحقيقي Supabase ] ---
SUPABASE_URL = "https://idfbpnhadhcekzzagmmn.supabase.co"
SUPABASE_KEY = "sb_secret_C3a3Phhj4NxOdx4c-L8G6Q_GPoOoTS5"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

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
    except: pass

def save_account_db(user_id, session_name, phone):
    try:
        supabase.table("accounts").upsert({"session_name": session_name, "user_id": user_id, "phone": phone}).execute()
    except: pass

def save_user_memory(user_id):
    try:
        supabase.table("memory").upsert({"target_id": str(user_id)}).execute()
    except: pass

def get_memory():
    try:
        res = supabase.table("memory").select("target_id").execute()
        return [row['target_id'] for row in res.data]
    except: return []

# ================= [ ⚔️ محرك سهم V73 - القفز الذكي والاختراق ] ================

async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **تفعيل رادار سهم... جاري اختراق المصدر.**")
    for session_file in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER: break
        added_list = get_memory()
        client = TelegramClient(session_file.replace('.session',''), MY_API_ID, MY_API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue

            # محاولة الانضمام للمصدر والهدف
            try: await client(JoinChannelRequest(src))
            except: pass
            try: await client(JoinChannelRequest(trg))
            except: pass

            targets = []
            # ميزة اختراق المجموعات المخفية عبر سحب المتفاعلين من الرسائل
            async for m in client.iter_messages(src, limit=3000):
                if len(targets) >= 100: break
                if m.sender_id and str(m.sender_id) not in added_list:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)

            count = 0
            for t in targets:
                if success >= total or count >= 40 or get_balance(uid) < PRICE_PER_MEMBER: break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1; count += 1
                    if success % 5 == 0:
                        bot.send_message(uid, f"➕ [{session_file}] أضاف: `{t.first_name}`")
                    await asyncio.sleep(random.randint(30, 60))
                except errors.FloodWaitError: break
                except: continue
            await client.disconnect()
        except: continue
    bot.send_message(uid, f"🏁 **اكتملت المهمة!**\n✅ الإضافة: `{success}`\n💰 المتبقي: `{get_balance(uid)}$` ")
# ================= [ 📱 القائمة الرئيسية ] ================

@bot.message_handler(commands=['start'])
def start_main(m):
    uid = m.chat.id
    get_balance(uid)
    params = m.text.split()
    if len(params) > 1 and params[1].isdigit():
        ref_id = int(params[1])
        if ref_id != uid:
            update_balance(ref_id, REFERRAL_GIFT)
            try: bot.send_message(ref_id, f"🎊 **بشارة!** دخل صديق برابطك، حصلت على `{REFERRAL_GIFT}$`.")
            except: pass

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الأضافه", "➕ إضافة حساب")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب", "🎁 رصيد مجاني")
    if uid == ADMIN_ID: mk.add("💎 لوحة المالك")
    bot.send_message(uid, "🐲 **دراجون V73 -  **\nأهلاً بك في بوت دراجون نظام إضافة الاعضاء لأي قروب تريده  .", reply_markup=mk)

# ================= [ 💳 نظام الشحن (تلقائي + يدوي) ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="pay_oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_man"))
    bot.send_message(m.chat.id, f"💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_call(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ بالشحن ($):**")
    bot.register_next_step_handler(msg, process_oxa)

def process_oxa(m):
    try:
        amt = float(m.text)
        payload = {
            'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD',
            'description': str(m.chat.id), 'callbackUrl': f"https://dragon-bot-gblf.onrender.com/oxa_callback"
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, f"✅ فاتورة شحن بقيمة {amt}$:", 
                           reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("دفع الآن 🔗", url=res['payLink'])))
    except: bot.send_message(m.chat.id, "⚠️ رقم غير صحيح.")

@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def man_call(c):
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(c.message.chat.id, f"💳 حول على محفظة USDT TRC20:\n`{MY_WALLET}`\n📸 ثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5_{m.chat.id}"), 
            types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10_{m.chat.id}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارٍ مراجعته من الإدارة..."); user_states[m.chat.id] = None

# ================= [ 📱 نظام إدارة الحسابات ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح (مثال: 967xxx):**")
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
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود الواصل للحساب:**")
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
    if res == "OK":
        bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح!**")
        save_account_db(m.chat.id, sess, ph)
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 **الحساب محمي، أرسل كلمة السر:**")
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
    if loop.run_until_complete(sign_p()) == "OK":
        bot.send_message(m.chat.id, "✅ **تم الربط (2FA)!**")
        save_account_db(m.chat.id, sess, ph)
    else: bot.send_message(m.chat.id, "❌ خطأ في كلمة السر.")

# ================= [ ⚙️ الحذف والإحصائيات ] ================

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب")
def delete_acc_menu(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        num = s.split('_')[-1].replace('.session', '')
        mk.add(types.InlineKeyboardButton(f"❌ حذف: {num}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب المراد حذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def finalize_delete(c):
    fname = c.data.replace("rm_", "")
    if os.path.exists(fname): os.remove(fname)
    supabase.table("accounts").delete().eq("session_name", fname).execute()
    bot.edit_message_text(f"✅ تم حذف الحساب بنجاح.", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats(m):
    army = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"📊 **إحصائياتك:**\n📱 جيشك: `{army}` حساب\n💰 رصيدك: `{get_balance(m.chat.id)}$`")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_info(m):
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n🆔 الآيدي: `{m.chat.id}`\n💰 الرصيد: `{get_balance(m.chat.id)}$`")

@bot.message_handler(func=lambda m: m.text == "🎁 رصيد مجاني")
def ref_link(m):
    bot.send_message(m.chat.id, f"🎁 **رابط الإحالة الخاص بك:**\nhttps://t.me/{bot.get_me().username}?start={m.chat.id}\n(ستربح {REFERRAL_GIFT}$ عن كل شخص يدخل)")

# ================= [ ⚔️ بدء العملية ] ================

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_attack_cmd(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيد غير كافٍ.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ، أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, step_trg, army)

def step_trg(m, army):
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**")
    bot.register_next_step_handler(msg, step_n, army, src)

def step_n(m, army, src):
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, run_final, army, src, trg)

def run_final(m, army, src, trg):
    try:
        num = int(m.text)
        threading.Thread(target=lambda: asyncio.run(run_sahm_v73(army, src, trg, num, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# ================= [ 🌐 خادم الويب Callback ] ================

app_web = Flask(__name__)

@app_web.route('/oxa_callback', methods=['POST'])
def oxa_cb():
    data = request.json
    if data.get('status') == 'confirmed':
        uid = int(data.get('description')); update_balance(uid, float(data.get('amount')))
        try: bot.send_message(uid, "✅ تم الشحن تلقائياً!")
        except: pass
    return "OK", 200

if __name__ == '__main__':
    print("🚀 دراجون V73 ينطلق...")
    # حذف الـ Webhook لضمان عدم وجود تعارض مع الـ Polling
    bot.remove_webhook() 
    
    threading.Thread(target=lambda: app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    
    # استخدام infinity_polling مع خاصية skip_pending لعدم تكرار الأوامر القديمة
    bot.infinity_polling(timeout=60, skip_pending=True)
