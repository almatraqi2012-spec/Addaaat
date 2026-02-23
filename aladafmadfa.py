import telebot
from telebot import types
import sqlite3, requests, asyncio, threading, time
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent
from telethon.errors import *

# --- الإعدادات (تأكد من صحتها) ---
BOT_TOKEN = "8574116889:AAFwu0ol0Cj4E2Ynn_9iuPcJKFiGz-kwcqA"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 5163375125  
PRICE_PER_MEMBER = 0.05 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

def db_run(query, params=(), fetch=False):
    conn = sqlite3.connect('dragon_vfinal.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

# تهيئة الجداول
db_run('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
db_run('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, session TEXT, phone TEXT)')

# --- المحرك الواقعي (القلب النابض) ---
async def transfer_process(uid, src, trg, count, mid):
    accs = db_run("SELECT session FROM accounts WHERE user_id=?", (uid,), True)
    if not accs: return bot.send_message(uid, "❌ أضف حسابات أولاً!")
    
    clients = []
    for s in accs:
        cl = TelegramClient(StringSession(s[0]), MY_API_ID, MY_API_HASH)
        await cl.connect()
        if await cl.is_user_authorized(): clients.append(cl)
    
    if not clients: return bot.send_message(uid, "❌ حساباتك معطلة!")
    
    added = 0
    try:
        leader = clients[0]
        s_ent = await leader.get_entity(src); t_ent = await leader.get_entity(trg)
        await leader(JoinChannelRequest(s_ent)); await leader(JoinChannelRequest(t_ent))
        
        async for u in leader.iter_participants(s_ent, limit=500, aggressive=True):
            if added >= count or (db_run("SELECT balance FROM users WHERE user_id=?", (uid,), True)[0][0] < PRICE_PER_MEMBER): break
            
            for c in clients:
                try:
                    await c(InviteToChannelRequest(t_ent, [u]))
                    # التحقق الفعلي من الانضمام
                    check = await c(GetParticipantsRequest(t_ent, ChannelParticipantsRecent(), 0, 5, hash=0))
                    if any(p.id == u.id for p in check.users):
                        added += 1
                        db_run("UPDATE users SET balance = balance - ? WHERE user_id=?", (PRICE_PER_MEMBER, uid))
                        bot.edit_message_text(f"✅ مضاف حقيقي: {added}\n💰 المتبقي: {db_run('SELECT balance FROM users WHERE user_id=?', (uid,), True)[0][0]:.2f}$", uid, mid)
                        await asyncio.sleep(5) # حماية
                        break
                except: continue
    except Exception as e: bot.send_message(uid, f"❌ خطأ: {e}")
    bot.send_message(uid, f"🏁 اكتمل! المضافين فعلياً: {added}")

# --- معالجة الأوامر والشحن ---
@bot.message_handler(commands=['start'])
def start(m):
    db_run("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (m.chat.id,))
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 حسابي", "🔄 بدء النقل", "➕ إضافة حسابات", "💰 الشحن")
    bot.send_message(m.chat.id, "🐲 دراجون V5: القوة والصدق.", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💰 الشحن")
def pay_msg(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⚡ تلقائي", callback_data="p_auto"), types.InlineKeyboardButton("👨‍💻 يدوي", callback_data="p_man"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    bot.answer_callback_query(c.id)
    if c.data.startswith("ok_"): # موافقة المالك
        _, amt, target = c.data.split("_")
        db_run("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, target))
        bot.send_message(target, f"✅ تم شحن {amt}$!")
        bot.edit_message_caption(f"✅ تم لـ {target}", c.message.chat.id, c.message.message_id)
    elif c.data == "p_man":
        bot.send_message(c.message.chat.id, f"💳 حول لـ:\n`{MY_WALLET}`\nوارسل الصورة.")

@bot.message_handler(content_types=['photo'])
def receipt(m):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("✅ 10$", callback_data=f"ok_10_{m.chat.id}"), types.InlineKeyboardButton("✅ 20$", callback_data=f"ok_20_{m.chat.id}"))
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 طلب شحن من {m.chat.id}", reply_markup=kb)
    bot.send_message(m.chat.id, "⏳ جاري المراجعة...")

@bot.message_handler(func=lambda m: m.text == "🔄 بدء النقل")
def tr_go(m):
    bot.send_message(m.chat.id, "📦 رابط المصدر:")
    bot.register_next_step_handler(m, lambda m1: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 رابط مجموعتك:"), lambda m2: bot.register_next_step_handler(bot.send_message(m.chat.id, "🔢 كم العدد؟"), lambda m3: threading.Thread(target=lambda: asyncio.run(transfer_process(m.chat.id, m1.text, m2.text, int(m3.text), bot.send_message(m.chat.id, "📡 جاري النقل...").message_id))).start())))

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حسابات")
def add_acc(m):
    bot.send_message(m.chat.id, "📱 الرقم:")
    bot.register_next_step_handler(m, add_2)

def add_2(m):
    phone = m.text.strip(); cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH)
    async def get_c(): await cl.connect(); r = await cl.send_code_request(phone); return r.phone_code_hash, cl.session.save()
    h, s = asyncio.run(get_c())
    bot.register_next_step_handler(bot.send_message(m.chat.id, "📩 الكود:"), add_3, phone, h, s)

def add_3(m, p, h, s):
    cl = TelegramClient(StringSession(s), MY_API_ID, MY_API_HASH)
    async def log(): await cl.connect(); await cl.sign_in(p, m.text, phone_code_hash=h); return cl.session.save()
    fs = asyncio.run(log())
    db_run("INSERT INTO accounts (user_id, session, phone) VALUES (?, ?, ?)", (m.chat.id, fs, p))
    bot.send_message(m.chat.id, "✅ تم!")

bot.infinity_polling()
