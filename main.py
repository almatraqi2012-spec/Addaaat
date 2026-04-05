# =============================================================
# 🐲 دراجون المطور V73 - نسخة الأرشفة الأبدية 🇾🇪
# الحقوق محفوظة للإمبراطور راوف | نظام سهم الجبار
# =============================================================

import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
import http.server
import socketserver
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
import pymongo
# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.007
REFERRAL_GIFT = 0.05

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 💾 إدارة البيانات الاحترافية ] ================

# --- [ 🌐 الربط السحابي بـ MongoDB Atlas ] ---
# الرابط الخاص بك الذي حفظناه (Cluster0)
MONGO_URI = "mongodb+srv://alkreem12:Abn-alkreem12@cluster0.p8iub.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client_db = pymongo.MongoClient(MONGO_URI)
db = client_db['dragon_v73_database']
users_col = db['users']       # بديل جدول users
accounts_col = db['accounts'] # بديل جدول accounts
memory_col = db['memory']     # بديل ملف memory.txt (ذاكرة سهم)

def get_balance(uid):
    user = users_col.find_one({"uid": uid})
    return round(user['balance'], 3) if user else 0.0

def update_balance(uid, amt):
    # تحديث الرصيد (زيادة أو نقصان) بضمان سحابي
    users_col.update_one(
        {"uid": uid},
        {"$inc": {"balance": round(amt, 3)}},
        upsert=True
    )

def save_account_db(user_id, session_name, phone):
    # أرشفة الحسابات المربوطة لضمان عدم ضياع الجيش
    accounts_col.update_one(
        {"session_name": session_name},
        {"$set": {"user_id": user_id, "phone": phone, "date": time.time()}},
        upsert=True
    )

def save_user_memory(user_id):
    # حفظ الأعضاء المضافين لمنع التكرار (بدل memory.txt)
    memory_col.update_one(
        {"target_id": str(user_id)},
        {"$set": {"added": True}},
        upsert=True
    )

def get_memory():
    # استرجاع قائمة المضافين من السحاب
    return [doc['target_id'] for doc in memory_col.find()]


# ================= [ ⚔️ محرك سهم V73 - القفز الذكي ] ================
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
            targets = []
            async for m in client.iter_messages(src, limit=5000):
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
                    bot.send_message(uid, f"➕ [{session_file}] أضاف: `{t.first_name}`")
                    await asyncio.sleep(random.randint(30, 60))
                except errors.FloodWaitError: break 
                except: continue
            await client.disconnect()
        except: continue
    bot.send_message(uid, f"🏁 **اكتملت المهمة!**\n✅ الإضافة: `{success}`\n💰 المتبقي: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة الرئيسية ونظام الإحالة ] ================
@bot.message_handler(commands=['start'])
def start_main(m):
    uid = m.chat.id
    conn = get_db()
    res = conn.execute("SELECT uid FROM users WHERE uid=?", (uid,)).fetchone()
    if res is None:
        params = m.text.split()
        if len(params) > 1 and params[1].isdigit():
            ref_id = int(params[1])
            if ref_id != uid:
                update_balance(ref_id, REFERRAL_GIFT)
                try: bot.send_message(ref_id, f"🎊 **بشارة!** دخل صديق برابطك، حصلت على `{REFERRAL_GIFT}$`.")
                except: pass
        conn.execute("INSERT INTO users (uid, balance) VALUES (?, 0.0)", (uid,))
        conn.commit()
    conn.close()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الأضافه", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب", "🎁 كسب رصيد مجاني")
    if uid == ADMIN_ID: mk.add("💎 لوحة المالك")
    bot.send_message(uid, "🐲 **دراجون المطور V73**\nأهلاً بك في نظام سهم الجبار.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🎁 كسب رصيد مجاني")
def referral_menu(m):
    ref_link = f"https://t.me/{bot.get_me().username}?start={m.chat.id}"
    bot.send_message(m.chat.id, f"🎁 **نظام الإحالات:**\nانشر رابطك واربح رصيد مجاني:\n`{ref_link}`")

# ================= [ 💳 نظام الشحن المطور ] ================
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="pay_oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_man"))
    bot.send_message(m.chat.id, f"💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_call(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ المطلوب بالشحن ($):**")
    bot.register_next_step_handler(msg, process_oxa)

def process_oxa(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, f"✅ فاتورة {amt}$:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("دفع الآن 🔗", url=res['payLink'])))
    except: bot.send_message(m.chat.id, "⚠️ رقم غير صحيح.")

@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def man_call(c):
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(c.message.chat.id, f"💳 المحفظة:\n`{MY_WALLET}`\n📸 أرسل صورة الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5_{m.chat.id}"), types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10_{m.chat.id}"), types.InlineKeyboardButton("✅ 50$", callback_data=f"set_50_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارٍ مراجعته..."); user_states[m.chat.id] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    _, amt, uid = c.data.split('_'); update_balance(int(uid), float(amt))
    bot.send_message(int(uid), f"🎉 تم شحن {amt}$!"); bot.edit_message_caption("✅ تم التأكيد", c.message.chat.id, c.message.message_id)

# ================= [ 📱 نظام ربط الحسابات ] ================
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    ph = m.text.strip().replace('+', '').replace(' ', '')
    if not ph.isdigit(): return bot.send_message(m.chat.id, "⚠️ أرقام فقط.")
    sess = f"sess_{m.chat.id}_{ph}"; loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def get_c():
        await cl.connect()
        try: res = await cl.send_code_request(ph); return res.phone_code_hash, "OK"
        except Exception as e: return str(e), "ERR"
        finally: await cl.disconnect()
    try:
        h, status = loop.run_until_complete(get_c())
        if status == "OK":
            msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
            bot.register_next_step_handler(msg, process_code, ph, h, sess)
        else: bot.send_message(m.chat.id, f"❌ {h}")
    except Exception as e: bot.send_message(m.chat.id, f"⚠️ عطل: {str(e)}")
    finally: loop.close()

def process_code(m, ph, h, sess):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(ph, m.text, phone_code_hash=h); return "OK"
        except errors.SessionPasswordNeededError: return "2FA"
        except Exception as e: return str(e)
        finally: await cl.disconnect()
    try:
        res = loop.run_until_complete(sign())
        if res == "OK": 
            bot.send_message(m.chat.id, "✅ **تم الربط بنجاح!**")
            save_account_db(m.chat.id, sess, ph)
        elif res == "2FA":
            msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة السر:**"); bot.register_next_step_handler(msg, process_password, sess, ph)
        else: bot.send_message(m.chat.id, f"❌ {res}")
    finally: loop.close()

def process_password(m, sess, ph):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign_p():
        await cl.connect()
        try: await cl.sign_in(password=m.text); return "OK"
        except Exception as e: return str(e)
        finally: await cl.disconnect()
    try:
        if loop.run_until_complete(sign_p()) == "OK": 
            bot.send_message(m.chat.id, "✅ **تم الربط!**")
            save_account_db(m.chat.id, sess, ph)
        else: bot.send_message(m.chat.id, "❌ خطأ في كلمة السر.")
    finally: loop.close()

# ================= [ ⚙️ الحذف والإحصائيات ] ================
@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats_all(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    bot.send_message(m.chat.id, f"📊 **إحصائياتك:**\n📱 الجيش: `{len(army)}`\n💰 الرصيد: `{get_balance(m.chat.id)}$` ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب")
def delete_acc_menu(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army: 
        num = s.split('_')[-1].replace('.session', '')
        mk.add(types.InlineKeyboardButton(f"❌ حذف: {num}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def finalize_delete(c):
    fname = c.data.replace("rm_", "")
    try:
        if os.path.exists(fname): os.remove(fname)
        if os.path.exists(fname + "-journal"): os.remove(fname + "-journal")
        # حذف من قاعدة البيانات أيضاً
        conn = get_db()
        conn.execute("DELETE FROM accounts WHERE session_name=?", (fname,))
        conn.commit(); conn.close()
        bot.answer_callback_query(c.id, "✅ تم الحذف")
        bot.edit_message_text(f"✅ تم حذف الحساب `{fname.split('_')[-1]}`.", c.message.chat.id, c.message.message_id)
    except Exception as e: bot.answer_callback_query(c.id, f"❌ خطأ: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_attack_cmd(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيد منخفض.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**"), lambda n: threading.Thread(target=lambda: asyncio.run(run_sahm_v73(army, s.text, t.text, int(n.text), m.chat.id))).start())))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    a = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n📱 الجيش: `{a}`")

def run_dummy_server():
    PORT = 7860
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

if __name__ == '__main__':
    print("🚀 دراجون V73 ينطلق في بيئة دوكر...")
    threading.Thread(target=run_dummy_server, daemon=True).start()
    bot.infinity_polling()
