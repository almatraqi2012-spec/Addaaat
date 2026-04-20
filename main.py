# =============================================================
# 🐲 دراجون المطور V73 - نسخة "إمبراطور السحاب" 🇾🇪
# الحقوق محفوظة للإمبراطور راوف | نظام سهم الجبار 2026
# المحرك الأصلي الكامل + نظام الإحالات + إصلاح الشحن السحابي
# =============================================================

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
MY_BOT_URL = "https://dragon-bot-gblf.onrender.com"

# --- [ 🔐 ربط الخزنة السحابية Supabase ] ---
SUPABASE_URL = "https://idfbpnhadhcekzzagmmn.supabase.co"
SUPABASE_KEY = "sb_secret_C3a3Phhj4NxOdx4c-L8G6Q_GPoOoTS5"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 💾 إدارة البيانات السحابية - إصلاح الشحن ] ================

def get_balance(uid):
    try:
        res = supabase.table("users").select("balance").eq("uid", uid).execute()
        if not res.data:
            supabase.table("users").insert({"uid": uid, "balance": 0.0}).execute()
            return 0.0
        return round(float(res.data[0]['balance']), 3)
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0.0

def update_balance(uid, amt):
    try:
        curr = get_balance(uid)
        new_bal = round(curr + amt, 3)
        # استخدام upsert لضمان التحديث حتى لو لم يكن المستخدم مسجلاً
        res = supabase.table("users").upsert({"uid": uid, "balance": new_bal}).execute()
        return True if res.data else False
    except Exception as e:
        print(f"Error updating balance: {e}")
        return False

def save_user_memory(tid):
    try: supabase.table("memory").upsert({"target_id": str(tid)}).execute()
    except: pass

def get_memory():
    try:
        res = supabase.table("memory").select("target_id").execute()
        return [row['target_id'] for row in res.data]
    except: return []

# ================= [ ⚔️ محرك سهم الجبار (النسخة المتوحشة) ] ================

async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **انطلاق إعصار دراجون... جاري جرد المتفاعلين.**")
    for sess in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER: break
        added_globally = get_memory()
        client = TelegramClient(sess.replace('.session',''), MY_API_ID, MY_API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue
            try: await client(JoinChannelRequest(src))
            except: pass
            try: await client(JoinChannelRequest(trg))
            except: pass
            targets = []
            async for m in client.iter_messages(src, limit=5000):
                if len(targets) >= 100: break
                if m.sender_id and str(m.sender_id) not in added_globally:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)
            acc_added = 0
            for t in targets:
                if success >= total or acc_added >= 45 or get_balance(uid) < PRICE_PER_MEMBER: break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1; acc_added += 1
                    if success % 5 == 0: bot.send_message(uid, f"✅ تم إضافة `{success}` عضو..")
                    await asyncio.sleep(random.randint(30, 60))
                except errors.FloodWaitError: break
                except: continue
            await client.disconnect()
        except: continue
    bot.send_message(uid, f"🏁 **تمت المهمة!**\n✅ الإضافة: `{success}`\n💰 الرصيد: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة ونظام الإحالة ] ================

@bot.message_handler(commands=['start'])
def start_main(m):
    uid = m.chat.id
    get_balance(uid)
    if uid != ADMIN_ID: bot.send_message(ADMIN_ID, f"👤 **دخول جديد:** `{uid}`")
    
    p = m.text.split()
    if len(p) > 1 and p[1].isdigit():
        rid = int(p[1])
        if rid != uid:
            update_balance(rid, REFERRAL_GIFT)
            try: bot.send_message(rid, f"🎁 حصلت على `{REFERRAL_GIFT}$` هدية إحالة!")
            except: pass

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الأضافه", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب", "🎁 كسب رصيد مجاني")
    if uid == ADMIN_ID: mk.add("💎 لوحة المالك")
    bot.send_message(uid, "🐲 **دراجون V73 - سهم الجبار**\nنظام التحدي السحابي.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🎁 كسب رصيد مجاني")
def referral_menu(m):
    link = f"https://t.me/{bot.get_me().username}?start={m.chat.id}"
    bot.send_message(m.chat.id, f"🎁 **نظام الإحالات:**\n\nاربح `{REFERRAL_GIFT}$` عن كل صديق يدخل البوت عبر رابطك:\n`{link}`")

# ================= [ 💰 نظام الشحن المطور ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_m(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="p_oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="p_man"))
    bot.send_message(m.chat.id, f"💰 رصيدك: `{get_balance(m.chat.id)}$`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "p_oxa")
def oxa_c(c):
    msg = bot.send_message(c.message.chat.id, "💵 **المبلغ ($):**")
    bot.register_next_step_handler(msg, oxa_go)

def oxa_go(m):
    try:
        a = float(m.text)
        d = {'merchant': OXAPAY_KEY,'amount': a,'currency': 'USD','description': str(m.chat.id),'callbackUrl': f"{MY_BOT_URL}/oxa_callback"}
        r = requests.post("https://api.oxapay.com/merchants/request", json=d).json()
        if r.get('payLink'):
            bot.send_message(m.chat.id, f"✅ فاتورة {a}$:", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("دفع الآن 🔗", url=r['payLink'])))
    except: bot.send_message(m.chat.id, "⚠️ خطأ.")

@bot.callback_query_handler(func=lambda c: c.data == "p_man")
def man_c(c):
    user_states[c.message.chat.id] = "wait_img"
    bot.send_message(c.message.chat.id, f"💳 حول لـ USDT TRC20:\n`{MY_WALLET}`\nأرسل الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_p(m):
    if user_states.get(m.chat.id) == "wait_img":
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5.0_{m.chat.id}"),
               types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10.0_{m.chat.id}"),
               types.InlineKeyboardButton("✅ 50$", callback_data=f"set_50.0_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارٍ المراجعة..."); user_states[m.chat.id] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_c(c):
    try:
        parts = c.data.split('_')
        amt = float(parts[1])
        uid = int(parts[2])
        if update_balance(uid, amt):
            bot.send_message(uid, f"🎊 تم شحن `{amt}$` بنجاح!")
            bot.edit_message_caption(f"✅ تم الشحن للمستخدم {uid}", c.message.chat.id, c.message.message_id)
        else: bot.answer_callback_query(c.id, "❌ خطأ سحابي")
    except Exception as e: bot.answer_callback_query(c.id, f"⚠️ {e}")

# ================= [ 📱 إدارة الجيش ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_s(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, ph_step)

def ph_step(m):
    p = m.text.replace('+','').replace(' ','')
    s = f"sess_{m.chat.id}_{p}"
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(s, MY_API_ID, MY_API_HASH, loop=loop)
    async def go():
        await cl.connect()
        try: r = await cl.send_code_request(p); return r.phone_code_hash, "OK"
        except Exception as e: return str(e), "ER"
        finally: await cl.disconnect()
    h, st = loop.run_until_complete(go())
    if st == "OK":
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
        bot.register_next_step_handler(msg, cd_step, p, h, s)
    else: bot.send_message(m.chat.id, f"❌ {h}")

def cd_step(m, p, h, s):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(s, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(p, m.text, phone_code_hash=h); return "OK"
        except errors.SessionPasswordNeededError: return "2FA"
        except Exception as e: return str(e)
        finally: await cl.disconnect()
    res = loop.run_until_complete(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم الربط!")
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 **أرسل التحقق (2FA):**")
        bot.register_next_step_handler(msg, pw_step, s, p)
    else: bot.send_message(m.chat.id, f"❌ {res}")

def pw_step(m, s, p):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(s, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign_p():
        await cl.connect()
        try: await cl.sign_in(password=m.text); return "OK"
        except: return "ER"
        finally: await cl.disconnect()
    if loop.run_until_complete(sign_p()) == "OK": bot.send_message(m.chat.id, "✅ تم الربط!")
    else: bot.send_message(m.chat.id, "❌ خطأ.")

# ================= [ ⚙️ الإحصائيات والحذف ] ================

@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def st_all(m):
    a = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    bot.send_message(m.chat.id, f"📊 **إحصائياتك:**\n📱 الجيش: `{len(a)}`\n💰 الرصيد: `{get_balance(m.chat.id)}$` ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب")
def del_m(m):
    a = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not a: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in a: mk.add(types.InlineKeyboardButton(f"❌ {s.split('_')[-1]}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def rm_c(c):
    f = c.data.replace("rm_", "")
    if os.path.exists(f): os.remove(f)
    bot.edit_message_text(f"✅ تم حذف {f.split('_')[-1]}", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_at(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيد منخفض.")
    a = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not a: return bot.send_message(m.chat.id, "❌ أضف حسابات.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, get_trg, a)

def get_trg(m, a):
    s = m.text; msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**")
    bot.register_next_step_handler(msg, get_n, a, s)

def get_n(m, a, s):
    t = m.text; msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, go_at, a, s, t)

def go_at(m, a, s, t):
    try:
        n = int(m.text)
        threading.Thread(target=lambda: asyncio.run(run_sahm_v73(a, s, t, n, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_inf(m):
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n🆔: `{m.chat.id}`")

# ================= [ 🌐 محرك الويب ] ================

web = Flask(__name__)

@web.route('/oxa_callback', methods=['POST'])
def callback():
    d = request.json
    if d.get('status') in ['confirmed', 'paid']:
        u = int(d.get('description')); am = float(d.get('amount'))
        if update_balance(u, am):
            try:
                bot.send_message(u, f"🎊 تم استلام `{am}$` تلقائياً!")
                bot.send_message(ADMIN_ID, f"💰 شحن آلي: `{am}$` لـ `{u}`")
            except: pass
    return "OK", 200

def run_s():
    p = int(os.environ.get('PORT', 10000))
    web.run(host='0.0.0.0', port=p)

if __name__ == '__main__':
    print("🚀 دراجون V73 ينطلق...")
    threading.Thread(target=run_s, daemon=True).start()
    bot.delete_webhook(drop_pending_updates=True)
    bot.infinity_polling(timeout=60)
