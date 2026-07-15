# =======================================================
# 🐉 دراغون المحرك V73 - نسخة الأعضاء الأقوياء 🇩🇪🇵🇸
# الحقوق محفوظة للمطور الرسمي | نظام شهم الجبار
# الاستضافة المستقرة للبوت سحابياً - بوابة Supabase الأقوى
# ==========================================================
import asyncio
from datetime import datetime, timedelta
from flask import Flask
import json
import logging
import os
import random
import requests
import telebot
from telebot import types
import threading
import time
from supabase import create_client, Client
from telethon import TelegramClient, errors, functions
from telethon import types as tl_types
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import (
    GetHistoryRequest,
    GetMessagesReactionsRequest,
)
from telethon.tl.functions.users import GetFullUserRequest

# ================= [ ⚙️ الإعدادات المركزية ] =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MY_API_ID = 21349867
MY_API_HASH = "7ced3ee4c80117bd5138410811b91f9f"
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTnviYpsA"
PRICE_PER_MEMBER = 0.007
REFERRAL_GIFT = 0.05

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
user_states = {}

# ================= [ 🌐 قاعدة البيانات والأرشفة - Supabase ] =================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("⚠️ خطأ: متغيرات Supabase غير موجودة في الـ Secrets!")
    supabase_client = None
else:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_balance(user_id):
    if not supabase_client:
        return 0.0
    try:
        # البحث بناءً على العمود 'id' أو 'username'
        # تأكد من استبدال 'id' بـ 'username' إذا كنت تربط بالاسم
        response = (
            supabase_client.table("users")
            .select("balance")
            .eq("id", int(user_id)) 
            .execute()
        )
        if response.data and len(response.data) > 0:
            return round(float(response.data[0]["balance"]), 3)
        return 0.0
    except Exception as e:
        logging.error(f"Error in get_balance: {e}")
        return 0.0

def update_balance(user_id, amt):
    if not supabase_client:
        return
    try:
        current_balance = get_balance(user_id)
        new_balance = round(current_balance + float(amt), 3)
        supabase_client.table("users").update({"balance": new_balance}).eq(
            "id", int(user_id)
        ).execute()
        logging.info(f"✅ تم تحديث الرصيد للمستخدم {user_id} إلى {new_balance}")
    except Exception as e:
        logging.error(f"Error in update_balance: {e}")
        
def save_account_db(user_id, session_string):
    if not supabase_client:
        return
    try:
        supabase_client.table("telegram_accounts").upsert(
            {
                "user_id": int(user_id),
                "session_string": str(session_string),
                "status": "active"
            }
        ).execute()
    except Exception as e:
        logging.error(f"Error in save_account_db: {e}")

def get_memory():
    if not supabase_client:
        return []
    try:
        # ملاحظة: إذا كان جدول الذاكرة لا يزال يحمل اسم memory_dragon احتفظ به كما هو
        response = supabase_client.table("memory_dragon").select("target_id").execute()
        return [row["target_id"] for row in response.data] if response.data else []
    except Exception as e:
        logging.error(f"Error in get_memory: {e}")
        return []

def safe_send(uid, text):
    def run():
        try:
            bot.send_message(uid, text, parse_mode="Markdown")
        except:
            pass
    import threading
    threading.Thread(target=run).start()
# ================= [ 🚀 محرك الرادار المطور والأمن V74 ] =================
async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(
        uid, "🚀 **تم تفعيل الرادار بنجاح!**\nجاري تجميع الضحايا وفحص الحسابات..."
    )

    # 1. جلب البيانات الحالية مرة واحدة لتخفيف الضغط على السيرفر
    added_list = get_memory()
    current_balance = get_balance(uid)

    if current_balance < PRICE_PER_MEMBER:
        bot.send_message(uid, "❌ رصيدك غير كافي لبدء العملية.")
        return

    # 2. استخراج قائمة مستهدفة موحدة من الأعضاء المتفاعلين لتفادي تكرار الحظر
    targets = []
    collector_scout = army[0]  # الحساب الأول يتولى مهمة كشف الجواسيس فقط
    client_scout = TelegramClient(
        collector_scout.replace(".session", ""), MY_API_ID, MY_API_HASH
    )

    try:
        await client_scout.connect()
        if await client_scout.is_user_authorized():
            async for m in client_scout.iter_messages(src, limit=3000):
                if len(targets) >= total * 2:  # جمع ضعف العدد لضمان التصفية
                    break
                if m.sender_id and str(m.sender_id) not in added_list:
                    try:
                        u = await m.get_sender()
                        if isinstance(u, tl_types.User) and not u.bot:
                            if u.id not in [x.id for x in targets]:
                                targets.append(u)
                    except:
                        continue
        await client_scout.disconnect()
    except Exception as e:
        bot.send_message(uid, f"⚠️ خطأ أثناء تجميع الأعضاء من المصدر: {e}")

    if not targets:
        bot.send_message(uid, "❌ لم يتم العثور على أعضاء متاحين للنقل أو المصدر محمي.")
        return

    bot.send_message(
        uid, f"🎯 تم تجميع `{len(targets)}` عضو متفاعل. جاري البدء في النقل..."
    )

    # 3. توزيع المهام على جيش الحسابات بالتناوب لمنع الحظر والتوقف
    target_index = 0
    for session_file in army:
        if success >= total or target_index >= len(targets):
            break

        client = TelegramClient(
            session_file.replace(".session", ""), MY_API_ID, MY_API_HASH
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                continue

            # انضمام الحساب للمجموعة المستهدفة أولاً إذا تطلب الأمر
            try:
                await client(JoinChannelRequest(trg))
            except:
                pass

            account_adds = 0
            while account_adds < 15 and success < total and target_index < len(targets):
                # فحص الرصيد محلياً
                if (success * PRICE_PER_MEMBER) >= current_balance:
                    bot.send_message(uid, "🛑 توقفت العملية بسبب نفاد الرصيد.")
                    break

                current_target = targets[target_index]
                target_index += 1

                try:
                    await client(InviteToChannelRequest(trg, [current_target]))
                    save_user_memory(current_target.id)
                    update_balance(uid, -PRICE_PER_MEMBER)

                    success += 1
                    account_adds += 1

                    bot.send_message(
                        uid,
                        f"➕ الحساب `[{session_file.split('_')[-1].replace('.session','')}]` أضاف بنجاح:\n👤 {current_target.first_name}",
                    )
                    # وقت انتظار آمن بين كل إضافة لمنع تعليق الحساب
                    await asyncio.sleep(random.randint(35, 65))

                except errors.FloodWaitError as e:
                    bot.send_message(
                        uid,
                        f"⏳ الحساب الحالي واجه حظر مؤقت لـ {e.seconds} ثانية، يتم الانتقال للحساب التالي...",
                    )
                    break
                except errors.UserPrivacyRestrictedError:
                    # المستخدم مفعل الخصوصية، نتخطاه فوراً دون تجميد
                    continue
                except Exception:
                    continue

            await client.disconnect()
        except Exception:
            continue

    bot.send_message(
        uid,
        f"🏁 **اكتملت المهمة بنجاح!**\n\n✅ إجمالي المضافين: `{success}`\n💰 رصيدك المتبقي الحالي: `{get_balance(uid)}`$",
    )


# دالة الوسيط لتشغيل الـ Async Loop داخل الـ Thread بشكل صحيح وآمن
def launch_radar_safely(army, src, trg, total, uid):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_sahm_v73(army, src, trg, total, uid))
        loop.close()
    except Exception as e:
        safe_send(uid, f"❌ حدث خلل أثناء معالجة عملية الإضافة: {str(e)}")


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
    if not m.text:
        return
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
    if not m.text:
        return
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
    if not m.text:
        return
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
# 🚀 تعديل التوجيه والتحكم في زر البدء (تم تصحيح المدخلات والـ Threads)
# =====================================================================
@bot.message_handler(func=lambda m: m.text in ["🚀 بدء السحب", "⚔️ بدء الأضافه"])
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

    msg = bot.send_message(m.chat.id, "📡 **أدخل يوزر المصدر (بدون @):**")
    bot.register_next_step_handler(msg, get_source_user, army)


def get_source_user(m, army):
    if not m.text:
        return
    # تنظيف المدخلات تلقائياً من الروابط ورموز الـ @
    source = m.text.strip().replace("@", "").split("/")[-1]
    msg = bot.send_message(m.chat.id, "🎯 **أدخل يوزر مجموعتك للـنقل إليها (بدون @):**")
    bot.register_next_step_handler(msg, get_target_group, army, source)


def get_target_group(m, army, source):
    if not m.text:
        return
    # تنظيف الرابط تلقائياً وتحويله لاسم مستخدم نقي قابل للإضافة
    target = m.text.strip().replace("@", "").split("/")[-1]
    msg = bot.send_message(m.chat.id, "🔢 **أدخل العدد الإجمالي المطلوب نقله:**")
    bot.register_next_step_handler(msg, start_radar_execution, army, source, target)


def start_radar_execution(m, army, source, target):
    if not m.text:
        return
    try:
        total_needed = int(m.text.strip())
        bot.send_message(m.chat.id, "⏳ جاري تحضير المحرك وإطلاق الحسابات...")

        # تشغيل السكربت عبر بيئة معزولة ونظيفة تمنع تعليق البوت الأساسي
        threading.Thread(
            target=launch_radar_safely,
            args=(army, source, target, total_needed, m.chat.id),
            daemon=True,
        ).start()
    except ValueError:
        bot.send_message(m.chat.id, "⚠️ خطأ: يرجى إدخال أرقام فقط للعدد المطلوب.")


# -------------- [ قسم حسابي ومعلومات المستثمر ] --------------
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
    # use_reloader=False ضروري جداً لمنع تشغيل السيرفر مرتين
    app_web.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🛰️ جاري تشغيل دراغون V73 ينطلق بنجاح الآن..")
    
    # 1. تشغيل السيرفر في الخلفية
    threading.Thread(target=run_server, daemon=True).start()
    
    # 2. تنظيف تليجرام من أي اتصالات معلقة قبل البدء (حل لخطأ 409)
    try:
        bot.remove_webhook()
    except:
        pass
        
    # 3. بدء البوت
    print("🚀 جاري الاتصال بتليجرام...")
    bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
