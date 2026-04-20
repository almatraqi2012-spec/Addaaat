# =============================================================
# 🐲 دراجون المطور V73 - نسخة "إمبراطور السحاب" 🇾🇪
# الحقوق محفوظة للإمبراطور راوف | نظام سهم الجبار 2026
# الإصدار النهائي: Supabase + المحرك الأصلي + نظام الإحالات
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
# ملاحظة: استبدل الرابط أدناه برابط تطبيقك الفعلي في Render لاستقبال الدفعات الآلية
MY_BOT_URL = "https://dragon-bot-gblf.onrender.com"

# --- [ 🔐 ربط الخزنة السحابية Supabase ] ---
# تم استخدام المفاتيح الخاصة بمشروعك (almatraqi2012)
SUPABASE_URL = "https://idfbpnhadhcekzzagmmn.supabase.co"
SUPABASE_KEY = "sb_secret_C3a3Phhj4NxOdx4c-L8G6Q_GPoOoTS5"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 💾 إدارة البيانات السحابية الاحترافية ] ================

def get_balance(uid):
    try:
        # البحث عن المستخدم في جدول users
        res = supabase.table("users").select("balance").eq("uid", uid).execute()
        if not res.data:
            # إذا لم يوجد، يتم تسجيله برصيد صفر
            supabase.table("users").insert({"uid": uid, "balance": 0.0}).execute()
            return 0.0
        return round(float(res.data[0]['balance']), 3)
    except Exception as e:
        print(f"Supa Error (Get): {e}")
        return 0.0

def update_balance(uid, amt):
    try:
        curr = get_balance(uid)
        new_bal = round(curr + amt, 3)
        # استخدام upsert لضمان التحديث الفوري حتى لو حدث تعارض
        res = supabase.table("users").upsert({"uid": uid, "balance": new_bal}).execute()
        return True if res.data else False
    except Exception as e:
        print(f"Supa Error (Update): {e}")
        return False

def save_user_memory(tid):
    try:
        # حفظ الأيدي الخاص بالعضو المضاف لمنع تكراره عالمياً
        supabase.table("memory").upsert({"target_id": str(tid)}).execute()
    except: pass

def get_memory():
    try:
        res = supabase.table("memory").select("target_id").execute()
        return [row['target_id'] for row in res.data]
    except: return []

# ================= [ ⚔️ محرك سهم V73 - سحب المتفاعلين والاختراق ] ================

async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **انطلاق إعصار دراجون... جاري اختراق المصدر.**")
    for sess_file in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER: break
        added_globally = get_memory()
        client = TelegramClient(sess_file.replace('.session',''), MY_API_ID, MY_API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue
            
            try: await client(JoinChannelRequest(src))
            except: pass
            try: await client(JoinChannelRequest(trg))
            except: pass

            targets = []
            # ميزة سحب المتفاعلين (سهم الجبار) لاختراق المجموعات المخفية
            async for m in client.iter_messages(src, limit=4000):
                if len(targets) >= 100: break
                if m.sender_id and str(m.sender_id) not in added_globally:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)
            
            acc_count = 0
            for t in targets:
                if success >= total or acc_count >= 45 or get_balance(uid) < PRICE_PER_MEMBER: break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1; acc_count += 1
                    if success % 5 == 0:
                        bot.send_message(uid, f"➕ [{sess_file}] أضاف بنجاح! الإجمالي: `{success}`")
                    await asyncio.sleep(random.randint(35, 65))
                except errors.FloodWaitError: break 
                except: continue
            await client.disconnect()
        except: continue
    bot.send_message(uid, f"🏁 **اكتملت المهمة بنجاح!**\n✅ الأعضاء المضافين: `{success}`\n💰 رصيدك الحالي: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة ونظام الإحالة ] ================

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
    mk.add("⚔️ بدء الأضافه", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب", "🎁 كسب رصيد مجاني")
    if uid == ADMIN_ID: mk.add("💎 لوحة المالك")
    bot.send_message(uid, "🐲 **دراجون المطور V73 **\nأهلاً بك يا إمبراطور في معقل السحاب.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🎁 كسب رصيد مجاني")
def referral_menu(m):
    ref_link = f"https://t.me/{bot.get_me().username}?start={m.chat.id}"
    bot.send_message(m.chat.id, f"🎁 **نظام الإحالات (كسب الرصيد):**\nانشر رابطك واربح `{REFERRAL_GIFT}$` عن كل صديق:\n`{ref_link}`")

# ================= [ 💳 نظام الشحن المطور ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="p_oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="p_man"))
    bot.send_message(m.chat.id, f"💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "p_oxa")
def oxa_call(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, process_oxa)

def process_oxa(m):
    try:
        amt = float(m.text)
        payload = {
            'merchant': OXAPAY_KEY,
            'amount': amt,
            'currency': 'USD',
            'description': str(m.chat.id),
            'callbackUrl': f"{MY_BOT_URL}/oxa_callback"
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            bot.send_message(m.chat.id, f"✅ فاتورة شحن بـ {amt}$:\nسيتم إضافة الرصيد تلقائياً بعد الدفع.", 
                           reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("دفع الآن 🔗", url=res['payLink'])))
    except: bot.send_message(m.chat.id, "⚠️ رقم غير صحيح.")

@bot.callback_query_handler(func=lambda c: c.data == "p_man")
def man_call(c):
    user_states[c.message.chat.id] = "wait_img"
    bot.send_message(c.message.chat.id, f"💳 محفظة USDT TRC20:\n`{MY_WALLET}`\n📸 أرسل صورة الإيصال بعد التحويل.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "wait_img":
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5.0_{m.chat.id}"), 
            types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10.0_{m.chat.id}"), 
            types.InlineKeyboardButton("✅ 50$", callback_data=f"set_50.0_{m.chat.id}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال شحن جديد: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارٍ مراجعة الإيصال من قبل الإدارة..."); user_states[m.chat.id] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    _, amt, uid = c.data.split('_')
    if update_balance(int(uid), float(amt)):
        bot.send_message(int(uid), f"🎊 **بشارة!** تم شحن `{amt}$` بنجاح إلى حسابك."); 
        bot.edit_message_caption(f"✅ تم الشحن بنجاح للمستخدم {uid}", c.message.chat.id, c.message.message_id)
    else:
        bot.answer_callback_query(c.id, "❌ خطأ في السحاب (Supabase)")

# ================= [ 📱 نظام ربط الحسابات ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي (مثال: 967xxx):**")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    ph = m.text.strip().replace('+', '').replace(' ', '')
    sess = f"sess_{m.chat.id}_{ph}"
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def get_c():
        await cl.connect()
        try: res = await cl.send_code_request(ph); return res.phone_code_hash, "OK"
        except Exception as e: return str(e), "ERR"
        finally: await cl.disconnect()
    h, status = loop.run_until_complete(get_c())
    if status == "OK":
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود الواصل للحساب:**")
        bot.register_next_step_handler(msg, process_code, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ {h}")

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
    if res == "OK": bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح!**")
    elif res == "2FA":
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر التحقق بخطوتين:**"); 
        bot.register_next_step_handler(msg, process_password, sess, ph)
    else: bot.send_message(m.chat.id, f"❌ {res}")

def process_password(m, sess, ph):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)
    async def sign_p():
        await cl.connect()
        try: await cl.sign_in(password=m.text); return "OK"
        except Exception as e: return str(e)
        finally: await cl.disconnect()
    if loop.run_until_complete(sign_p()) == "OK": bot.send_message(m.chat.id, "✅ **تم الربط!**")
    else: bot.send_message(m.chat.id, "❌ خطأ في كلمة السر.")

# ================= [ ⚙️ الإحصائيات والحذف ] ================

@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats_all(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    bot.send_message(m.chat.id, f"📊 **إحصائياتك:**\n📱 جيش دراجون: `{len(army)}` حساب\n💰 الرصيد: `{get_balance(m.chat.id)}$` ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب")
def delete_acc_menu(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات مرتبطة.")
    mk = types.InlineKeyboardMarkup()
    for s in army: 
        num = s.split('_')[-1].replace('.session', '')
        mk.add(types.InlineKeyboardButton(f"❌ حذف: {num}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب المراد حذفه من الجيش:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def finalize_delete(c):
    fname = c.data.replace("rm_", "")
    if os.path.exists(fname): os.remove(fname)
    bot.edit_message_text(f"✅ تم حذف الحساب `{fname.split('_')[-1]}` نهائياً.", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_attack_cmd(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيدك منخفض جداً.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ أضف حسابات للجيش أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **أرسل يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, step_target, army)

def step_target(m, army):
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 **أرسل يوزر مجموعتك (بدون @):**")
    bot.register_next_step_handler(msg, step_num, army, src)

def step_num(m, army, src):
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب إضافته:**")
    bot.register_next_step_handler(msg, finalize_attack, army, src, trg)

def finalize_attack(m, army, src, trg):
    try:
        num = int(m.text)
        threading.Thread(target=lambda: asyncio.run(run_sahm_v73(army, src, trg, num, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "❌ يرجى إدخال رقم صحيح.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    bal = get_balance(m.chat.id)
    army_count = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n💰 الرصيد المتوفر: `{bal}$` \n📱 عدد حسابات الجيش: `{army_count}`")

# ================= [ 🌐 خادم الويب واستقبال الدفع ] ================

app_web = Flask(__name__)

@app_web.route('/oxa_callback', methods=['POST'])
def oxa_callback():
    data = request.json
    if data.get('status') in ['confirmed', 'paid']:
        uid = int(data.get('description'))
        amount = float(data.get('amount'))
        if update_balance(uid, amount):
            try:
                bot.send_message(uid, f"🎊 **بشارة!** تم استلام الدفع بنجاح.\n💰 تم إضافة `{amount}$` إلى رصيدك آلياً.")
                bot.send_message(ADMIN_ID, f"💰 **شحن آلي:** المستخدم `{uid}` شحن `{amount}$` عبر Oxapay.")
            except: pass
    return "OK", 200

def run_server():
    PORT = int(os.environ.get('PORT', 10000))
    app_web.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    print("🚀 دراجون V73 السحابي ينطلق...")
    threading.Thread(target=run_server, daemon=True).start()
    bot.infinity_polling(timeout=60)
