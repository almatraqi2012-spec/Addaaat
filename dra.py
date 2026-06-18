# ==========================================================
# 🐉 دراغون المحرك V73 - نسخة الأعضاء الأقوياء 🇩🇪🇵🇸
# الحقوق محفوظة للمطور الرسمي | نظام شهم الجبار
# الاستضافة المستقرة للبوت سحابياً - بوابة Supabase الأقوى
# ==========================================================
# --- المكتبات التي يحتاجها البوت ---
import random
import os
import logging
import threading
import time
import asyncio
import requests
from supabase import create_client, Client
from flask import Flask

import telebot
from telebot import types
from telethon import TelegramClient, functions, types as tl_types, errors
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest

# --- ⚠️ المكتبات الإضافية ---
from datetime import datetime, timedelta
import json
from telethon.tl.functions.messages import (
    GetMessagesReactionsRequest,
    GetHistoryRequest,
)
from telethon.tl.functions.users import GetFullUserRequest

# ================= [ ⚙️ الإعدادات المركزية ] =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_API_ID = 21349687
MY_API_HASH = "7ced3ee4c80117bd5138410811b91f9f"
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTnviYpsA"
PRICE_PER_MEMBER = 0.007
REFERRAL_GIFT = 0.05

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 🌐 قاعدة البيانات والأرشفة - Supabase السحابية ] =================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("⚠️ خطأ: متغيرات Supabase غير موجودة في الـ Secrets!")
    supabase_client = None
else:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- 🏦 الدوال السحابية لبوت دراجون ---
def get_balance(uid):
    if not supabase_client:
        return 0.0
    try:
        response = (
            supabase_client.table("users_dragon")
            .select("balance")
            .eq("uid", int(uid))
            .execute()
        )
        if response.data and len(response.data) > 0:
            return round(float(response.data[0]["balance"]), 3)
        else:
            supabase_client.table("users_dragon").insert(
                {"uid": int(uid), "balance": 0.0}
            ).execute()
            return 0.0
    except Exception as e:
        logging.error(f"Error in get_balance: {e}")
        return 0.0


def update_balance(uid, amt):
    if not supabase_client:
        return
    try:
        current_balance = get_balance(uid)
        new_balance = round(current_balance + float(amt), 3)
        supabase_client.table("users_dragon").update({"balance": new_balance}).eq(
            "uid", int(uid)
        ).execute()
        logging.info(f"✅ تم تحديث الرصيد في السحاب للمستخدم {uid} إلى {new_balance}")
    except Exception as e:
        logging.error(f"Error in update_balance: {e}")


def save_account_db(user_id, session_name, phone):
    if not supabase_client:
        return
    try:
        supabase_client.table("accounts_dragon").upsert(
            {
                "session_name": str(session_name),
                "user_id": int(user_id),
                "phone": str(phone),
                "status": "active",
            }
        ).execute()
    except Exception as e:
        logging.error(f"Error in save_account_db: {e}")


def save_user_memory(user_id):
    if not supabase_client:
        return
    try:
        supabase_client.table("memory_dragon").upsert(
            {"target_id": str(user_id)}
        ).execute()
    except Exception as e:
        logging.error(f"Error in save_user_memory: {e}")


def get_memory():
    if not supabase_client:
        return []
    try:
        response = supabase_client.table("memory_dragon").select("target_id").execute()
        return [row["target_id"] for row in response.data] if response.data else []
    except Exception as e:
        logging.error(f"Error in get_memory: {e}")
        return []


# دالة مساعدة معزولة لإرسال رسائل التحديثات والتقارير بأمان
def safe_send(uid, text):
    def run():
        try:
            bot.send_message(uid, text, parse_mode="Markdown")
        except:
            pass

    threading.Thread(target=run).start()


# ================= [ 🚀 محرك الرادار المطور الأقوى V74 - مضاد السحب المستحيل ] =================
async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(uid, "🚀 تفعيل رادار سهم... جاري اختراق المصدر.")
    for session_file in army:
        if success >= total or get_balance(uid) < PRICE_PER_MEMBER:
            break
        added_list = get_memory()
        client = TelegramClient(
            session_file.replace(".session", ""), MY_API_ID, MY_API_HASH
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                continue
            targets = []
            async for m in client.iter_messages(src, limit=5000):
                if len(targets) >= 100:
                    break
                if m.sender_id and str(m.sender_id) not in added_list:
                    u = await m.get_sender()
                    if isinstance(u, tl_types.User) and not u.bot:
                        if u.id not in [x.id for x in targets]:
                            targets.append(u)
            count = 0
            for t in targets:
                if (
                    success >= total
                    or count >= 40
                    or get_balance(uid) < PRICE_PER_MEMBER
                ):
                    break
                try:
                    await client(InviteToChannelRequest(trg, [t]))
                    save_user_memory(t.id)
                    update_balance(uid, -PRICE_PER_MEMBER)
                    success += 1
                    count += 1
                    bot.send_message(
                        uid, f"➕ [{session_file}] أضاف:\n\n{t.first_name}\n\n"
                    )
                    await asyncio.sleep(random.randint(30, 60))
                except errors.FloodWaitError:
                    break
                except:
                    continue
            await client.disconnect()
        except:
            continue
    bot.send_message(
        uid,
        f"🏁 اكتملت المهمة!\n✅ الإضافة:\n\n{success}\n\n\n💰 المتبقي:\n\n{get_balance(uid)}$\n\n",
    )


# ================= [ 🎫 الأوامر الأساسية ولوحة التحكم ] =================
@bot.message_handler(commands=["start"])
def start_main(m):
    uid = m.chat.id
    get_balance(uid)
    params = m.text.split()
    if len(params) > 1 and params[1].isdigit():
        ref_id = int(params[1])
        if ref_id != uid:
            update_balance(ref_id, REFERRAL_GIFT)
            try:
                bot.send_message(
                    ref_id,
                    f"🎉 **مبارك!** دخل عضو جديد برابطك، كسبت `{REFERRAL_GIFT}`$.",
                )
            except:
                pass

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("🚀 بدء السحب", "➡️ إضافة حساب للتليجرام")
    mk.add("💵 شحن الرصيد", "👤 حسابي")
    mk.add("📊 الإحصائيات", "❌ حذف حساب", "🎁 كسب رصيد مجاني")
    if uid == ADMIN_ID:
        mk.add("⚙️ لوحة الأدمن")
    bot.send_message(
        uid,
        "🐉 **مرحباً بك في بوت دراغون المحرك V73**\nأهلاً بك في أقوى منصة كاشفة وساحبة للأعضاء الحقيقيين والمتفاعلين.. سيزيد ترتيب مجموعتك الآن .",
        reply_markup=mk,
    )


@bot.message_handler(func=lambda m: m.text == "🎁 كسب رصيد مجاني")
def referral_menu(m):
    ref_link = f"https://t.me/{bot.get_me().username}?start={m.chat.id}"
    bot.send_message(
        m.chat.id,
        f"🎁 **نظام الإحالة كالتالي:**\nانشر رابطك واكسب رصيد مجاني عن كل مستخدم يقيد حساباته:\n`{ref_link}`",
    )


# ================= [ 💳 شحن الرصيد والمدفوعات ] =================
@bot.message_handler(func=lambda m: m.text == "💵 شحن الرصيد")
def payment_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🔺 شحن آلي (Oxapay)", callback_data="pay_oxa"),
        types.InlineKeyboardButton("💳 شحن يدوي (إيداع)", callback_data="pay_man"),
    )
    bot.send_message(
        m.chat.id, f"💵 رصيدك الحالي هو: `{get_balance(m.chat.id)}`$", reply_markup=mk
    )


# -------------- [ قسم الشحن الآلي Oxapay ] --------------
@bot.callback_query_handler(func=lambda c: c.data == "pay_oxa")
def oxa_call(c):
    msg = bot.send_message(
        c.message.chat.id, "💵 **أدخل القيمة المطلوبة بالدولار ($):**"
    )
    bot.register_next_step_handler(msg, process_oxa)


def process_oxa(m):
    if not m.text:
        return
    try:
        amt = float(m.text.strip())
        payload = {
            "merchant": OXAPAY_KEY,
            "amount": amt,
            "currency": "USD",
            "description": str(m.chat.id),
        }
        res = requests.post(
            "https://api.oxapay.com/merchants/request", json=payload
        ).json()

        track_id = res.get("trackId")
        pay_url = res.get("payLink")

        if pay_url:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("💳 اضغط هنا للدفع الآمن", url=pay_url)
            )
            bot.send_message(
                m.chat.id,
                f"⏳ جاري تجهيز فاتورة بقيمة {amt}$ (دفع تلقائي):\n🔗 سيتم فحص دفعك دورياً بمجرد إرسال الدفع.",
                reply_markup=markup,
            )
            threading.Thread(
                target=auto_check_payment, args=(m.chat.id, track_id, amt)
            ).start()
        else:
            bot.send_message(m.chat.id, "❌ عذراً، خطأ في اتخاذ رابط الدفع.")
    except:
        bot.send_message(m.chat.id, "⚠️ يرجى إرسال المبلغ بالأرقام فقط.")


def auto_check_payment(chat_id, track_id, amount):
    for _ in range(60):
        time.sleep(60)
        try:
            check = requests.post(
                "https://api.oxapay.com/merchants/inquiry",
                json={"merchant": OXAPAY_KEY, "trackId": track_id},
            ).json()
            if (
                check.get("status") == "Paid"
                or check.get("result") == "100"
                or check.get("result") == 100
            ):
                update_balance(chat_id, amount)
                bot.send_message(
                    chat_id,
                    f"🎉 **مبارك!** تم استقبال الدفع التلقائي للمبلغ.\n💵 تم إضافة `{amount}$` إلى رصيدك بنجاح.",
                )
                break
        except:
            continue


# -------------- [ قسم الشحن اليدوي (الإيداع) ] --------------
@bot.callback_query_handler(func=lambda c: c.data == "pay_man")
def man_call(c):
    user_states[c.message.chat.id] = "waiting_receipt"
    bot.send_message(
        c.message.chat.id,
        f"🏢 **الشحن اليدوي:**\n\nالمحفظة USDT TRC20:\n`{MY_WALLET}`\n\n📷 أرسل صورة الوصل أو لقطة الشاشة بعد الإيداع.",
    )


@bot.message_handler(content_types=["photo"])
def handle_receipt(m):
    if user_states.get(m.chat.id) == "waiting_receipt":
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ 5$", callback_data=f"set_5_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 10$", callback_data=f"set_10_{m.chat.id}"),
            types.InlineKeyboardButton("✅ 50$", callback_data=f"set_50_{m.chat.id}"),
        )
        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"📩 وصل شحن جديد\n👤 للمستثمر: `{m.chat.id}`",
            reply_markup=mk,
        )
        bot.reply_to(
            m, "⏳ تم استلام إيصال الدفع، جاري مراجعته والتحقق منه من قبل الإدارة..."
        )
        user_states[m.chat.id] = None


@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_confirm(c):
    try:
        _, amt, uid = c.data.split("_")
        # تم تصحيح شحن سوباباس وتحديث رصيد المشترك الفعلي بنجاح
        update_balance(int(uid), float(amt))
        bot.send_message(
            int(uid), f"🎉 **مبارك!** تم قبول إيصالك وشحن رصيدك بمبلغ {amt}$ بنجاح."
        )
        bot.edit_message_caption(
            f"✅ تم قبول الشحن بنجاح للمستخدم {uid} بمبلغ ({amt}$)",
            c.message.chat.id,
            c.message.message_id,
        )
    except Exception as e:
        bot.answer_callback_query(c.id, f"❌ حدث خلل في العملية: {e}")


# ================= [ ⚙️ تشغيل وربط الحسابات ] =================
@bot.message_handler(func=lambda m: m.text == "➡️ إضافة حساب للتليجرام")
def add_acc_start(m):
    msg = bot.send_message(m.chat.id, "📱 **أرسل رقم الهاتف مع مفتاح الدولة:**")
    bot.register_next_step_handler(msg, process_phone)


def process_phone(m):
    ph = m.text.strip().replace("+", "").replace(" ", "")
    if not ph.isdigit():
        return bot.send_message(m.chat.id, "⚠️ الرقم غير صحيح.")
    sess = f"sess_{m.chat.id}_{ph}"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)

    async def get_c():
        await cl.connect()
        try:
            res = await cl.send_code_request(ph)
            return res.phone_code_hash, "OK"
        except Exception as e:
            return str(e), "ERR"
        finally:
            await cl.disconnect()

    try:
        h, status = loop.run_until_complete(get_c())
        if status == "OK":
            msg = bot.send_message(m.chat.id, "📩 **أرسل كود التحقق:**")
            bot.register_next_step_handler(msg, process_code, ph, h, sess)
        else:
            bot.send_message(m.chat.id, f"❌ {h}")
    except Exception as e:
        bot.send_message(m.chat.id, f"⚠️ عذراً: {str(e)}")
    finally:
        loop.close()


def process_code(m, ph, h, sess):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)

    async def sign():
        await cl.connect()
        try:
            await cl.sign_in(ph, m.text, phone_code_hash=h)
            return "OK"
        except errors.SessionPasswordNeededError:
            return "2FA"
        except Exception as e:
            return str(e)
        finally:
            await cl.disconnect()

    try:
        res = loop.run_until_complete(sign())
        if res == "OK":
            bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح!**")
            save_account_db(m.chat.id, sess, ph)
        elif res == "2FA":
            msg = bot.send_message(m.chat.id, "🔒 **أرسل رمز التحقق بخطوتين:**")
            bot.register_next_step_handler(msg, process_password, sess, ph)
        else:
            bot.send_message(m.chat.id, f"❌ {res}")
    finally:
        loop.close()


def process_password(m, sess, ph):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH, loop=loop)

    async def sign_p():
        await cl.connect()
        try:
            await cl.sign_in(password=m.text)
            return "OK"
        except Exception as e:
            return str(e)
        finally:
            await cl.disconnect()

    try:
        if loop.run_until_complete(sign_p()) == "OK":
            bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح!**")
            save_account_db(m.chat.id, sess, ph)
        else:
            bot.send_message(m.chat.id, "❌ خطأ في رمز التحقق بخطوتين.")
    finally:
        loop.close()


# ================= [ ⚙️ العرض وحذف الحسابات المتواجدة ] =================
@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats_all(m):
    army = [
        f
        for f in os.listdir(".")
        if f.startswith(f"sess_{m.chat.id}_") and f.endswith(".session")
    ]
    bot.send_message(
        m.chat.id,
        f"📊 **إحصائياتك:**\n📱 الحسابات: `{len(army)}`\n💵 الرصيد المتاح: `{get_balance(m.chat.id)}`$ ",
    )


@bot.message_handler(func=lambda m: m.text == "❌ حذف حساب")
def delete_acc_menu(m):
    army = [
        f
        for f in os.listdir(".")
        if f.startswith(f"sess_{m.chat.id}_") and f.endswith(".session")
    ]
    if not army:
        return bot.send_message(m.chat.id, "❌ لا توجد حسابات مربوطة.")
    mk = types.InlineKeyboardMarkup()
    for s in army:
        num = s.split("_")[-1].replace(".session", "")
        mk.add(types.InlineKeyboardButton(f"❌ حذف: {num}", callback_data=f"rm_{s}"))
    bot.send_message(m.chat.id, "اختر الحساب للمسح نهائياً:", reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def finalize_delete(c):
    fname = c.data.replace("rm_", "")
    try:
        if os.path.exists(fname):
            os.remove(fname)
        if supabase_client:
            supabase_client.table("accounts_dragon").delete().eq(
                "session_name", fname
            ).execute()
        bot.answer_callback_query(c.id, "✅ تم الحذف بنجاح")
        bot.edit_message_text(
            f"✅ تم إلغاء ربط الحساب وحذفه `{fname.split('_')[-1]}`.",
            c.message.chat.id,
            c.message.message_id,
        )
    except Exception as e:
        bot.answer_callback_query(c.id, f"❌ حدث خلل: {str(e)}")


# =====================================================================
# 🚀 محرك تشغيل السحب المطور - مدموج بالكامل ومضاد للتجمد الصامت
# =====================================================================
def start_radar_thread(army, src, trg, num, uid):
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_dragon_force_v74(army, src, trg, num, uid))
        loop.close()
    except Exception as e:
        print(f"❌ خطأ في ثريد الرادار: {e}", flush=True)


@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الأضافه")
def start_attack_cmd(m):
    if get_balance(m.chat.id) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيد منخفض.")
    army = [
        f
        for f in os.listdir(".")
        if f.startswith(f"sess_{m.chat.id}_") and f.endswith(".session")
    ]
    if not army:
        return bot.send_message(m.chat.id, "❌ أضف حسابات أولاً.")
    msg = bot.send_message(m.chat.id, "📡 يوزر المصدر (بدون @):")
    bot.register_next_step_handler(
        msg,
        lambda s: bot.register_next_step_handler(
            bot.send_message(m.chat.id, "🎯 يوزر مجموعتك (بدون @):"),
            lambda t: bot.register_next_step_handler(
                bot.send_message(m.chat.id, "🔢 العدد المطلوب:"),
                lambda n: threading.Thread(
                    target=lambda: asyncio.run(
                        run_sahm_v73(army, s.text, t.text, int(n.text), m.chat.id)
                    )
                ).start(),
            ),
        ),
    )  # -------------- [ قسم حسابي ومعلومات المستثمر ] --------------


@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    bal = get_balance(m.chat.id)
    army_count = len(
        [
            f
            for f in os.listdir(".")
            if f.startswith(f"sess_{m.chat.id}_") and f.endswith(".session")
        ]
    )
    bot.send_message(
        m.chat.id,
        f"👤 **حسابك:**\n💵 الرصيد: `{bal}$` \n📦 الحسابات النشطة: `{army_count}`",
    )


# ================= [ 🌐 خادم ويب مصغر لإبقاء البوت حياً ] =================
app_web = Flask(__name__)


@app_web.route("/")
def health_check():
    return "Dragon V73 Pro is Running Safely!", 200


def run_server():
    PORT = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    print("🛰️ جاري تشغيل دراغون V73 ينطلق بنجاح الآن..")
    # تشغيل خادم الويب بدون تجميد المنفذ أو البوت
    threading.Thread(target=run_server, daemon=True).start()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
