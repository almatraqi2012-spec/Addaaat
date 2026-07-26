import logging
import os
import socks
import random
import re
import threading
import time
import requests
from supabase import Client, create_client
import telebot
from telebot import types
from telethon import TelegramClient, errors
from telethon import types as tl_types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "7757013532:AAG74ogwnwZtsQ9bU236Q-Xq4mpmhy5sl6g"
MY_API_ID = int(os.environ.get("API_ID", 21349867))
MY_API_HASH = os.environ.get("API_HASH", "7ced3ee4c80117bd5138410811b91f9f")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 6016547718))

OXAPAY_KEY = os.environ.get("OXAPAY_KEY", "CE8H0F-ISXBD2-RXHALY-KZXUZU")
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.05
REFERRAL_GIFT = 0.007

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}
telebot.apihelper.CONNECT_TIMEOUT = 30
telebot.apihelper.READ_TIMEOUT = 60

# ================= [ ☁️ الاتصال بـ Supabase ] ================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("⚠️ خطأ: متغيرات Supabase غير موجودة في الـ Secrets!")
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ================= [ 💳 إدارة الأرصدة والمستخدمين ] ================
def get_balance(uid):
    if not supabase:
        return 0.0
    try:
        numeric_id = int(uid)
        res = (
            supabase.table("users")
            .select("balance")
            .eq("id", numeric_id)
            .execute()
        )

        if res.data and len(res.data) > 0:
            return round(float(res.data[0]["balance"]), 2)

        supabase.table("users").upsert(
            {"id": numeric_id, "balance": 0.0}
        ).execute()
        return 0.0
    except Exception as e:
        logging.error(f"Error in get_balance: {e}")
        return 0.0


def update_balance(uid, amt):
    if not supabase:
        return
    try:
        numeric_id = int(uid)
        current_bal = get_balance(numeric_id)
        new_bal = round(current_bal + float(amt), 2)

        supabase.table("users").upsert(
            {"id": numeric_id, "balance": new_bal}
        ).execute()
    except Exception as e:
        logging.error(f"Error in update_balance: {e}")


# ================= [ 📱 إدارة الجلسات والحسابات ] ================
def save_account_db(user_id, phone_number, session_string):
    if not supabase:
        return
    try:
        supabase.table("telegram_accounts").upsert({
            "user_id": int(user_id),
            "phone": str(phone_number).strip(),
            "session_string": str(session_string).strip(),
            "status": "active",
        }).execute()
    except Exception as e:
        logging.error(f"Error in save_account_db: {e}")


def get_user_accounts(user_id):
    if not supabase:
        return []
    try:
        res = (
            supabase.table("telegram_accounts")
            .select("phone, session_string")
            .eq("user_id", int(user_id))
            .eq("status", "active")
            .execute()
        )
        return res.data if res.data else []
    except Exception as e:
        logging.error(f"Error in get_user_accounts: {e}")
        return []


def delete_account_db(user_id, phone):
    if not supabase:
        return
    try:
        supabase.table("telegram_accounts").delete().eq(
            "user_id", int(user_id)
        ).eq("phone", str(phone)).execute()
    except Exception as e:
        logging.error(f"Error in delete_account_db: {e}")


# ================= [ 🧠 إدارة الذاكرة لمنع التكرار ] ================
def save_user_memory(target_id):
    if not supabase:
        return
    try:
        supabase.table("memory").upsert(
            {"target_id": str(target_id)}
        ).execute()
    except Exception as e:
        logging.error(f"Error in save_user_memory: {e}")


def get_memory():
    if not supabase:
        return []
    try:
        res = supabase.table("memory").select("target_id").execute()
        return [row["target_id"] for row in res.data] if res.data else []
    except Exception as e:
        logging.error(f"Error in get_memory: {e}")
        return []


# ================= [ 🔍 خوارزمية جلب الكيانات الذكية ] ================
async def resolve_entity_safely(client, identifier):
    """جلب المجموعة أو العضو بالتراتب: آيدي -> يوزر -> اسم"""
    if not identifier:
        return None
    identifier_str = str(identifier).strip()

    # 1. جلب بالآيدي العددي
    if identifier_str.lstrip("-").isdigit():
        try:
            return await client.get_entity(int(identifier_str))
        except Exception:
            pass

    # 2. جلب باليوزر أو الرابط
    try:
        clean_user = identifier_str.split("/")[-1].replace("@", "")
        return await client.get_entity(clean_user)
    except Exception:
        pass

    # 3. جلب بالاسم من المحادثات المفتوحة
    try:
        async for dialog in client.iter_dialogs(limit=100):
            if (
                dialog.name and identifier_str.lower() in dialog.name.lower()
            ):
                return dialog.entity
    except Exception:
        pass

    return None


async def extract_users_from_message(message):
    """استخراج المعرفات من كاتب الرسالة ومن داخل نص الرسالة"""
    found = []

    # كاتب الرسالة
    if message.sender_id:
        found.append(message.sender_id)

    # الإشارات داخل النص
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, tl_types.MessageEntityMention):
                found.append(
                    message.text[entity.offset : entity.offset + entity.length]
                )
            elif isinstance(entity, tl_types.MessageEntityMentionName):
                found.append(entity.user_id)

    # التعبير النمطي للرموز واليوزرات داخل الرسالة
    if message.text:
        found.extend(re.findall(r"@[a-zA-Z0-9_]{5,32}", message.text))

    return list(set(found))


# ================= [ ⚔️ محرك سهم الشامل V73 ] ================
async def run_sahm_v73(army_accounts, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 **تفعيل رادار سهم الشامل... جاري بدء الإضافة.**")

    # تحميل الذاكرة لمنع التكرار نهائياً
    added_ids = set(get_memory())

    for acc in army_accounts:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER:
            break

        session_str = acc.get("session_string")
        phone = acc.get("phone")

        client = TelegramClient(
            StringSession(session_str),
            MY_API_ID,
            MY_API_HASH,
            proxy=(socks.SOCKS5, 'عنوان_البروكسي', المنفذ_Port, True, 'اسم_المستخدم', 'كلمة_المرور')
        )

        client = TelegramClient(
            StringSession(session_str), MY_API_ID, MY_API_HASH
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                continue

            # التعرف على المجموعة المصدر والهدف بكل الطرق (آيدي/يوزر/اسم/رموز)
            src_entity = await resolve_entity_safely(client, src)
            trg_entity = await resolve_entity_safely(client, trg)

            if not src_entity or not trg_entity:
                continue

            targets = []

            # استخراج الأعضاء والرسائل والنصوص
            async for m in client.iter_messages(src_entity, limit=3000):
                if len(targets) >= 100:
                    break

                candidates = await extract_users_from_message(m)

                for cand in candidates:
                    cand_str = str(cand)
                    if cand_str not in added_ids and cand not in [
                        x.id for x in targets
                    ]:
                        try:
                            u = await resolve_entity_safely(client, cand)
                            if isinstance(u, tl_types.User) and not u.bot:
                                targets.append(u)
                        except Exception:
                            continue

            count = 0
            for t in targets:
                if (
                    success >= total
                    or count >= 40
                    or get_balance(uid) < PRICE_PER_MEMBER
                ):
                    break
                try:
                    await client(InviteToChannelRequest(trg_entity, [t]))

                    save_user_memory(t.id)
                    added_ids.add(str(t.id))

                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1
                    count += 1
                    bot.send_message(
                        uid, f"➕ [{phone}] أضاف: `{t.first_name}`"
                    )
                    await asyncio.sleep(random.randint(20, 40))
                except errors.FloodWaitError:
                    break
                except Exception:
                    continue

            await client.disconnect()
        except Exception as e:
            logging.error(f"Error in client task: {e}")
            continue

    bot.send_message(
        uid,
        f"🏁 **اكتملت المهمة!**\n✅ الإضافة: `{success}`\n💰 الرصيد المتبقي: `{get_balance(uid)}$`",
    )


# ================= [ 📱 الواجهة ونظام الإحالة ] ================
@bot.message_handler(commands=["start"])
def start_main(m):
    uid = m.chat.id
    current_bal = get_balance(uid)

    params = m.text.split()
    if len(params) > 1 and params[1].isdigit():
        ref_id = int(params[1])
        if ref_id != uid:
            update_balance(ref_id, REFERRAL_GIFT)
            try:
                bot.send_message(
                    ref_id,
                    f"🎊 **بشارة!** دخل صديق برابطك، حصلت على `{REFERRAL_GIFT}$`.",
                )
            except Exception:
                pass

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("🚀 بدء السحب", "➡️ إضافة حساب للتليجرام")
    mk.add("💵 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "❌ حذف حساب", "🎁 كسب رصيد مجاني")
    if uid == ADMIN_ID:
        mk.add("💎 لوحة المالك")

    bot.send_message(
        uid,
        "🐲 **مرحباً بك في دراجون المطور!**\nاختر من القائمة أدناه للبدء:",
        reply_markup=mk,
    )


@bot.message_handler(func=lambda m: m.text == "🎁 كسب رصيد مجاني")
def referral_menu(m):
    ref_link = f"https://t.me/{bot.get_me().username}?start={m.chat.id}"
    bot.send_message(
        m.chat.id,
        f"🎁 **نظام الإحالات:**\n\nرابطك لربح `{REFERRAL_GIFT}$`:\n`{ref_link}`",
    )


# ================= [ 🚀 بدء السحب والإضافة ] ================
@bot.message_handler(
    func=lambda m: m.text in ["🚀 بدء السحب", "⚔️ بدء الأضافه"]
)
def start_attack_cmd(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيدك غير كافٍ للبدء.")

    army = get_user_accounts(m.chat.id)
    if not army:
        return bot.send_message(
            m.chat.id, "❌ لا توجد حسابات مضافة، أضف حساباً أولاً."
        )

    msg = bot.send_message(
        m.chat.id,
        "📡 **أرسل المصدر (آيدي، يوزر @، رابط، أو اسم المجموعة):**",
    )
    bot.register_next_step_handler(
        msg,
        lambda s: bot.register_next_step_handler(
            bot.send_message(
                m.chat.id,
                "🎯 **أرسل مجموعتك (آيدي، يوزر @، رابط، أو اسم المجموعة):**",
            ),
            lambda t: bot.register_next_step_handler(
                bot.send_message(m.chat.id, "🔢 **أدخل العدد المطلوب:**"),
                lambda n: threading.Thread(
                    target=lambda: asyncio.run(
                        run_sahm_v73(
                            army, s.text, t.text, int(n.text), m.chat.id
                        )
                    )
                ).start(),
            ),
        ),
    )


# ================= [ ➡️ إضافة حساب ] ================
@bot.message_handler(
    func=lambda m: m.text
    in ["➡️ إضافة حساب للتليجرام", "➕ إضافة حساب للجيش"]
)
def add_acc_start(m):
    msg = bot.send_message(
        m.chat.id,
        "📱 **أرسل الرقم المطلوب إضافته مع المفتاح الدولي (مثال: 967xxxxxxxx):**",
    )
    bot.register_next_step_handler(msg, process_phone)


def process_phone(m):
    ph = m.text.strip().replace("+", "").replace(" ", "")
    if not ph.isdigit():
        return bot.send_message(m.chat.id, "⚠️ أرقام فقط.")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH, loop=loop)

    async def get_c():
        await cl.connect()
        try:
            res = await cl.send_code_request(ph)
            sess_str = cl.session.save()
            return res.phone_code_hash, sess_str, "OK"
        except Exception as e:
            return str(e), None, "ERR"
        finally:
            await cl.disconnect()

    try:
        h, sess_str, status = loop.run_until_complete(get_c())
        if status == "OK":
            msg = bot.send_message(m.chat.id, "📩 **أرسل الكود:**")
            bot.register_next_step_handler(
                msg, process_code, ph, h, sess_str
            )
        else:
            bot.send_message(m.chat.id, f"❌ {h}")
    except Exception as e:
        bot.send_message(m.chat.id, f"⚠️ عطل: {str(e)}")
    finally:
        loop.close()


def process_code(m, ph, h, sess_str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cl = TelegramClient(
        StringSession(sess_str), MY_API_ID, MY_API_HASH, loop=loop
    )

    async def sign():
        await cl.connect()
        try:
            await cl.sign_in(ph, m.text, phone_code_hash=h)
            final_session = cl.session.save()
            return "OK", final_session
        except errors.SessionPasswordNeededError:
            return "2FA", cl.session.save()
        except Exception as e:
            return str(e), None
        finally:
            await cl.disconnect()

    try:
        res, final_sess = loop.run_until_complete(sign())
        if res == "OK":
            save_account_db(m.chat.id, ph, final_sess)
            bot.send_message(m.chat.id, "✅ **تم الربط وحفظ الحساب!**")
        elif res == "2FA":
            msg = bot.send_message(m.chat.id, "🔐 **أرسل كلمة سر 2FA:**")
            bot.register_next_step_handler(
                msg, process_password, ph, final_sess
            )
        else:
            bot.send_message(m.chat.id, f"❌ {res}")
    finally:
        loop.close()


def process_password(m, ph, sess_str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cl = TelegramClient(
        StringSession(sess_str), MY_API_ID, MY_API_HASH, loop=loop
    )

    async def sign_p():
        await cl.connect()
        try:
            await cl.sign_in(password=m.text)
            return "OK", cl.session.save()
        except Exception as e:
            return str(e), None
        finally:
            await cl.disconnect()

    try:
        res, final_sess = loop.run_until_complete(sign_p())
        if res == "OK":
            save_account_db(m.chat.id, ph, final_sess)
            bot.send_message(m.chat.id, "✅ **تم الربط وحفظ الحساب!**")
        else:
            bot.send_message(m.chat.id, f"❌ خطأ: {res}")
    finally:
        loop.close()


# ================= [ 💵 الشحن والمحفظة ] ================
@bot.message_handler(
    func=lambda m: m.text in ["💵 شحن الرصيد", "💰 شحن الرصيد"]
)
def payment_menu(m):
    user_states[m.chat.id] = None
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton(
            "⚡ شحن Oxapay (آلي)", callback_data="pay_oxa"
        ),
        types.InlineKeyboardButton(
            "💳 شحن محفظة (يدوي)", callback_data="pay_man"
        ),
    )
    bot.send_message(
        m.chat.id, f"💰 رصيدك الحالي: `{get_balance(m.chat.id)}$`", reply_markup=mk
    )


@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_call(c):
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass
    msg = bot.send_message(c.message.chat.id, "💵 **أدخل المبلغ ($):**")
    bot.register_next_step_handler(msg, process_oxa)


def process_oxa(m):
    try:
        amt = float(m.text)
        res = requests.post(
            "https://api.oxapay.com/merchants/request",
            json={"merchant": OXAPAY_KEY, "amount": amt, "currency": "USD"},
        ).json()
        if res.get("payLink"):
            mk = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("دفع 🔗", url=res["payLink"])
            )
            bot.send_message(m.chat.id, f"✅ فاتورة {amt}$:", reply_markup=mk)
    except Exception:
        bot.send_message(m.chat.id, "⚠️ رقم غير صحيح.")


@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def man_call(c):
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(
        c.message.chat.id, f"💳 المحفظة:\n`{MY_WALLET}`\n📸 أرسل الإيصال."
    )


@bot.message_handler(content_types=["photo"])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup(row_width=3)
        mk.add(
            types.InlineKeyboardButton(
                "✅ 5$", callback_data=f"set_5_{m.chat.id}"
            ),
            types.InlineKeyboardButton(
                "✅ 10$", callback_data=f"set_10_{m.chat.id}"
            ),
            types.InlineKeyboardButton(
                "✅ 50$", callback_data=f"set_50_{m.chat.id}"
            ),
        )
        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"📩 إيصال من `{m.chat.id}`",
            reply_markup=mk,
        )
        bot.reply_to(m, "⏳ جارٍ المراجعة...")
        user_states[m.chat.id] = None


@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass
    _, amt, uid = c.data.split("_")
    update_balance(int(uid), float(amt))
    bot.send_message(int(uid), f"🎉 تم شحن {amt}$!")
    bot.edit_message_caption(
        f"✅ تم تفعيل {amt}$ للحساب {uid}",
        c.message.chat.id,
        c.message.message_id,
    )


# ================= [ ❌ حذف حساب ] ================
@bot.message_handler(func=lambda m: m.text in ["❌ حذف حساب", "🗑️ حذف حساب"])
def delete_session_menu(m):
    uid = m.chat.id
    try:
        user_sessions = get_user_accounts(uid)

        if not user_sessions:
            return bot.send_message(
                uid, "❌ **لا توجد لديك أي حسابات مضافة حالياً.**"
            )

        mk = types.InlineKeyboardMarkup(row_width=1)
        for sess in user_sessions:
            phone = sess.get("phone")
            mk.add(
                types.InlineKeyboardButton(
                    f"❌ حذف الرقم: +{phone}",
                    callback_data=f"delsess_{phone}",
                )
            )

        bot.send_message(
            uid,
            "📱 **اختر الرقم الذي تريد حذفه:**",
            reply_markup=mk,
        )
    except Exception as e:
        logging.error(f"Error in delete_session_menu: {e}")
        bot.send_message(uid, "⚠️ حدث خطأ أثناء جلب الحسابات.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("delsess_"))
def process_delete_session(c):
    try:
        bot.answer_callback_query(c.id, "جاري الحذف...")
    except Exception:
        pass

    uid = c.message.chat.id
    phone = c.data.split("_")[1]

    try:
        delete_account_db(uid, phone)
        bot.edit_message_text(
            f"✅ **تم حذف الرقم `+{phone}` بنجاح.**\nيمكنك الآن إعادة إضافته عبر (➡️ إضافة حساب للتليجرام).",
            c.message.chat.id,
            c.message.message_id,
        )
    except Exception as e:
        logging.error(f"Error in process_delete_session: {e}")
        bot.send_message(uid, "⚠️ حدث خطأ أثناء محاولة الحذف.")


# ================= [ 📊 الإحصائيات والمعلومات ] ================
@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats_all(m):
    accs = get_user_accounts(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"📊 **إحصائياتك:**\n📱 الجيش: `{len(accs)}`\n💰 الرصيد: `{get_balance(m.chat.id)}$`",
    )


@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    accs = get_user_accounts(m.chat.id)
    bot.send_message(
        m.chat.id,
        f"👤 **حسابك:**\n💰 الرصيد: `{get_balance(m.chat.id)}$`\n📱 الجيش: `{len(accs)}`",
    )


if __name__ == "__main__":
    print("🐲 دراجون V73 ينطلق الآن بنجاح...")
    bot.infinity_polling(
        skip_pending=True, timeout=60, long_polling_timeout=60
    )
