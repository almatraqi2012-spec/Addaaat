# ============================================================
# 🐲 دراجون المطور V73 - نسخة الأرشفة الأبدية 🇾🇪
# الحقوق محفوظة للإمبراطور راوف | نظام سهم الجبار
# الإصدار المستقر لبيئة Render - قوة SQLite القصوى
# ============================================================
# --- المكتبات التي لديك بالفعل ---
from flask import Flask, render_template, request
import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# --- ⚠️ المكتبات الناقصة (يجب إضافتها فوراً) ---
from datetime import datetime, timedelta # ضروري لبرمجة "تصاعد الأرصدة" وحساب الوقت
import json # للتعامل مع ملفات الإعدادات والذاكرة (added_list)
from telethon.tl.functions.messages import GetMessagesReactionsRequest, GetHistoryRequest # أساسي لسحب المتفاعلين بالإيموجي في المجموعات المخفية
from telethon.tl.functions.users import GetFullUserRequest # لجلب آيدي العضو في حال كان مخفياً
# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN =os.environ.get('BOT_TOKEN')
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.007
REFERRAL_GIFT = 0.05

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 💾 إدارة البيانات الاحترافية - SQLite ] ================

def get_db():
    conn = sqlite3.connect('dragon_v73.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.execute('CREATE TABLE IF NOT EXISTS accounts (session_name TEXT PRIMARY KEY, user_id INTEGER, phone TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS memory (target_id TEXT PRIMARY KEY)')
    conn.commit()
    return conn

db_conn = get_db()

def get_balance(uid):
    row = db_conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    if not row:
        db_conn.execute("INSERT INTO users (uid, balance) VALUES (?, 0.0)", (uid,))
        db_conn.commit()
        return 0.0
    return round(row[0], 3)

def update_balance(uid, amt):
    db_conn.execute("UPDATE users SET balance = balance + ? WHERE uid = ?", (round(amt, 3), uid))
    db_conn.commit()

def save_account_db(user_id, session_name, phone):
    db_conn.execute("INSERT OR REPLACE INTO accounts (session_name, user_id, phone) VALUES (?, ?, ?)",
                   (session_name, user_id, phone))
    db_conn.commit()

def save_user_memory(user_id):
    try:
        db_conn.execute("INSERT INTO memory (target_id) VALUES (?)", (str(user_id),))
        db_conn.commit()
    except: pass

def get_memory():
    return [row[0] for row in db_conn.execute("SELECT target_id FROM memory").fetchall()]

# ================= [ ⚔️ محرك سهم V73 - القفز التلقائي ] ================
async def run_dragon_force_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🐲 **رادار الدراجون مفعّل.. جاري اختراق القيود وسحب المتفاعلين.**")

    # تقسيم العدد المطلوب على عدد الحسابات المتوفرة
    per_account = 35
    for session_file in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER: break

        session_name = session_file.replace('.session','')
        client = TelegramClient(session_name, MY_API_ID, MY_API_HASH)

        try:
            await client.connect()
            if not await client.is_user_authorized():
                bot.send_message(uid, f"⚠️ الحساب `{session_name}` منتهي الجلسة.. قفز.")
                continue

            # فحص التقييد (SpamBlock)
            try:
                await client(functions.messages.SendMessageRequest(peer='@SpamBot', message='/start'))
            except errors.UserBannedInChannelError:
                bot.send_message(uid, f"🚫 الحساب `{session_name}` مقيد.. القفز للتالي.")
                continue

            added_list = get_memory() # قائمة المخزنين سابقاً لمنع التكرار
            targets = []

            # --- خوارزمية السحب العميق (حتى للمخفي والقنوات) ---
            # 1. سحب المتفاعلين بالايموجي (للأعضاء المتفاعلين فقط)
# 1. سحب المتفاعلين (تأكد من ترتيب المسافات كالتالي)
            async for msg in client.iter_messages(src, limit=1000):
                if msg.reactions:
                    # هذا السطر يجب أن يكون مزاحاً لليمين بـ 4 مسافات عن الـ if
                    async for user in client.iter_participants(src, filter=tl_types.ChannelParticipantsRecent()):
                        if user.id not in [x.id for x in targets] and str(user.id) not in added_list:
                            targets.append(user)
                        if len(targets) >= 100:
                            break
                if len(targets) >= 100:
                    break
            # 2. سحب المتحدثين في الدردشة (للمجموعات المخفية)
            if len(targets) < 50:
                async for m in client.iter_messages(src, limit=5000):
                    u = await m.get_sender()
                    if isinstance(u, types.User) and not u.bot:
                        if u.id not in [x.id for x in targets] and str(u.id) not in added_list:
                            targets.append(u)

            # --- عملية الإضافة القتالية ---
            acc_added = 0
            for t in targets:
                if success >= total or acc_added >= per_account or get_balance(uid) < PRICE_PER_MEMBER:
                    break

                try:
                    # محاولة الإضافة المباشرة
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1
                    acc_added += 1

                    if success % 10 == 0:
                        bot.send_message(uid, f"🔥 تم إضافة `{success}` أعضاء حتى الآن..")

                    # وقت انتظار عشوائي ذكي لتجنب الحظر
                    await asyncio.sleep(random.randint(20, 35))

                except errors.PeerFloodError:
                    bot.send_message(uid, f"� حساب `{session_name}` تعب (Flood).. القفز للتالي.")
                    break # القفز للحساب التالي
                except errors.UserPrivacyRestrictedError:
                    continue # العضو مغلق الخصوصية، انتقل للذي يليه
                except Exception as e:
                    continue

            await client.disconnect()

        except Exception as e:
            bot.send_message(uid, f"❌ خطأ في الحساب `{session_name}`: {str(e)}")
            continue

    bot.send_message(uid, f"🏁 **اكتملت مهمة الدراجون!**\n✅ إجمالي الإضافة: `{success}`\n💰 المتبقي في محفظتك: `{get_balance(uid)}$` ")
# ================= [ 📱 الواجهة الرئيسية ونظام الإحالة ] ================

@bot.message_handler(commands=['start'])
def start_main(m):
    uid = m.chat.id
    get_balance(uid) # تسجيل المستخدم
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
    bot.send_message(uid, "🐲 **دراجون المطور **\nأهلاً بك في بوت قاهر القيود، رادار الاختراق العميق.. سيطرتك تبدأ الآن .", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🎁 كسب رصيد مجاني")
def referral_menu(m):
    ref_link = f"https://t.me/{bot.get_me().username}?start={m.chat.id}"
    bot.send_message(m.chat.id, f"🎁 **نظام الإحالات:**\nانشر رابطك واربح رصيد مجاني:\n`{ref_link}`")

# ================= [ 💳 نظام الشحن المطور ] ================

# ================= [ 💳 نظام الشحن المطور (تلقائي + يدوي) ] ================

# 1. القائمة الرئيسية للشحن
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="pay_oxa"),
        types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="pay_man")
    )
    bot.send_message(m.chat.id, f"💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=mk)

# ---------------- [ قسم الشحن الآلي Oxapay ] ----------------

@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_call(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ المطلوب بالشحن ($):**")
    bot.register_next_step_handler(msg, process_oxa)

def process_oxa(m):
    if not m.text: return
    try:
        amt = float(m.text.strip())
        payload = {
            'merchant': OXAPAY_KEY,
            'amount': amt,
            'currency': 'USD',
            'description': str(m.chat.id),
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()

        track_id = res.get('trackId')
        pay_url = res.get('payLink')

        if pay_url:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 اضغط هنا للدفع الآن", url=pay_url))
            bot.send_message(m.chat.id,
                           f"✅ فاتورة {amt}$ (دفع تلقائي):\n🔗 سيتم شحن رصيدك فور الدفع.",
                           reply_markup=markup)

            # تشغيل الفحص الآلي في الخلفية
            threading.Thread(target=auto_check_payment, args=(m.chat.id, track_id, amt)).start()
        else:
            bot.send_message(m.chat.id, "❌ عذراً، فشل في توليد رابط الدفع.")
    except:
        bot.send_message(m.chat.id, "⚠️ يرجى إرسال المبلغ بالأرقام فقط.")

def auto_check_payment(chat_id, track_id, amount):
    # فحص كل دقيقة لمدة 60 دقيقة
    for _ in range(60):
        time.sleep(60)
        try:
            check = requests.post("https://api.oxapay.com/merchants/inquiry", json={
                'merchant': OXAPAY_KEY,
                'trackId': track_id
            }).json()
            if check.get('status') == 'Paid' or check.get('result') == '100':
                update_balance(chat_id, amount)
                bot.send_message(chat_id, f"🎊 **بشارة!** تم استلام الدفع تلقائياً.\n💰 تم إضافة `{amount}$` إلى رصيدك بنجاح.")
                break
        except: continue

# ---------------- [ قسم الشحن اليدوي (الإيصالات) ] ----------------

# هذا الجزء هو الذي كان يحتاج لتركيز (ربط الزر بالدالة)
@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def man_call(c):
    # تفعيل حالة الانتظار ضروري لكي يفهم البوت أن الصورة القادمة هي إيصال
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(c.message.chat.id, f"🏦 **الشحن اليدوي:**\n\nالمحفظة USDT TRC20:\n`{MY_WALLET}`\n\n📸 أرسل صورة الإيصال هنا بعد التحويل.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    # التحقق من أن المستخدم ضغط على زر الشحن اليدوي
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 50$", callback_data=f"set_50_{m.chat.id}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id,
                      caption=f"📩 إيصال شحن جديد\n👤 الشخص: `{m.chat.id}`",
                      reply_markup=mk)
        bot.reply_to(m, "⏳ تم استلام الإيصال، جارٍ المراجعة من قبل الإدارة...")
        # تصفير الحالة لكي لا يتداخل مع صور أخرى
        user_states[m.chat.id] = None

# تأكيد الشحن من قبل الآدمن
@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    try:
        _, amt, uid = c.data.split('_')
        update_balance(int(uid), float(amt))
        bot.send_message(int(uid), f"🎉 **بشارة!** تم شحن حسابك بـ {amt}$ بنجاح.")
        bot.edit_message_caption(f"✅ تم الشحن بنجاح ({amt}$)", c.message.chat.id, c.message.message_id)
    except Exception as e:
        bot.answer_callback_query(c.id, "❌ خطأ في العملية")
# ================= [ 📱 نظام ربط الحسابات ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc_start(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    ph = m.text.strip().replace('+', '').replace(' ', '')
    if not ph.isdigit(): return bot.send_message(m.chat.id, "⚠️ أرقام فقط.")
    sess = f"sess_{m.chat.id}_{ph}"
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
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
            msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة السر:**");
            bot.register_next_step_handler(msg, process_password, sess, ph)
        else: bot.send_message(m.chat.id, f"❌ {res}")
    finally: loop.close()

def process_password(m, sess, ph):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)          async def sign_p():
        await cl.connect()
        try: await cl.sign_in(password=m.text); return "OK"                   except Exception as e: return str(e)
        finally: await cl.disconnect()                                    try:
        if loop.run_until_complete(sign_p()) == "OK":
            bot.send_message(m.chat.id, "✅ **تم الربط!**")
            save_account_db(m.chat.id, sess, ph)                              else: bot.send_message(m.chat.id, "❌ خطأ في كلمة السر.")
    finally: loop.close()
                                                                      # ================= [ ⚙️ الحذف والإحصائيات ] ================          
@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")        def stats_all(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    bot.send_message(m.chat.id, f"📊 **إحصائياتك:**\n📱 الجيش: `{len(army)}`\n💰 الرصيد: `{get_balance(m.chat.id)}$` ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب")
def delete_acc_menu(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        num = s.split('_')[-1].replace('.session', '')                        mk.add(types.InlineKeyboardButton(f"❌ حذف: {num}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))  def finalize_delete(c):
    fname = c.data.replace("rm_", "")                                     try:
        if os.path.exists(fname): os.remove(fname)                            db_conn.execute("DELETE FROM accounts WHERE session_name=?", (fname,))
        db_conn.commit()
        bot.answer_callback_query(c.id, "✅ تم الحذف")
        bot.edit_message_text(f"✅ تم حذف الحساب `{fname.split('_')[-1]}`.", c.message.chat.id, c.message.message_id)
    except Exception as e: bot.answer_callback_query(c.id, f"❌ خطأ: {str(e)}")                                                             
@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_attack_cmd(m):                                                  if get_balance(m.chat.id) < PRICE_PER_MEMBER: return bot.send_message(m.chat.id, "❌ رصيد منخفض.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")     bot.register_next_step_handler(msg, step_target, army)

def step_target(m, army):
    src = m.text
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**")    bot.register_next_step_handler(msg, step_num, army, src)

def step_num(m, army, src):
    trg = m.text
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, finalize_attack, army, src, trg)                                                                    
def finalize_attack(m, army, src, trg):
    try:
        num = int(m.text)
        threading.Thread(target=lambda: asyncio.run(run_dragon_force_v73(army, src, trg, num, m.chat.id))).start()                              except: bot.send_message(m.chat.id, "❌ أدخل رقم صحيح.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")             def info(m):
    bal = get_balance(m.chat.id)
    army = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])                                                              bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{bal}$` \n📱 الجيش: `{army}`")

def check_my_pay(chat_id, track_id, amount):
    # محاولة الفحص كل دقيقة (لمدة 30 دقيقة)
    for _ in range(30):                                                       import time
        time.sleep(60)
        try:
            # طلب التأكد من الفاتورة
            res = requests.post("https://api.oxapay.com/merchants/inquiry", json={
                'merchant': OXAPAY_KEY,
                'trackId': track_id
            }, timeout=20).json()                                     
            if res.get('status') == 'Paid':
                # هنا السطر الذي يضيف الرصيد (تأكد أن اسم الدالة عندك update_balance)
                update_balance(chat_id, amount)
                bot.send_message(chat_id, f"✅ تم استلام {amount}$ وتحديث رصيدك تلقائياً!")
                break
        except:                                                                   continue
# ================= [ 🌐 خادم الويب للإبقاء حياً في Render ] ================
                                                                      def run_dummy_server():
    PORT = int(os.environ.get('PORT', 10000))
    class MyHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Dragon V73 Pro is Running!")
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        httpd.serve_forever()                                         app_web = Flask(__name__)
                                                                      
def health_check():                                                       return "Dragon V73 Pro is Running!", 200

def run_server():
    PORT = int(os.environ.get('PORT', 10000))
    # إعداد المسار داخل الدالة أو خارجها بشكل صحيح
    app_web.add_url_rule('/', 'health_check', health_check)
    app_web.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    print("🚀 دراجون V73 ينطلق بنظام الشحن التلقائي...")
    # تشغيل السيرفر في خيط مستقل
    threading.Thread(target=run_server, daemon=True).start()              bot.infinity_polling(timeout=60)
