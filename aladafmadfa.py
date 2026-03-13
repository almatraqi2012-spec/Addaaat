import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718 # آيدي حسابك (المالك)

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {} # لتتبع حالة المستخدم (هل هو في مرحلة إرسال إيصال؟)

# ================= [ 💾 إدارة البيانات والذاكرة ] ================
def get_db():
    conn = sqlite3.connect('dragon_pro.db', timeout=30)
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    return conn

def get_balance(uid):
    conn = get_db(); res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amt):
    conn = get_db(); curr = get_balance(uid)
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amt, 2)))
    conn.commit(); conn.close()

# ================= [ ⚔️ محرك سهم (نفس القوة الأصلية) ] ================

async def run_sahm_engine(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **بدأ اكتساح سهم... جاري صيد الأهداف.**")
    if not os.path.exists('memory.txt'): open('memory.txt', 'w').close()
    
    for session_file in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER: break
        with open('memory.txt', 'r') as f: added_list = f.read().splitlines()
        
        client = TelegramClient(session_file.replace('.session',''), MY_API_ID, MY_API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue
            
            targets = []
            async for m in client.iter_messages(src, limit=5000):
                if len(targets) >= 30: break 
                if m.sender_id and str(m.sender_id) not in added_list:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)
            
            for t in targets:
                if get_balance(uid) < PRICE_PER_MEMBER or success >= total: break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    with open('memory.txt', 'a') as f: f.write(str(t.id) + '\n')
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1
                    bot.send_message(uid, f"➕ [{session_file}] أضاف: `{t.first_name}`")
                    await asyncio.sleep(random.randint(30, 60))
                except: continue
            await client.disconnect()
        except: continue
    bot.send_message(uid, f"🏁 **انتهى الاكتساح!**\n✅ الإضافة: `{success}`\n💰 رصيدك الحالي: `{get_balance(uid)}$` ")

# ================= [ 📱 قسم الدفع المنظم ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    user_states[m.chat.id] = None # تصفير الحالة
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="pay_auto"),
        types.InlineKeyboardButton("💳 شحن يدوي (إرسال إيصال)", callback_data="pay_manual")
    )
    txt = f"💰 **رصيدك الحالي:** `{get_balance(m.chat.id)}$` \n\nاختر وسيلة الشحن المناسبة:"
    bot.send_message(m.chat.id, txt, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "pay_auto")
def oxa_payment(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ المطلوب شحنه ($):**\nمثال: `10` أو `50`")
    bot.register_next_step_handler(msg, process_oxa_link)

def process_oxa_link(m):
    try:
        amount = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': amount, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        
        pay_url = res.get('payLink')
        if pay_url:
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع", url=pay_url))
            bot.send_message(m.chat.id, f"✅ **تم إنشاء فاتورة بقيمة {amount}$**\nيرجى الدفع عبر الرابط التالي:", reply_markup=mk)
        else:
            bot.send_message(m.chat.id, "❌ حدث خطأ في الاتصال ببوابة Oxapay. حاول لاحقاً.")
    except:
        bot.send_message(m.chat.id, "⚠️ يرجى إدخال رقم صحيح (مثلاً: 10).")

@bot.callback_query_handler(func=lambda c: c.data == "pay_manual")
def manual_payment(c):
    user_states[c.message.chat.id] = "waiting_receipt" # تعيين الحالة
    txt = f"💳 **الشحن اليدوي:**\n\nيرجى تحويل المبلغ لعنوان المحفظة:\n`{MY_WALLET}`\n\n📸 **الآن أرسل صورة الإيصال (سكرين شوت) هنا مباشرة.**"
    bot.send_message(c.message.chat.id, txt)

# --- معالج استقبال الإيصال وإرساله للمالك ---
@bot.message_handler(content_types=['photo'])
def handle_receipt_photo(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        # إرسال للمالك
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ تفعيل 10$", callback_data=f"adm_10_{m.chat.id}"),
            types.InlineKeyboardButton("✅ تفعيل 50$", callback_data=f"adm_50_{m.chat.id}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, 
                       caption=f"📩 **إيصال شحن جديد**\n👤 المستخدم: `{m.chat.id}`\nاسم المستخدم: @{m.from_user.username}", reply_markup=mk)
        
        bot.reply_to(m, "✅ **تم استلام الإيصال!**\nجارِ المراجعة من قبل الإدارة وتفعيل الرصيد فوراً.")
        user_states[m.chat.id] = None # إنهاء الحالة
    else:
        bot.reply_to(m, "صورة جميلة! لكن إذا كنت تريد الشحن، اضغط على زر 'شحن الرصيد' أولاً.")

# ================= [ 📱 بقية الأوامر والتحكم ] ================

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_confirm_pay(c):
    # adm_10_12345
    _, amt, uid = c.data.split('_')
    update_balance(int(uid), float(amt))
    bot.send_message(int(uid), f"🎉 **مبروك! تم شحن {amt}$ في حسابك بنجاح.**")
    bot.edit_message_caption(f"✅ تم تفعيل {amt}$ للمستخدم {uid}", c.message.chat.id, c.message.message_id)

@bot.message_handler(commands=['start'])
def start_panel(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم", "➕ إضافة حساب")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("🗑️ حذف حساب")
    bot.send_message(m.chat.id, "🐲 **دراجون V70 - النسخة المصححة**\nتم تنظيم الدفع وربط الإيصالات بالمالك.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم")
def start_atk(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك لا يكفي (0$). اشحن أولاً.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ! أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**"), lambda n: threading.Thread(target=lambda: asyncio.run(run_sahm_engine(army, s.text, t.text, int(n.text), m.chat.id))).start())))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    a = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n📱 عدد الحسابات: `{a}`")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, step_otp)

def step_otp(m):
    ph = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{ph}"
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def get_c():
        await cl.connect()
        try: return (await cl.send_code_request(ph)).phone_code_hash, "OK"
        except Exception as e: return str(e), "ERR"
        finally: await cl.disconnect()
    h, status = asyncio.run(get_c())
    if status == "OK":
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
        bot.register_next_step_handler(msg, step_login, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ {h}")

def step_login(m, ph, h, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await cl.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم الربط!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر 2FA:**")
        bot.register_next_step_handler(msg, lambda p: bot.send_message(m.chat.id, "✅ تم!") if asyncio.run(cl.connect() or cl.sign_in(password=p.text) or cl.disconnect()) else None)

if __name__ == '__main__':
    bot.infinity_polling()
