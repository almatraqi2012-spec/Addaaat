import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718 # آيدي حسابك كمدير

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 إدارة البيانات ] ================
def get_db():
    conn = sqlite3.connect('dragon_final.db', timeout=30)
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

# ================= [ ⚔️ محرك سهم (V69) ] ================

async def run_attack_v69(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "📡 **بدأ الرادار العميق بالمسح... جاري الصيد.**")
    
    for session_file in army:
        if success >= total: break
        if get_balance(uid) < PRICE_PER_MEMBER:
            bot.send_message(uid, "🛑 **توقف! انتهى رصيدك.**")
            break

        added_list = get_memory()
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
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1
                    bot.send_message(uid, f"➕ [{session_file}] أضاف: `{t.first_name}`")
                    await asyncio.sleep(random.randint(30, 60))
                except: continue
            await client.disconnect()
        except: continue

    bot.send_message(uid, f"🏁 **اكتمل الاكتساح!**\n✅ الإضافة: `{success}`\n💰 رصيدك: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة والأوامر ] ================

@bot.message_handler(commands=['start'])
def start_panel(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم", "➕ إضافة حساب")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "🗑️ حذف حساب")
    if m.chat.id == ADMIN_ID: mk.add("💎 لوحة المدير")
    bot.send_message(m.chat.id, "🐲 **دراجون V69 - النسخة النهائية**\nكل الميزات مدمجة وشغالة 100%.", reply_markup=mk)

# --- لوحة المدير ---
@bot.message_handler(func=lambda m: m.text == "💎 لوحة المدير")
def admin_panel(m):
    if m.chat.id != ADMIN_ID: return
    msg = bot.send_message(m.chat.id, "أرسل (آيدي المستخدم + المبلغ) كالتالي:\n`12345678 10` ")
    bot.register_next_step_handler(msg, process_admin_add)

def process_admin_add(m):
    try:
        uid, amt = m.text.split()
        update_balance(int(uid), float(amt))
        bot.send_message(m.chat.id, f"✅ تم إضافة {amt}$ للحساب {uid}")
        bot.send_message(int(uid), f"🎉 تم إضافة {amt}$ لرصيدك من قبل الإدارة!")
    except: bot.send_message(m.chat.id, "❌ خطأ في التنسيق.")

# --- الشحن (Oxapay + Manual) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def charge_menu(m):
    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⚡ Oxapay", callback_data="oxa"),
        types.InlineKeyboardButton("💳 إيصال يدوي", callback_data="man")
    )
    bot.send_message(m.chat.id, f"💰 رصيدك: `{get_balance(m.chat.id)}$` \n\nالمحفظة:\n`{MY_WALLET}`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "oxa")
def oxa_call(c):
    msg = bot.send_message(c.message.chat.id, "💵 **المبلغ بالدولار:**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"🔗 رابط الدفع: {requests.post('https://api.oxapay.com/merchants/request', json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD'}).json().get('payLink')}"))

@bot.callback_query_handler(func=lambda c: c.data == "man")
def manual_call(c):
    bot.send_message(c.message.chat.id, "📸 أرسل صورة الإيصال الآن وسيقوم المدير بمراجعته.")

@bot.message_handler(content_types=['photo'])
def receipt_handler(m):
    if m.chat.id != ADMIN_ID:
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 إيصال من: `{m.chat.id}`\nللتفعيل استخدم لوحة المدير.")
        bot.reply_to(m, "⏳ جارِ مراجعة الإيصال...")

# --- إضافة الحسابات ---
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب")
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
        except Exception as e: return str(e), False
        finally: await cl.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم الربط!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر 2FA:**")
        bot.register_next_step_handler(msg, lambda p: bot.send_message(m.chat.id, "✅ تم!") if asyncio.run(cl.connect() or cl.sign_in(password=p.text) or cl.disconnect()) else None)

# --- الهجوم ---
@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم")
def attack_v69(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك 0$! اشحن أولاً.")
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد:**"), lambda n: threading.Thread(target=lambda: asyncio.run(run_attack_v69(army, s.text, t.text, int(n.text), m.chat.id))).start())))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    a = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n📱 الجيش: `{a}`")

if __name__ == '__main__':
    print("🐲 دراجون V69 أونلاين.. اكتساح شامل!")
    bot.infinity_polling()
