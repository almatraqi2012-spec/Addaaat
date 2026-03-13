import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية - النسخة النهائية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 قاعدة البيانات والذاكرة ] ================
def init_db():
    conn = sqlite3.connect('dragon_final.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL)')
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect('dragon_final.db')
    res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amount):
    conn = sqlite3.connect('dragon_final.db')
    curr = get_balance(uid)
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amount, 2)))
    conn.commit(); conn.close()

def save_mem(uid):
    with open('memory.txt', 'a') as f: f.write(str(uid) + '\n')

def get_mem():
    return set(open('memory.txt', 'r').read().splitlines()) if os.path.exists('memory.txt') else set()

# ================= [ ⚔️ المحرك الأسطوري V50 ] ================

async def dragon_core_engine(army, src_input, trg_input, total, uid):
    success = 0
    mem_list = get_mem()
    bot.send_message(uid, "📡 **بدأ رادار دراجون بالاختراق... جاري صيد الأهداف.**")
    
    # استخدام أول حساب ككشاف
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await scout.connect()
        # محاولة فك تشفير يوزر المصدر والهدف
        source = await scout.get_entity(src_input)
        target_group = await scout.get_entity(trg_input)
        
        # الانضمام لضمان الرؤية
        try: await scout(JoinChannelRequest(source))
        except: pass

        targets = []
        # سحب المتفاعلين (رادار سهم)
        async for m in scout.iter_messages(source, limit=1000):
            if len(targets) >= total: break
            if m.sender_id and str(m.sender_id) not in mem_list:
                u = await m.get_sender()
                if isinstance(u, tl_types.User) and not u.bot:
                    targets.append(u)
        
        # سحب الأونلاين (رادار دراجون) إذا نقص العدد
        if len(targets) < total:
            async for u in scout.iter_participants(source, limit=500):
                if len(targets) >= total: break
                if str(u.id) not in mem_list and not u.bot:
                    if isinstance(u.status, (tl_types.UserStatusRecently, tl_types.UserStatusOnline)):
                        targets.append(u)
        
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ خطأ في الرادار: {e}")

    if not targets: return bot.send_message(uid, "❌ لم نجد أعضاء جدد في هذا المصدر.")
    bot.send_message(uid, f"⚔️ **تم قنص {len(targets)} متفاعل. بدأ الجر القسري!**")

    # [ عملية الإضافة بتدوير الجيش ]
    for i, target in enumerate(targets):
        if success >= total: break
        
        acc = army[i % len(army)].replace('.session','')
        client = TelegramClient(acc, MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            # الانضمام للمجموعة الهدف قبل الإضافة لكسر الحماية
            try: await client(JoinChannelRequest(target_group))
            except: pass
            
            await client(InviteToChannelRequest(target_group, [target]))
            save_mem(target.id)
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total}] تم سحب: `@{target.username or target.id}`")
            await client.disconnect()
            await asyncio.sleep(random.randint(25, 45)) # فاصل أمان
            
        except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
            save_mem(target.id); await client.disconnect(); continue
        except errors.FloodWaitError as e:
            bot.send_message(uid, f"⏳ الحساب `{acc}` متعب، سأنتظر {e.seconds} ثانية.")
            await client.disconnect(); continue
        except Exception:
            await client.disconnect(); continue

    bot.send_message(uid, f"🏁 **اكتمل الاكتساح!**\n✅ الأعضاء المضافين: `{success}`")

# ================= [ 📱 الواجهة والأوامر ] ================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط دراجون الشامل)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي", "📊 إحصائيات النظام", "🗑️ حذف حساب من الجيش")
    bot.send_message(m.chat.id, "🐲 **دراجون V50 - نسخة تحدي المحترفين**\nجاهز لسحق أي منافس.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي (مثال: 9665...):**")
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
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود (OTP):**")
        bot.register_next_step_handler(msg, step_login, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ فشل: {h}")

def step_login(m, ph, h, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await cl.connect()
        try: await cl.sign_in(ph, m.text, phone_code_hash=h); return "DONE", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await cl.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "DONE": bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر التحقق بخطوتين (2FA):**")
        bot.register_next_step_handler(msg, step_2fa, sess)
    else: bot.send_message(m.chat.id, f"❌ {res}")

async def step_2fa(m, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH); await cl.connect()
    try: await cl.sign_in(password=m.text); bot.send_message(m.chat.id, "✅ تم فك الحماية بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")
    finally: await cl.disconnect()

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط دراجون الشامل)")
def attack_init(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_") and f.endswith('.session')]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ! أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, attack_step2, army)

def attack_step2(m, army):
    src = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**")
    bot.register_next_step_handler(msg, attack_step3, army, src)

def attack_step3(m, army, src):
    trg = m.text.strip().replace('@','')
    msg = bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**")
    bot.register_next_step_handler(msg, attack_final, army, src, trg)

def attack_final(m, army, src, trg):
    try:
        n = int(m.text)
        if get_balance(m.chat.id) < (n * PRICE_PER_MEMBER): return bot.send_message(m.chat.id, "❌ رصيدك لا يكفي.")
        threading.Thread(target=lambda: asyncio.run(dragon_core_engine(army, src, trg, n, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ أدخل رقماً صحيحاً.")

# [ نظام الشحن والمالية ]
@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "oxa")
def oxa_pay(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"🔗 فاتورة الشحن: {requests.post('https://api.oxapay.com/merchants/request', json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD', 'description': str(m.chat.id)}).json().get('payLink', 'خطأ')}"))

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def manual_pay(c):
    bot.send_message(c.message.chat.id, f"💳 حول لعنوان المحفظة وأرسل الإيصال:\n`{MY_WALLET}`")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ شحن 10$", callback_data=f"adm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ تم إرسال الإيصال، انتظر التفعيل.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_confirm(c):
    d = c.data.split('_'); update_balance(int(d[2]), float(d[1]))
    bot.send_message(int(d[2]), f"🎉 تم شحن {d[1]}$ لرصيدك!"); bot.edit_message_caption("✅ تم التأكيد", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")]
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 جيشك: `{len(army)}` حساب.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_menu(m):
    army = [f for f in os.listdir('.') if f.startswith(f"sess_{m.chat.id}_")]
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ.")
    mk = types.InlineKeyboardMarkup()
    for s in army: mk.add(types.InlineKeyboardButton(f"❌ {s.split('_')[-1]}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_exec(c):
    f = c.data.replace("del_", ""); os.remove(f) if os.path.exists(f) else None
    bot.edit_message_text("✅ تم حذف الحساب.", c.message.chat.id, c.message.message_id)

if __name__ == '__main__':
    init_db()
    print("🐲 دراجون V50 الأسطوري قيد التشغيل...")
    bot.infinity_polling()
