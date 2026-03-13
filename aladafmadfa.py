import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 إدارة الرصيد والذاكرة ] ================
def get_db():
    conn = sqlite3.connect('dragon_v68.db', timeout=30)
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
    return conn

def get_balance(uid):
    conn = get_db(); res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amt):
    conn = get_db(); curr = get_balance(uid)
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amt, 2)))
    conn.commit(); conn.close()

def save_user_to_memory(user_id):
    with open('memory.txt', 'a') as f: f.write(str(user_id) + '\n')

def get_added_users():
    if not os.path.exists('memory.txt'): return []
    with open('memory.txt', 'r') as f: return f.read().splitlines()

# ================= [ ⚔️ محرك سهم الاحترافي V68 ] ================

async def run_controlled_attack(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "📡 **بدأ المحرك بفحص الرصيد وصيد الأهداف...**")
    
    for session_file in army:
        if success >= total: break
        
        # فحص الرصيد قبل البدء مع كل حساب
        if get_balance(uid) < PRICE_PER_MEMBER:
            bot.send_message(uid, "⚠️ **توقف العمل! نفذ رصيدك تماماً.**")
            break

        added_list = get_added_users()
        client = TelegramClient(session_file.replace('.session',''), MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue
            
            targets = []
            async for msg in client.iter_messages(src, limit=5000):
                if len(targets) >= 30: break 
                if msg.sender_id and str(msg.sender_id) not in added_list:
                    u = await msg.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]: targets.append(u)
            
            for user in targets:
                # فحص الرصيد قبل كل عملية إضافة "فردية"
                if get_balance(uid) < PRICE_PER_MEMBER:
                    bot.send_message(uid, "🛑 **عذراً، رصيدك انتهى. اشحن للاستمرار.**")
                    await client.disconnect(); return

                if success >= total: break
                
                try:
                    await client(InviteToChannelRequest(trg, [user]))
                    save_user_to_memory(user.id)
                    update_balance(uid, -PRICE_PER_MEMBER) # خصم فوري
                    success += 1
                    bot.send_message(uid, f"➕ [{session_file}] أضاف بنجاح: `{user.first_name}`")
                    await asyncio.sleep(random.randint(35, 60))
                except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
                    save_user_to_memory(user.id); continue
                except Exception: continue
                
            await client.disconnect()
        except:
            try: await client.disconnect()
            except: pass
            continue

    bot.send_message(uid, f"🏁 **اكتملت العملية!**\n✅ الإضافة: `{success}`\n💰 رصيدك الحالي: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة والتحكم ] ================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (مدفوع)", "➕ إضافة حساب")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("🗑️ حذف حساب")
    bot.send_message(m.chat.id, "🐲 **دراجون V68 - نظام التحكم المالي**\nالآن كل عضو مضاف محسوب بدقة بالرصيد.", reply_markup=mk)

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
    if res == "OK": bot.send_message(m.chat.id, "✅ تم ربط الحساب.")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل الباسورد (2FA):**")
        bot.register_next_step_handler(msg, lambda p: bot.send_message(m.chat.id, "✅ تم!") if asyncio.run(cl.connect() or cl.sign_in(password=p.text) or cl.disconnect()) else None)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay(m):
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⚡ Oxapay (تلقائي)", callback_data="oxa"), types.InlineKeyboardButton("💳 يدوي (إيصال)", callback_data="man"))
    bot.send_message(m.chat.id, f"💰 رصيدك الحالي: `{get_balance(m.chat.id)}$` \n\nحول للمحفظة:\n`{MY_WALLET}`", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "oxa")
def oxa_p(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"🔗 الرابط: {requests.post('https://api.oxapay.com/merchants/request', json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD'}).json().get('payLink')}"))

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (مدفوع)")
def attack_cmd(m):
    # فحص أولي قبل طلب اليوزرات
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ **رصيدك 0$! اشحن أولاً لكي تتمكن من الهجوم.**")
        
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ!")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر:**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك:**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**"), lambda n: threading.Thread(target=lambda: asyncio.run(run_controlled_attack(army, s.text, t.text, int(n.text), m.chat.id))).start())))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    a = len([f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")])
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$` \n📱 عدد الحسابات: `{a}`")

if __name__ == '__main__':
    bot.infinity_polling()
