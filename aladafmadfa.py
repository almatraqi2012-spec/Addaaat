import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ===============
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718 # آيدي حسابك كمالك

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 💾 إدارة البيانات (الرصيد والذاكرة) ] ================
def get_db():
    conn = sqlite3.connect('dragon_final_v73.db', timeout=30)
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    return conn

def get_balance(uid):
    conn = get_db(); res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amt):
    conn = get_db(); curr = get_balance(uid)
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amt, 2)))
    conn.commit(); conn.close()

def save_user_memory(user_id):
    with open('memory.txt', 'a') as f: f.write(str(user_id) + '\n')

def get_memory():
    if not os.path.exists('memory.txt'): return []
    with open('memory.txt', 'r') as f: return f.read().splitlines()

# ================= [ ⚔️ محرك سهم (القوة الأصلية) ] ================

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
            
            # الرادار العميق (5000 رسالة - السر في القوة)
            targets = []
            async for m in client.iter_messages(src, limit=5000):
                if len(targets) >= 100: break 
                if m.sender_id and str(m.sender_id) not in added_list:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)
            
            count = 0
            for t in targets:
                if success >= total or count >= 15 or get_balance(uid) < PRICE_PER_MEMBER: break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1; count += 1
                    bot.send_message(uid, f"➕ [{session_file}] أضاف: `{t.first_name}` | مجموعك: `{success}`")
                    await asyncio.sleep(random.randint(30, 60))
                except: continue
            await client.disconnect()
        except: continue

    bot.send_message(uid, f"🏁 **اكتملت المهمة!**\n✅ الإضافة: `{success}`\n💰 الرصيد المتبقي: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة ولوحة التحكم ] ================

@bot.message_handler(commands=['start'])
def start_main(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الأضافه", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب")
    if m.chat.id == ADMIN_ID: mk.add("💎 لوحة المالك")
    bot.send_message(m.chat.id, "🐲 **مرحباً بكم في بوت دراجون**\nيمكنك إضافة اعضاء لقروبك من اي قروب تريده.", reply_markup=mk)

# --- نظام الشحن المزدوج (آلي + يدوي) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def payment_menu(m):
    user_states[m.chat.id] = None
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("⚡ شحن Oxapay (آلي)", callback_data="pay_oxa"),
        types.InlineKeyboardButton("💳 شحن محفظة (يدوي)", callback_data="pay_man")
    )
    bot.send_message(m.chat.id, f"💰 رصيدك: `{get_balance(m.chat.id)}$` \n\nاختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_call(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, process_oxa)

def process_oxa(m):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD'}).json()
        link = res.get('payLink')
        if link:
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("اضغط هنا للدفع 🔗", url=link))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بقيمة {m.text}$\nيرجى الدفع عبر الرابط:", reply_markup=mk)
        else: bot.send_message(m.chat.id, "❌ خطأ من بوابة الدفع.")
    except: bot.send_message(m.chat.id, "⚠️ أدخل مبلغاً صحيحاً.")

@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def man_call(c):
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(c.message.chat.id, f"💳 **المحفظة:**\n`{MY_WALLET}`\n\n📸 **أرسل صورة الإيصال الآن.**")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup(row_width=3)
        mk.add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 50$", callback_data=f"set_50_{m.chat.id}")
        )
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, 
                       caption=f"📩 **إيصال جديد من:** `{m.chat.id}`\nاسم المستخدم: @{m.from_user.username}", reply_markup=mk)
        bot.reply_to(m, "⏳ تم إرسال الإيصال للمدير. سيتم التفعيل فوراً.")
        user_states[m.chat.id] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    _, amt, uid = c.data.split('_')
    update_balance(int(uid), float(amt))
    bot.send_message(int(uid), f"🎉 **مبروك! تم شحن {amt}$ في حسابك.**")
    bot.edit_message_caption(f"✅ تم تفعيل {amt}$ للحساب {uid}", c.message.chat.id, c.message.message_id)

# --- تفعيل أزرار الإحصائيات والحذف ---
@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats_all(m):
    a_count = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **إحصائياتك:**\n📱 جيش الحسابات: `{a_count}`\n✅ الذاكرة (تم اصطيادهم): `{len(get_memory())}`\n💰 رصيدك: `{get_balance(m.chat.id)}$` ")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب")
def delete_acc_menu(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        phone = s.split('_')[-1].replace('.session', '')
        mk.add(types.InlineKeyboardButton(f"❌ حذف {phone}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر حساباً لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def finalize_delete(c):
    fname = c.data.replace("rm_", "")
    if os.path.exists(fname):
        os.remove(fname)
        bot.edit_message_text(f"✅ تم حذف الحساب بنجاح.", c.message.chat.id, c.message.message_id)

# --- تنفيذ الهجوم ---
@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_attack_cmd(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك 0$! اشحن أولاً.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**"), lambda n: threading.Thread(target=lambda: asyncio.run(run_sahm_v73(army, s.text, t.text, int(n.text), m.chat.id))).start())))

# --- حسابي وإضافة حساب ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    a = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n📱 حسابات الجيش: `{a}`")

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي:**")
    bot.register_next_step_handler(msg, step_1)

def step_1(m):
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
        bot.register_next_step_handler(msg, step_2, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ {h}")

def step_2(m, ph, h, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception: return "Error", False
        finally: await cl.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم ربط الحساب!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر 2FA:**")
        bot.register_next_step_handler(msg, lambda p: bot.send_message(m.chat.id, "✅ تم!") if asyncio.run(cl.connect() or cl.sign_in(password=p.text) or cl.disconnect()) else None)

if __name__ == '__main__':
    bot.infinity_polling()
