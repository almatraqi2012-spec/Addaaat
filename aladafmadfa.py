import telebot, threading, time, asyncio, requests, random, os, sqlite3
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from telethon.tl.types import UserStatusRecently, UserStatusOnline

# ================= [ ⚙️ الإعدادات المركزية - النسخة القتالية ] ================
BOT_TOKEN = "8574116889:AAHSlnMQE442Y_RWH5hYq4wNcJkOw2LiArM"
MY_API_ID = 21349867
MY_API_HASH = '7ced3ee4c80117bd5138410811b91f9f'
ADMIN_ID = 6016547718

OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 💾 إدارة البيانات والذاكرة ] ================
def init_db():
    conn = sqlite3.connect('dragon_v48.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance REAL)')
    conn.commit(); conn.close()

def get_balance(uid):
    conn = sqlite3.connect('dragon_v48.db')
    res = conn.execute("SELECT balance FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close(); return res[0] if res else 0.0

def update_balance(uid, amount):
    curr = get_balance(uid)
    conn = sqlite3.connect('dragon_v48.db')
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, round(curr + amount, 2)))
    conn.commit(); conn.close()

def save_mem(uid):
    with open('memory.txt', 'a') as f: f.write(str(uid) + '\n')

def get_mem():
    return set(open('memory.txt', 'r').read().splitlines()) if os.path.exists('memory.txt') else set()

def get_army(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ ⚔️ محرك دراجون V48: كاسر الجسور ] ================

async def dragon_core_engine(army, src_input, trg_input, total, uid):
    success = 0
    mem_list = get_mem()
    bot.send_message(uid, "📡 **جاري اختراق المصدر بآليات دراجون V48...**")
    
    # تحسين: تحويل اليوزرات إلى كيانات صالحة فوراً لتجنب ResolveUsernameRequest
    targets = []
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await scout.connect()
        # محاولة الانضمام لفك تشفير المجموعة (حل جذري لخطأ Key not registered)
        try:
            source = await scout.get_entity(src_input)
            target_group = await scout.get_entity(trg_input)
            await scout(JoinChannelRequest(source))
        except Exception as e:
            return bot.send_message(uid, f"❌ فشل الوصول للمصدر: {e}")
        
        # 1. رادار سهم (المتفاعلين الجدد)
        async for m in scout.iter_messages(source, limit=2000):
            if len(targets) >= total: break
            if m.sender_id and str(m.sender_id) not in mem_list:
                s = await m.get_sender()
                if isinstance(s, tl_types.User) and not s.bot:
                    targets.append(s)
        
        # 2. السحب من قائمة الأعضاء (للأعضاء المتواجدين حالياً)
        if len(targets) < total:
            async for u in scout.iter_participants(source, limit=1000):
                if len(targets) >= total * 2: break
                if str(u.id) not in mem_list and not u.bot:
                    if isinstance(u.status, (UserStatusRecently, UserStatusOnline)):
                        targets.append(u)
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ عطل في الرادار: {e}")

    if not targets: return bot.send_message(uid, "❌ المصدر محمي أو تم سحبه بالكامل مسبقاً.")
    
    bot.send_message(uid, f"⚔️ **تم قنص {len(targets)} هدف حقيقي. بدأت مرحلة الاكتساح!**")

    # [ مرحلة الإضافة القسرية ]
    for i, target in enumerate(targets):
        if success >= total: break
        
        current_account = army[i % len(army)].replace('.session','')
        client = TelegramClient(current_account, MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            # خطوة ذكية: جعل الحساب ينضم للمجموعة الهدف قبل الإضافة لتجنب الحظر
            try: await client(JoinChannelRequest(target_group))
            except: pass
            
            await client(InviteToChannelRequest(target_group, [target]))
            save_mem(target.id)
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{total}] تم جر: `@{target.username or target.id}`")
            
            await client.disconnect()
            # فاصل زمني متغير لذكاء التخفي
            await asyncio.sleep(random.randint(20, 35))
            
        except (errors.UserPrivacyRestrictedError, errors.UserAlreadyParticipantError):
            save_mem(target.id); await client.disconnect(); continue
        except errors.FloodWaitError as e:
            bot.send_message(uid, f"⏳ الحساب `{current_account}` طلب استراحة لـ {e.seconds} ثانية.")
            await client.disconnect(); continue
        except Exception:
            await client.disconnect(); continue

    bot.send_message(uid, f"🏁 **انتهت الملحمة بنجاح!**\n✅ الأعضاء الجدد: `{success}`\n💰 رصيدك المتبقي: `{get_balance(uid)}$` ")

# ================= [ 📱 الواجهة والأزرار ] ================

@bot.message_handler(commands=['start'])
def start_cmd(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (نمط دراجون الشامل)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي", "📊 إحصائيات النظام", "🗑️ حذف حساب من الجيش")
    bot.send_message(m.chat.id, "🐲 **دراجون V48 - إمبراطورية الاكتساح**\nالنسخة التي لا تقهر.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (نمط دراجون الشامل)")
def attack_init(m):
    if not get_army(m.chat.id): return bot.send_message(m.chat.id, "❌ جيشك فارغ! أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 **يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, lambda s: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 **يوزر مجموعتك (بدون @):**"), lambda t: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 **العدد المطلوب:**"), lambda n: run_attack(s.text, t.text, n))))

def run_attack(src, trg, n):
    try:
        count = int(n.text)
        if get_balance(n.chat.id) < (count * PRICE_PER_MEMBER): return bot.send_message(n.chat.id, "❌ رصيدك غير كافٍ.")
        threading.Thread(target=lambda: asyncio.run(dragon_core_engine(get_army(n.chat.id), src.strip().replace('@',''), trg.strip().replace('@',''), count, n.chat.id))).start()
    except: bot.send_message(n.chat.id, "⚠️ خطأ في البيانات.")

# [ نظام 2FA الكامل ]
@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_phone(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل الرقم مع المفتاح الدولي (مثال: 9665...):**")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    ph = m.text.strip().replace('+', '')
    sess = f"sess_{m.chat.id}_{ph}"
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def get_hash():
        await client.connect()
        try: return (await client.send_code_request(ph)).phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    h, ok = asyncio.run(get_hash())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
        bot.register_next_step_handler(msg, process_otp, ph, h, sess)
    else: bot.send_message(m.chat.id, f"❌ فشل: {h}")

def process_otp(m, ph, h, sess):
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try: await client.sign_in(ph, m.text, phone_code_hash=h); return "OK", False
        except errors.SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    res, n2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم ربط الحساب بنجاح!")
    elif n2fa:
        msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر التحقق بخطوتين:**")
        bot.register_next_step_handler(msg, process_2fa, sess)
    else: bot.send_message(m.chat.id, f"❌ {res}")

async def process_2fa(m, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH); await cl.connect()
    try: await cl.sign_in(password=m.text); bot.send_message(m.chat.id, "✅ تم الربط!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")
    finally: await cl.disconnect()

# ================= [ 💰 النظام المالي والادمن ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="oxa"),
           types.InlineKeyboardButton("💳 شحن يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "oxa")
def oxa_pay(c):
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, f"🔗 رابط الدفع: {requests.post('https://api.oxapay.com/merchants/request', json={'merchant': OXAPAY_KEY, 'amount': m.text, 'currency': 'USD', 'description': str(m.chat.id)}).json().get('payLink', 'خطأ')}"))

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def manual_pay(c):
    bot.send_message(c.message.chat.id, f"💳 حول هنا وأرسل الإيصال:\n`{MY_WALLET}`")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ شحن 10$", callback_data=f"adm_10_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارِ التدقيق...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_confirm(c):
    d = c.data.split('_'); update_balance(int(d[2]), float(d[1]))
    bot.send_message(int(d[2]), f"🎁 تم شحن {d[1]}$!"); bot.edit_message_caption("✅ تم التأكيد", c.message.chat.id, c.message.message_id)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 الجيش: `{len(get_army(m.chat.id))}` حساب.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات النظام")
def sys_stats(m):
    total_sess = len([f for f in os.listdir('.') if f.endswith('.session')])
    bot.send_message(m.chat.id, f"📊 **الإحصائيات الكلية:**\n📱 إجمالي الجلسات: `{total_sess}`")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف حساب من الجيش")
def del_menu(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ لا يوجد حسابات.")
    mk = types.InlineKeyboardMarkup()
    for s in army: mk.add(types.InlineKeyboardButton(f"❌ {s.split('_')[-1]}", callback_data=f"del_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب لحذفه:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_confirm(c):
    f = c.data.replace("del_", ""); os.remove(f) if os.path.exists(f) else None
    bot.edit_message_text("✅ تم حذف الحساب.", c.message.chat.id, c.message.message_id)

if __name__ == '__main__':
    init_db()
    print("🐲 دراجون V48 جاهز للاكتساح...")
    bot.infinity_polling()
