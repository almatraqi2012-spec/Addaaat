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
from telethon.sessions import StringSession
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
        # تحويل لـ int ليطابق حقل int8 في سوبابيس تماماً
        numeric_id = int(user_id)
        print(f"DEBUG: Checking balance for user_id (int8): {numeric_id}")
        
        response = supabase_client.table("users").select("balance").eq("id", numeric_id).execute()
        
        print(f"DEBUG: Database response: {response.data}")
        
        if response.data and len(response.data) > 0:
            return round(float(response.data[0]["balance"]), 3)
        
        # إذا لم يكن موجوداً، ننشئه كـ int8 برصيد صفر
        print(f"DEBUG: User {numeric_id} not found. Creating fresh profile...")
        supabase_client.table("users").upsert({"id": numeric_id, "balance": 0.0}).execute()
        return 0.0
    except Exception as e:
        print(f"DEBUG: Error in get_balance: {e}")
        return 0.0

def update_balance(user_id, amt):
    if not supabase_client:
        return
    try:
        numeric_id = int(user_id)
        current_balance = get_balance(numeric_id)
        new_balance = round(current_balance + float(amt), 3)
        
        # تحديث كـ int8 لضمان الحفظ الصحيح للرصيد
        supabase_client.table("users").upsert({"id": numeric_id, "balance": new_balance}).execute()
        logging.info(f"✅ تم تحديث الرصيد للمستخدم {numeric_id} إلى {new_balance}")
    except Exception as e:
        logging.error(f"Error in update_balance: {e}")
        
# تأكد أن دالة الحفظ تستقبل الـ session_string النقي
# دالة الحفظ المحدثة بالكامل لاستقبال الرقم والجلسة معاً
def save_account_db(user_id, phone_number, session_string):
    if not supabase_client:
        return
    try:
        numeric_id = int(user_id)
        supabase_client.table("telegram_accounts").upsert(
            {
                "user_id": numeric_id,
                "phone": str(phone_number).strip(),    # حفظ الرقم في عموده الصحيح
                "session_string": str(session_string), # الكود المشفر الطويل
                "status": "active"
            }
        ).execute()
        logging.info(f"✅ تم حفظ الحساب بنجاح في السوبابيس للمستخدم {numeric_id}")
    except Exception as e:
        logging.error(f"Error in save_account_db: {e}")
def get_memory():
    if not supabase_client:
        return []
    try:
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

# ================= [ 🐉 محرك دراجون الخارق بنظام الاقتحام والتحدي الشامل V76 Pro ] ================                                           
# ==============:
# ================= [ 🚀 محرك الرادار المطور بنظام التحدي والمداورة V75 ] =================
async def run_sahm_v73(army, src, trg, total, uid):
    success = 0
    bot.send_message(
        uid,
        "⚡ تم تفعيل المحرك الهجين (تحدي + مداورة حية) V75!\n⚙️ جاري قشط الأهداف وتجهيز رادارات الحسابات بالتوازي...",
    )

    # 1. جلب الرصيد والحد الأقصى المسموح به ماليًا
    current_balance = get_balance(uid)
    max_allowed_by_balance = int(current_balance // PRICE_PER_MEMBER)
    total_to_add = min(total, max_allowed_by_balance)

    if total_to_add <= 0:
        bot.send_message(uid, "❌ رصيدك غير كافي لنقل أي عضو.")
        return

    db_accounts = [s.strip() for s in army if s]
    if not db_accounts:
        bot.send_message(uid, "❌ لا توجد حسابات نشطة ممررة للمحرك!")
        return

    # جلب القائمة السوداء من سوبابيس لمرة واحدة في البداية لتسريع الفحص
    added_list = []
    if supabase_client:
        try:
            res = (
                supabase_client.table("memory_dragon")
                .select("target_id")
                .execute()
            )
            if res.data:
                added_list = [str(row["target_id"]) for row in res.data]
        except Exception as e:
            print(f"DEBUG Error fetching Supabase blacklist: {e}")

    # 2. هيكلة الحسابات: كل حساب سيحتفظ ببياناته وجلساته وأهدافه الـ 100 الخاصة به
    active_fleet = []

    bot.send_message(
        uid,
        "📡 المرحلة الأولى: بدء تشغيل الرادارات المستقلة لكل حساب لصيد الأعضاء...",
    )

    for idx, session_str in enumerate(db_accounts):
        client = TelegramClient(
            StringSession(session_str.strip()), MY_API_ID, MY_API_HASH
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                continue

            # الانضمام الذكي للجروب الهدف قبل البدء
            joined = await smart_join(client, trg)
            if not joined:
                await client.disconnect()
                continue

            # تجهيز معرف المصدر بشكل صحيح
            target_source = src
            if not target_source.startswith(
                "https://"
            ) and not target_source.startswith("@"):
                target_source = f"@{target_source}"

            # كسر حماية القشط بالانضمام للمصدر
            try:
                if "joinchat/" in target_source or "+" in target_source:
                    link_hash = target_source.split("/")[-1].replace("+", "")
                    await client(ImportChatInviteRequest(link_hash))
                else:
                    await client(JoinChannelRequest(target_source))
                await asyncio.sleep(1)
            except Exception:
                pass

            # 📡 رادار الحساب الفردي (تحدي قشط 5000 رسالة وصيد 100 هدف فريد)
            account_targets = []
            async for message in client.iter_messages(
                target_source, limit=5000
            ):
                if len(account_targets) >= 100:
                    break

                if (
                    message.sender_id
                    and str(message.sender_id) not in added_list
                ):
                    try:
                        sender = await message.get_sender()
                        if (
                            isinstance(sender, tl_types.User)
                            and not sender.bot
                            and not sender.deleted
                        ):
                            if sender.id not in [u.id for u in account_targets]:
                                account_targets.append(sender)
                    except Exception:
                        continue

            if account_targets:
                # إضافة الحساب لأسطول التشغيل الجاهز للمداورة
                active_fleet.append(
                    {
                        "index": idx + 1,
                        "client": client,
                        "targets": account_targets,
                        "adds_count": 0,
                        "target_idx": 0,
                        "is_flooded": False,
                    }
                )
                print(
                    f"✅ الحساب {idx + 1} جاهز ومعه {len(account_targets)} هدف."
                )
            else:
                await client.disconnect()

        except Exception as e:
            print(f"Error preparing account {idx + 1}: {e}")
            try:
                await client.disconnect()
            except Exception:
                pass

    if not active_fleet:
        bot.send_message(
            uid,
            "❌ فشل صيد أي أعضاء. المصدر محمي تماماً أو الحسابات معطلة.",
        )
        return

    bot.send_message(
        uid,
        f"🎯 اكتمل الصيد بنجاح! تم تجهيز {len(active_fleet)} حسابات.\n"
        f"⚡ جاري إطلاق طوفان النقل بنظام المداورة التناوبية الحية لحماية الحسابات...",
    )

    # 3. خوارزمية المداورة الحية (عضو لكل حساب بالتناوب الدائري المتواصل)
    while success < total_to_add:
        # تصفية الحسابات التي ما زالت تمتلك أهدافاً ولم تصل لحد الـ 15 ولم تصب بالفلود
        available_accounts = [
            acc
            for acc in active_fleet
            if acc["adds_count"] < 15
            and not acc["is_flooded"]
            and acc["target_idx"] < len(acc["targets"])
        ]

        if not available_accounts:
            break  # توقف عند انتهاء كل الحسابات من حدها أو أهدافها

        for acc in available_accounts:
            if success >= total_to_add:
                break

            client = acc["client"]
            user = acc["targets"][acc["target_idx"]]
            acc["target_idx"] += 1

            try:
                # تنفيذ أمر الإضافة المباشر للجروب الهدف
                await client(InviteToChannelRequest(trg, [user]))

                # حفظ في قاعدة بيانات سوبابيس فوراً لمنع التكرار اللحظي
                if supabase_client:
                    try:
                        supabase_client.table("memory_dragon").insert(
                            {"target_id": str(user.id)}
                        ).execute()
                    except Exception:
                        pass

                success += 1
                acc["adds_count"] += 1
                current_balance -= PRICE_PER_MEMBER

                bot.send_message(
                    uid,
                    f"➕ [{acc['index']}] أضاف بنجاح: {user.first_name or user.id}\n"
                    f"📊 المجموع الحالي: {success} عضو.",
                )

                # استراحة قصيرة بين الحسابات المداورة لتوزيع الضغط (أمان إضافي)
                await asyncio.sleep(random.randint(10, 25))

            except (
                errors.UserPrivacyRestrictedError,
                errors.UserAlreadyParticipantError,
            ):
                if supabase_client:
                    try:
                        supabase_client.table("memory_dragon").insert(
                            {"target_id": str(user.id)}
                        ).execute()
                    except Exception:
                        pass
                continue

            except errors.FloodWaitError:
                acc["is_flooded"] = True
                bot.send_message(
                    uid,
                    f"⏳ الحساب رقم {acc['index']} أصيب بالفلود. تم إخراجه من المداورة مؤقتاً.",
                )
                continue
            except Exception:
                continue

    # 4. تنظيف وإغلاق كافة الجلسات المفتوحة بشكل سليم
    for acc in active_fleet:
        try:
            await acc["client"].disconnect()
        except Exception:
            pass

    # 5. التحديث المالي النهائي للرصيد داخل سوبابيس
    if success > total:
        success = total

    if success > 0:
        total_deduction = success * PRICE_PER_MEMBER
        update_balance(uid, -total_deduction)

    bot.send_message(
        uid,
        f"🏁 اكتملت العملية بنجاح مذهل وبأعلى معايير الأمان!\n\n"
        f"✅ إجمالي المضافين: {success}\n"
        f"💰 رصيدك المتبقي الفعلي: {get_balance(uid)}$",
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
# ================= [ ⚙️ تشغيل وربط الحسابات المحدث بالسوبابيس ] =================
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
    
    # استخدام StringSession فارغ لاستخراج النص الصافي
    from telethon.sessions import StringSession
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH, loop=loop)

    async def sign():
        await cl.connect()
        try:
            await cl.sign_in(ph, m.text, phone_code_hash=h)
            # 🔥 استخراج الجلسة بصيغة النص الخام المتوافق 100%
            pure_string = str(cl.session.save())
            return "OK", pure_string
        except errors.SessionPasswordNeededError:
            return "2FA", None
        except Exception as e:
            return str(e), None
        finally:
            await cl.disconnect()

    try:
        res, session_str = loop.run_until_complete(sign())
        if res == "OK":
            bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح وتوليد الجلسة السحابية!**")
            save_account_db(m.chat.id, ph, session_str)
        elif res == "2FA":
            msg = bot.send_message(m.chat.id, "🔒 **أرسل رمز التحقق بخطوتين:**")
            bot.register_next_step_handler(msg, process_password, sess, ph)
        else:
            bot.send_message(m.chat.id, f"❌ {res}")
    except Exception as e:
        print(f"DEBUG Error in process_code: {e}")
    finally:
        loop.close()


def process_password(m, sess, ph):
    if not m.text:
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    from telethon.sessions import StringSession
    cl = TelegramClient(StringSession(), MY_API_ID, MY_API_HASH, loop=loop)

    async def sign_p():
        await cl.connect()
        try:
            await cl.sign_in(password=m.text)
            # 🔥 استخراج الجلسة بصيغة النص الخام هنا أيضاً
            pure_string = str(cl.session.save())
            return "OK", pure_string
        except Exception as e:
            return str(e), None
        finally:
            await cl.disconnect()

    try:
        res, session_str = loop.run_until_complete(sign_p())
        if res == "OK":
            bot.send_message(m.chat.id, "✅ **تم ربط الحساب بنجاح وتوليد الجلسة السحابية!**")
            save_account_db(m.chat.id, ph, session_str)
        else:
            bot.send_message(m.chat.id, f"❌ خطأ في التحقق: {res}")
    except Exception as e:
        print(f"DEBUG Error in process_password: {e}")
    finally:
        loop.close()
# ================= [ ⚙️ العرض وحذف الحسابات المتواجدة ] =================
@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats_all(m):
    # تحويل المعرف لـ int لضمان مطابقة int8 في سوبابيس
    uid = int(m.chat.id)
    
    # 1. جلب الرصيد الحقيقي من القاعدة
    bal = get_balance(uid)
    
    # 2. جلب إجمالي عدد حسابات المستخدم من سوبابيس بدلاً من المجلد المحلي
    army_count = 0
    if supabase_client:
        try:
            response = supabase_client.table("telegram_accounts").select("id").eq("user_id", uid).execute()
            if response.data:
                army_count = len(response.data)
        except Exception as e:
            print(f"DEBUG Error fetching stats count from db: {e}")

    # 3. إرسال الإحصائيات الدقيقة
    bot.send_message(
        m.chat.id,
        f"📊 **إحصائياتك:**\n📱 الحسابات: `{army_count}`\n💵 الرصيد المتاح: `{bal}`$ ",
        parse_mode="Markdown"
    )


# ================= [ 🛠️ نظام الحذف السحابي المتزامن التلقائي ] =================

@bot.message_handler(func=lambda m: m.text == "❌ حذف حساب")
def delete_acc_menu(m):
    # 1. جلب الحسابات مباشرة من عمود accounts بجدول users
    army = []
    if supabase_client:
        try:
            res = supabase_client.table("users").select("accounts").eq("user_id", str(m.chat.id)).execute()
            if res.data and res.data[0].get("accounts"):
                # تقسيم السطور وتنظيف الحسابات
                army = [s.strip() for s in res.data[0]["accounts"].split("\n") if s.strip()]
        except Exception as e:
            print(f"DEBUG Error fetching accounts for deletion: {e}")

    # 2. التحقق الصارم من وجود حسابات (لمنع التناقض)
    if not army:
        return bot.send_message(m.chat.id, "❌ لا توجد حسابات مربوطة.")

    # 3. بناء الأزرار الذكية بناءً على الترتيب الفعلي للحسابات
    mk = types.InlineKeyboardMarkup()
    for idx, session_str in enumerate(army):
        # نستخرج آخر 10 أحرف من جلسة السلسلة لتمييز الحساب للمستخدم بأمان
        short_id = session_str[-10:] if len(session_str) > 10 else f"الحساب {idx+1}"
        mk.add(types.InlineKeyboardButton(f"❌ حذف: ...{short_id}", callback_data=f"del_dragon_{idx}"))
        
    bot.send_message(m.chat.id, "اختر الحساب للمسح نهائياً من النظام السحابي:", reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data.startswith("del_dragon_"))
def finalize_delete(c):
    # استخراج رقم الترتيب المراد حذفه
    try:
        acc_index = int(c.data.replace("del_dragon_", ""))
    except:
        return bot.answer_callback_query(c.id, "❌ بيانات غير صالحة.")

    if not supabase_client:
        return bot.answer_callback_query(c.id, "❌ سوبابيس غير متصل حالياً.")

    try:
        # 1. جلب القائمة الحالية من قاعدة البيانات لتفادي مسح بيانات خاطئة
        res = supabase_client.table("users").select("accounts").eq("user_id", str(c.message.chat.id)).execute()
        
        if not res.data or not res.data[0].get("accounts"):
            bot.answer_callback_query(c.id, "❌ لم يتم العثور على الحسابات.")
            return

        army = [s.strip() for s in res.data[0]["accounts"].split("\n") if s.strip()]

        # 2. التأكد من أن الترتيب المطلوب حذفه موجود فعلاً في النطاق
        if acc_index >= len(army):
            bot.answer_callback_query(c.id, "❌ تم تحديث الحسابات مسبقاً.")
            return

        # 3. إزالة الحساب المحدد من القائمة
        removed_acc = army.pop(acc_index)
        
        # 4. إعادة دمج الحسابات المتبقية وإرسالها مجدداً لسوبابيس لتحديث العمود
        updated_accounts_str = "\n".join(army)
        
        supabase_client.table("users").update({"accounts": updated_accounts_str}).eq("user_id", str(c.message.chat.id)).execute()

        # 5. تأكيد الحذف بنجاح وتحديث واجهة المستخدم فوراً
        bot.answer_callback_query(c.id, "✅ تم الحذف بنجاح من السحابة")
        
        # استخراج رمز تمييزي مصغر للحساب المحذوف للتأكيد
        short_id = removed_acc[-10:] if len(removed_acc) > 10 else f"رقم {acc_index + 1}"
        
        bot.edit_message_text(
            f"✅ **تم إلغاء ربط الحساب بنجاح وحذفه نهائياً من السيرفر!**\n⚙️ الحساب المحذوف: `...{short_id}`\n📦 الحسابات المتبقية الحالية: `{len(army)}`",
            c.message.chat.id,
            c.message.message_id,
        )

    except Exception as e:
        print(f"Error executing cloud deletion: {e}")
        bot.answer_callback_query(c.id, f"❌ حدث خلل أثناء الحذف: {str(e)}")

# =====================================================================
# 🚀 تعديل التوجيه والتحكم في زر البدء (تم تصحيح المدخلات والـ Threads والسوبابيس)
# =====================================================================
@bot.message_handler(func=lambda m: m.text in ["🚀 بدء السحب", "⚔️ بدء الأضافه"])
def start_attack_cmd(m):
    uid = int(m.chat.id)
    
    # 1. التحقق من الرصيد
    if get_balance(uid) < PRICE_PER_MEMBER:
        return bot.send_message(m.chat.id, "❌ رصيد منخفض.")
    
    # 2. جلب الحسابات النشطة مباشرة وبشكل مرن
    army = []
    if supabase_client:
        try:
            res = supabase_client.table("telegram_accounts").select("session_string").eq("user_id", uid).eq("status", "active").execute()
            if res.data:
                # نأخذ نصوص الجلسات وننظف المسافات فقط دون شروط معقدة
                army = [row["session_string"].strip() for row in res.data if row.get("session_string")]
        except Exception as e:
            print(f"DEBUG Error fetching army from DB: {e}")

    # 3. التحقق من وجود حسابات في المصفوفة
    if not army:
        return bot.send_message(m.chat.id, "❌ أضف حسابات أولاً.")

    # إذا نجح، ينتقل للخطوة التالية فوراً
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

# 1️⃣ الدالة الأولى: تجهيز البيئة لتشغيل المحرك بدون تجميد البوت
def launch_radar_safely(army, source, target, total_needed, chat_id):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # تشغيل دالة النقل
        loop.run_until_complete(
            run_sahm_v73(army, source, target, total_needed, chat_id)
        )
        loop.close()
    except Exception as e:
        print(f"❌ خطأ المحرك: {e}")
        try:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء التشغيل:\n`{str(e)}`")
        except Exception:
            pass


# 2️⃣ الدالة الثانية: استقبال الأمر وإطلاق العملية
def start_radar_execution(m, army, source, target):
    if not m.text:
        return
    try:
        total_needed = int(m.text.strip())
        bot.send_message(m.chat.id, "⏳ جاري تحضير المحرك وإطلاق الحسابات...")

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
    # تحويل المعرف لـ int لضمان مطابقة int8 في سوبابيس
    uid = int(m.chat.id)
    
    # 1. جلب الرصيد من القاعدة
    bal = get_balance(uid)
    
    # 2. جلب عدد الحسابات النشطة للمستخدم مباشرة من سوبابيس
    army_count = 0
    if supabase_client:
        try:
            response = supabase_client.table("telegram_accounts").select("id").eq("user_id", uid).eq("status", "active").execute()
            if response.data:
                army_count = len(response.data)
        except Exception as e:
            print(f"DEBUG Error fetching accounts count from db: {e}")

    # 3. إرسال النص المحدث
    bot.send_message(
        m.chat.id,
        f"👤 **حسابك:**\n💵 الرصيد: `{bal}$` \n📦 الحسابات النشطة: `{army_count}`",
        parse_mode="Markdown"
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
    print("🛰️ جاري تشغيل دراغون V73..")
    
    # تشغيل السيرفر
    threading.Thread(target=run_server, daemon=True).start()
    
    # تنظيف تليجرام (مهم جداً لحل خطأ 409)
    try:
        bot.remove_webhook()
    except:
        pass
        
    # بدء البوت
    bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
