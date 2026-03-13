import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" # مفتاح التاجر
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # المحفظة
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 نظام الذاكرة "سهم" (السر في النجاح) ] ================
# استخدمنا ملف memory.txt لضمان عدم القفل (Database Locked)
def get_added_users():
    if not os.path.exists('memory.txt'): return []
    with open('memory.txt', 'r') as f: return f.read().splitlines()

def save_user(user_id):
    with open('memory.txt', 'a') as f: f.write(str(user_id) + '\n')

def get_balance(uid):
    conn = sqlite3.connect('dragon_v66.db', timeout=30)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    res = c.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amt):
    conn = sqlite3.connect('dragon_v66.db', timeout=30)
    c = conn.cursor()
    curr = get_balance(uid)
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amt, 2)))
    conn.commit(); conn.close()

# ================= [ ⚔️ محرك "سهم" المدمج V66 ] ================

async def run_sahm_attack(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **تم تفعيل رادار سهم (V66)... صيد الأهداف بدأ.**")
    
    for session_file in army:
        if success >= total: break
        added_list = get_added_users() # تحديث القائمة السوداء فوراً
        client = TelegramClient(session_file.replace('.session',''), MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue
            
            # الرادار العميق (نفس منطق السكربت الناجح)
            targets = []
            async for msg in client.iter_messages(src, limit=5000):
                if len(targets) >= 50: break 
                if msg.sender_id and str(msg.sender_id) not in added_list:
                    u = await msg.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)
            
            count = 0
            for user in targets:
                if success >= total or count >= 15: break # حد الأمان لكل حساب
                try:
                    await client(InviteToChannelRequest(trg, [user]))
                    save_user(user.id)
                    success += 1; count += 1
                    update_balance(uid, -PRICE_PER_MEMBER)
                    bot.send_message(uid, f"➕ [{session_file}] أضاف بنجاح: `{user.first_name}`")
                    await asyncio.sleep(random.randint(35, 65))
                except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
                    save_user(user.id); continue
                except Exception: continue
                
            await client.disconnect()
        except Exception as e:
            try: await client.disconnect()
            except: pass
            continue

    bot.send_message(uid, f"🏁 **انتهى الاكتساح!**\n✅ الأعضاء: `{success}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة والأزرار الكاملة ] ================

@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط سهم المطور)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("📊 إحصائيات النظام", "🗑️ حذف حساب من الجيش")
    bot.send_message(m.chat.id, "🐲 **إمبراطورية دراجون V66 - النسخة الشاملة**\nمرحباً بك يا قائد. البوت الآن يعمل بنفس قوة سكربت 'سهم'.", reply_markup=mk)

# --- إضافة حساب ---
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
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود (OTP):**")
        bot.register_next_step_handler(msg, step_2, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {h}")

def step_2(m, ph, h, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await cl.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح!**")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر (2FA):**")
        bot.register_next_step_handler(msg, lambda passw: bot.send_message(m.chat.id, "✅ تم!") if asyncio.run(cl.connect() or cl.sign_in(password=passw.text) or cl.disconnect()) else None)

# --- الشحن (التاجر والمحفظة) ---
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⚡ Oxapay (تلقائي)", callback_data="oxa"),
        types.InlineKeyboardButton("💳 يدوي (إيصال)", callback_data="man")
    )
    bot.send_message(m.chat.id, f"💰 رصيدك: `{get_balance(m.chat.id)}$` \n\nحول للمحفظة وأرسل الإيصال:\n`{MY_WALLET}`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "oxa")
def oxa_p(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"🔗 رابط الدفع: {requests.post('https://api.oxapay.com/merchants/request', json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD'}).json().get('payLink')}"))

# --- الهجوم والحذف ---
@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط سهم المطور)")
def start_atk(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ!")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد:**"), lambda n: threading.Thread(target=lambda: asyncio.run(run_sahm_attack(army, s.text, t.text, int(n.text), m.chat.id))).start())))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    a = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n📱 الجيش: `{a}` حساب.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_acc(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")]
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army: mk.add(types.InlineKeyboardButton(f"❌ {s.split('_')[-1]}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_confirm(c):
    f = c.data.replace("del_", ""); os.remove(f) if os.path.exists(f) else None
    bot.edit_message_text("✅ تم حذف الحساب.", c.message.chat.id, c.message.message_id)

if __name__ == '__main__':
    bot.infinity_polling()
