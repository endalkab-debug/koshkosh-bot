import os
import uuid
import random
import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone
import pytz

from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

HOST_TELEGRAM_ID = 446176588
SUPPORT_CHANNEL = "@KoshKosh_Support"
BOT_USERNAME = "@KoshKosh_LuckyJar_bot"

CBE_ACCOUNT = "1000211559277"
TELEBIRR_NUMBER = "0913550415"
CBEBIRR_NUMBER = "0913550415"

PRICE_PER_NUMBER = 100
TOTAL_NUMBERS = 100

PRIZES = {
    "1st": 4000,
    "2nd": 2000,
    "3rd": 1500,
}

EAT = pytz.timezone('Africa/Addis_Ababa')
TRANSACTION_MINUTES = 15
DRAW_DELAY_MINUTES = 15

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger("koshkosh-bot")

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "KoshKosh Bot running.", 200

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    flask_app.run(host="0.0.0.0", port=port)

number_status = {}
user_carts = {}
orders = {}
active_order_by_user = {}
game_drawn = False
extensions = 0
game_postponed_today = False
draw_task = None

LANGUAGES = {
    "en": {
        "welcome": "🎉 Welcome to KoshKosh Lucky Jar!\n\nChoose an option below to continue.",
        "play": "🎟️ Play / Select Numbers",
        "board": "📊 Number Board",
        "rules": "📜 Rules & Prizes",
        "language": "🌐 Change Language",
        "back": "🔙 Back to Main Menu",
        "contact": "📞 Contact Support",
        "choose_language": "Please choose your language:",
        "language_changed": "✅ Language changed to English.",
        "select_numbers": "🎟️ Select your lucky number(s).\nPrice: {price} Birr per number.\n\n🟢 Available   🟠 Your selection   🔴 Sold",
        "selected": "Selected numbers: {numbers}\nTotal: {total} Birr",
        "no_selection": "Please select at least one available number.",
        "number_taken": "Sorry, number {number} is no longer available.",
        "number_added": "Number {number} added.",
        "number_removed": "Number {number} removed.",
        "checkout": "✅ Continue to Checkout",
        "cancel": "❌ Cancel Selection",
        "name_prompt": "Please enter your full name:",
        "phone_prompt": "Please enter your phone number:",
        "invoice": "🧾 **Payment Invoice**\n\nOrder ID: `{order_id}`\nName: {name}\nPhone: {phone}\nNumbers: {numbers}\nTotal: **{total} Birr**\n\n💳 **Pay to:**\nCBE: `{cbe}`\nTelebirr: `{telebirr}`\nCBEBirr: `{cbebirr}`\n\n📸 **Send your payment screenshot manually to the channel:** {channel}",
        "expired": "⌛ **Transaction expired.** Numbers released.",
        "rules_text": "📜 **Rules & Prizes**\n\n• 100 Birr per number.\n• 15-minute payment window.\n\n🏆 **Prizes**\n🥇 4,000 ETB\n🥈 2,000 ETB\n🥉 1,500 ETB",
        "board_text": "📊 **Board**\n\n🟢 Available: {available}\n⏳ Reserved: {reserved}\n🔴 Sold: {sold}",
        "main_menu": "Main menu:",
        "support_info": "Contact @KoshKoshSupport",
        "host_only": "Host only.",
        "status_text": "📊 **Status**\n\nAvailable: {available}\nReserved: {reserved}\nSold: {sold}",
        "order_channel": "💳 **New Payment**\n\nOrder ID: `{order_id}`\nName: {name}\nPhone: {phone}\nNumbers: {numbers}\nAmount: {total} Birr\n\nVerify below.",
        "approved_host": "Approved.",
        "rejected_host": "Rejected.",
        "sold_out": "🎉 All 100 sold! Draw in 15 mins.",
        "approved_button": "✅ Approve",
        "rejected_button": "❌ Reject",
        "page_1": "⬅️ Page 1 (1-50)",
        "page_2": "➡️ Page 2 (51-100)",
        "time_extended": "⚠️ 9PM reached. Extended by 1 hour!",
        "game_postponed": "😔 No sales today. Postponed.",
    },
    "am": {
        "welcome": "🎉 ወደ ኮሽኮሽ ሎተሪ እንኳን በደህና መጡ!\n\nለመቀጠል ከታች ያለውን አማራጭ ይምረጡ።",
        "play": "🎟️ ይጫወቱ / ቁጥር ይምረጡ",
        "board": "📊 የቁጥሮች ሰንጠረዥ",
        "rules": "📜 ደንቦች እና ሽልማቶች",
        "language": "🌐 ቋንቋ ይቀይሩ",
        "back": "🔙 ወደ ዋናው ማውጫ",
        "contact": "📞 የድጋፍ አገልግሎት",
        "choose_language": "እባክዎ ቋንቋዎን ይምረጡ፦",
        "language_changed": "✅ ቋንቋው ወደ አማርኛ ተቀይሯል።",
        "select_numbers": "🎟️ የዕድል ቁጥርዎን/ቁጥሮችዎን ይምረጡ።\n\n🟢 ክፍት   🟠 የመረጡት   🔴 የተሸጠ",
        "selected": "የመረጡት ቁጥሮች፦ {numbers}\nጠቅላላ፦ {total} ብር",
        "no_selection": "እባክዎ ቢያንስ አንድ ክፍት ቁጥር ይምረጡ።",
        "number_taken": "ይቅርታ፣ ቁጥር {number} ከእንግዲህ ክፍት አይደለም።",
        "number_added": "ቁጥር {number} ተጨምሯል።",
        "number_removed": "ቁጥር {number} ተወግዷል።",
        "checkout": "✅ ወደ ክፍያ ይቀጥሉ",
        "cancel": "❌ ምርጫውን ይሰርዙ",
        "name_prompt": "እባክዎ ሙሉ ስምዎን ያስገቡ:",
        "phone_prompt": "እባክዎ ስልክ ቁጥርዎን ያስገቡ:",
        "invoice": "🧾 **የክፍያ ደረሰኝ**\n\nየትዕዛዝ መለያ፦ `{order_id}`\nስም፦ {name}\nስልክ፦ {phone}\nቁጥሮች፦ {numbers}\nጠቅላላ፦ **{total} ብር**\n\n💳 **የክፍያ አማራጮች**\nCBE፦ `{cbe}`\nTelebirr፦ `{telebirr}`\nCBEBirr፦ `{cbebirr}`\n\n📸 **የክፍያ ስክሪንሾትዎን በእጅዎ ወደዚህ ቻናል ይላኩ:** {channel}",
        "expired": "⌛ **ጊዜው አልቋል።**",
        "rules_text": "📜 **ደንቦች**\n\n• 100 ብር ለአንድ ቁጥር\n\n🏆 **ሽልማቶች**\n🥇 4,000 ብር\n🥈 2,000 ብር\n🥉 1,500 ብር",
        "board_text": "📊 **ሰንጠረዥ**\n\n🟢 ክፍት፦ {available}\n⏳ የተያዙ፦ {reserved}\n🔴 የተሸጡ፦ {sold}",
        "main_menu": "ዋና ማውጫ፦",
        "support_info": "ለድጋፍ @KoshKoshSupport",
        "host_only": "ለአስተናጋጅ ብቻ።",
        "status_text": "📊 ሁኔታ\n\nክፍት፦ {available}\nየተያዙ፦ {reserved}\nየተሸጡ፦ {sold}",
        "order_channel": "💳 **አዲስ ክፍያ**\n\nOrder ID: `{order_id}`\nስም፦ {name}\nስልክ፦ {phone}\nቁጥሮች፦ {numbers}\nጠቅላላ፦ {total} ብር",
        "approved_host": "ተፈቅዷል።",
        "rejected_host": "ውድቅ ተደርጓል።",
        "sold_out": "🎉 ሁሉም ተሽጠዋል!",
        "approved_button": "✅ አጽድቅ",
        "rejected_button": "❌ ውድቅ አድርግ",
        "page_1": "⬅️ ገጽ 1 (1-50)",
        "page_2": "➡️ ገጽ 2 (51-100)",
        "time_extended": "⚠️ 9:00 ሰዓት ደርሷል! ጨዋታው ተራዝሟል።",
        "game_postponed": "😔 ዛሬ ምንም አልተሸጠም። ጨዋታው ተላልፏል።",
    },
}

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("language", "en")

def t(context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs) -> str:
    lang = get_lang(context)
    template = LANGUAGES.get(lang, LANGUAGES["en"]).get(key, LANGUAGES["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template

def user_text(lang: str, key: str, **kwargs) -> str:
    template = LANGUAGES.get(lang, LANGUAGES["en"]).get(key, LANGUAGES["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template

def main_menu_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "play"), callback_data="play")],
        [InlineKeyboardButton(t(context, "board"), callback_data="show_board")],
        [InlineKeyboardButton(t(context, "rules"), callback_data="show_rules")],
        [InlineKeyboardButton(t(context, "language"), callback_data="change_language")],
        [InlineKeyboardButton(t(context, "contact"), callback_data="contact_support")],
    ])

def language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="set_language:en"),
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="set_language:am"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ])

def number_grid_keyboard(user_id: int, context, page: int = 1):
    cart = user_carts.get(user_id)
    selected = cart["numbers"] if cart else set()
    rows = []
    row = []
    
    start_num = 1 if page == 1 else 51
    end_num = 50 if page == 1 else 100

    for number in range(start_num, end_num + 1):
        status = number_status.get(number)
        if number in selected:
            label = f"🟠{number}"
            callback = f"toggle:{number}"
        elif status and status["status"] == "sold":
            label = f"🔴{number}"
            callback = "unavailable"
        elif status and status["status"] == "reserved":
            label = f"⏳{number}"
            callback = "unavailable"
        else:
            label = f"🟢{number}"
            callback = f"toggle:{number}"
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav_row = []
    if page == 1:
        nav_row.append(InlineKeyboardButton(t(context, "page_2"), callback_data="page_2"))
    else:
        nav_row.append(InlineKeyboardButton(t(context, "page_1"), callback_data="page_1"))
    rows.append(nav_row)

    if selected:
        rows.append([InlineKeyboardButton(t(context, "checkout"), callback_data="checkout")])
        rows.append([InlineKeyboardButton(t(context, "cancel"), callback_data="cancel_cart")])
    
    rows.append([InlineKeyboardButton(t(context, "back"), callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def approval_keyboard(order_id: str, lang: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(user_text(lang, "approved_button"), callback_data=f"approve:{order_id}"),
            InlineKeyboardButton(user_text(lang, "rejected_button"), callback_data=f"reject:{order_id}"),
        ]
    ])

def cart_is_expired(cart) -> bool:
    return datetime.now(timezone.utc) >= cart["expires_at"]

def release_cart_numbers(user_id: int, cart):
    for number in list(cart["numbers"]):
        status = number_status.get(number)
        if status and status.get("status") == "reserved" and status.get("user_id") == user_id:
            number_status.pop(number, None)

async def expire_cart_after_deadline(user_id: int, cart_token: str, context: ContextTypes.DEFAULT_TYPE):
    cart = user_carts.get(user_id)
    if not cart or cart["token"] != cart_token:
        return
    delay = max(0, (cart["expires_at"] - datetime.now(timezone.utc)).total_seconds())
    await asyncio.sleep(delay)
    cart = user_carts.get(user_id)
    if not cart or cart["token"] != cart_token:
        return
    order_id = active_order_by_user.get(user_id)
    order = orders.get(order_id) if order_id else None
    if order and order.get("status") == "proof_submitted":
        return
    if order and order.get("status") in ("approved", "rejected", "expired"):
        return
    release_cart_numbers(user_id, cart)
    user_carts.pop(user_id, None)
    if order:
        order["status"] = "expired"
        active_order_by_user.pop(user_id, None)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=user_text(cart.get("language", "en"), "expired"),
            parse_mode="Markdown",
        )
    except Exception:
        pass

def start_cart_timer(user_id: int, cart, context):
    old_task = cart.get("task")
    if old_task and not old_task.done():
        old_task.cancel()
    cart["task"] = asyncio.create_task(expire_cart_after_deadline(user_id, cart["token"], context))

def remaining_minutes(cart) -> int:
    seconds = max(0, (cart["expires_at"] - datetime.now(timezone.utc)).total_seconds())
    return int((seconds + 59) // 60)

async def start_draw_timer(context: ContextTypes.DEFAULT_TYPE):
    global draw_task
    await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text="🎉 All 100 numbers sold! The draw will happen in 15 minutes.", parse_mode="Markdown")
    draw_task = asyncio.create_task(execute_scheduled_draw(context))

async def execute_scheduled_draw(context: ContextTypes.DEFAULT_TYPE):
    global game_drawn
    await asyncio.sleep(DRAW_DELAY_MINUTES * 60)
    if game_drawn:
        return
    sold_numbers = [number for number, item in number_status.items() if item["status"] == "sold"]
    if len(sold_numbers) < 3:
        await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text="❌ Cannot draw: Less than 3 numbers sold.")
        return
    
    winners = random.sample(sold_numbers, 3)
    game_drawn = True
    result = user_text("en", "draw_result", first=winners[0], second=winners[1], third=winners[2])
    am_result = user_text("am", "draw_result", first=winners[0], second=winners[1], third=winners[2])
    
    try:
        await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=result, parse_mode="Markdown")
        await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=am_result, parse_mode="Markdown")
    except Exception:
        pass

    await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=result, parse_mode="Markdown")
    for position, number in enumerate(winners, start=1):
        winner_user_id = number_status[number].get("user_id")
        if winner_user_id:
            await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=f"Winner {position}: Number {number}\nTelegram ID: {winner_user_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("language", "en")
    await update.message.reply_text(t(context, "welcome"), reply_markup=main_menu_keyboard(context))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(context, "choose_language"), reply_markup=language_keyboard())

async def show_number_grid(update: Update, context, page: int = 1):
    user_id = update.effective_user.id
    cart = user_carts.get(user_id)
    if cart and cart_is_expired(cart):
        release_cart_numbers(user_id, cart)
        user_carts.pop(user_id, None)
        order_id = active_order_by_user.pop(user_id, None)
        if order_id and order_id in orders:
            orders[order_id]["status"] = "expired"
        cart = None
    
    text = t(context, "select_numbers", price=PRICE_PER_NUMBER)
    if cart and cart["numbers"]:
        selected_numbers = sorted(cart["numbers"])
        total = len(selected_numbers) * PRICE_PER_NUMBER
        text += "\n\n" + t(context, "selected", numbers=", ".join(map(str, selected_numbers)), total=total)
        text += f"\n\n⏳ Time remaining: {remaining_minutes(cart)} minute(s)."
    
    markup = number_grid_keyboard(user_id, context, page)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

async def show_board(update: Update, context):
    sold = sum(1 for item in number_status.values() if item["status"] == "sold")
    reserved = sum(1 for item in number_status.values() if item["status"] == "reserved")
    available = TOTAL_NUMBERS - sold - reserved
    text = t(context, "board_text", available=available, reserved=reserved, sold=sold)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]]))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]]))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "unavailable":
        return await query.answer("This number is sold or reserved.", show_alert=True)
    if data == "main_menu":
        await query.answer()
        return await query.edit_message_text(t(context, "welcome"), reply_markup=main_menu_keyboard(context))
    if data == "play":
        await query.answer()
        return await show_number_grid(update, context, page=1)
    if data == "page_1":
        await query.answer()
        return await show_number_grid(update, context, page=1)
    if data == "page_2":
        await query.answer()
        return await show_number_grid(update, context, page=2)
    if data == "show_board":
        await query.answer()
        return await show_board(update, context)
    if data == "show_rules":
        await query.answer()
        return await query.edit_message_text(t(context, "rules_text"), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]]))
    if data == "change_language":
        await query.answer()
        return await query.edit_message_text(t(context, "choose_language"), reply_markup=language_keyboard())
    if data.startswith("set_language:"):
        lang = data.split(":", 1)[1]
        context.user_data["language"] = lang
        await query.answer()
        return await query.edit_message_text(user_text(lang, "language_changed"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(user_text(lang, "back"), callback_data="main_menu")]]))
    if data == "contact_support":
        await query.answer()
        return await query.message.reply_text(t(context, "support_info"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]]))
    if data.startswith("toggle:"):
        number = int(data.split(":", 1)[1])
        cart = user_carts.get(user_id)
        if cart and cart_is_expired(cart):
            release_cart_numbers(user_id, cart)
            user_carts.pop(user_id, None)
            order_id = active_order_by_user.pop(user_id, None)
            if order_id and order_id in orders:
                orders[order_id]["status"] = "expired"
            cart = None
        if cart and number in cart["numbers"]:
            cart["numbers"].remove(number)
            status = number_status.get(number)
            if status and status.get("status") == "reserved" and status.get("user_id") == user_id:
                number_status.pop(number, None)
            if not cart["numbers"]:
                task = cart.get("task")
                if task and not task.done():
                    task.cancel()
                user_carts.pop(user_id, None)
                active_order_by_user.pop(user_id, None)
            await query.answer(t(context, "number_removed", number=number))
            return await show_number_grid(update, context, page=1 if number <= 50 else 2)
        status = number_status.get(number)
        if status:
            return await query.answer(t(context, "number_taken", number=number), show_alert=True)
        if not cart:
            now = datetime.now(timezone.utc)
            cart = {"token": str(uuid.uuid4()), "numbers": set(), "started_at": now, "expires_at": now + timedelta(minutes=TRANSACTION_MINUTES), "task": None, "language": get_lang(context)}
            user_carts[user_id] = cart
            start_cart_timer(user_id, cart, context)
        cart["numbers"].add(number)
        number_status[number] = {"status": "reserved", "user_id": user_id}
        await query.answer(t(context, "number_added", number=number))
        return await show_number_grid(update, context, page=1 if number <= 50 else 2)
    if data == "cancel_cart":
        cart = user_carts.get(user_id)
        if cart:
            task = cart.get("task")
            if task and not task.done():
                task.cancel()
            release_cart_numbers(user_id, cart)
            user_carts.pop(user_id, None)
        order_id = active_order_by_user.pop(user_id, None)
        if order_id and order_id in orders:
            orders[order_id]["status"] = "cancelled"
        await query.answer("Selection cancelled.")
        return await query.edit_message_text(t(context, "welcome"), reply_markup=main_menu_keyboard(context))
    if data == "checkout":
        cart = user_carts.get(user_id)
        if not cart or not cart["numbers"]:
            return await query.answer(t(context, "no_selection"), show_alert=True)
        if cart_is_expired(cart):
            release_cart_numbers(user_id, cart)
            user_carts.pop(user_id, None)
            await query.answer(t(context, "expired"), show_alert=True)
            return await query.edit_message_text(t(context, "expired"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]]))
        await query.answer()
        context.user_data["checkout_name"] = None
        context.user_data["checkout_order_token"] = cart["token"]
        context.user_data["awaiting_name"] = True
        return await query.message.reply_text(t(context, "name_prompt"))
    if data.startswith("approve:"):
        return await approve_payment_callback(update, context)
    if data.startswith("reject:"):
        return await reject_payment_callback(update, context)
    await query.answer()

async def handle_customer_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if context.user_data.get("awaiting_name"):
        cart = user_carts.get(user_id)
        if not cart or cart_is_expired(cart):
            context.user_data.pop("awaiting_name", None)
            return await update.message.reply_text(t(context, "expired"))
        if len(text) < 2:
            return await update.message.reply_text("Please enter a valid full name.")
        context.user_data["checkout_name"] = text
        context.user_data["awaiting_name"] = False
        context.user_data["awaiting_phone"] = True
        return await update.message.reply_text(t(context, "phone_prompt"))

    if context.user_data.get("awaiting_phone"):
        cart = user_carts.get(user_id)
        if not cart or cart_is_expired(cart):
            context.user_data.pop("awaiting_phone", None)
            return await update.message.reply_text(t(context, "expired"))
        phone = text.replace(" ", "").replace("-", "")
        if len(phone) < 9:
            return await update.message.reply_text("Please enter a valid phone number.")
        name = context.user_data.get("checkout_name", "")
        numbers = sorted(cart["numbers"])
        total = len(numbers) * PRICE_PER_NUMBER
        order_id = uuid.uuid4().hex[:12].upper()
        order = {"order_id": order_id, "user_id": user_id, "name": name, "phone": phone, "numbers": numbers, "total": total, "language": cart.get("language", get_lang(context)), "status": "awaiting_payment", "created_at": datetime.now(timezone.utc), "expires_at": cart["expires_at"], "cart_token": cart["token"], "channel_message_id": None}
        orders[order_id] = order
        active_order_by_user[user_id] = order_id
        context.user_data.pop("awaiting_phone", None)
        context.user_data.pop("awaiting_name", None)
        context.user_data.pop("checkout_name", None)
        
        # Send Invoice to User
        invoice = user_text(order["language"], "invoice", order_id=order_id, name=name, phone=phone, numbers=", ".join(map(str, numbers)), quantity=len(numbers), price=PRICE_PER_NUMBER, total=total, cbe=CBE_ACCOUNT, telebirr=TELEBIRR_NUMBER, cbebirr=CBEBIRR_NUMBER, channel=SUPPORT_CHANNEL)
        await update.message.reply_text(invoice, parse_mode="Markdown")

        # Send Order Details & Buttons to Channel
        channel_text = user_text(order["language"], "order_channel", order_id=order_id, name=name, phone=phone, user_id=user_id, numbers=", ".join(map(str, numbers)), total=total)
        try:
            await context.bot.send_message(
                chat_id=SUPPORT_CHANNEL, 
                text=channel_text, 
                parse_mode="Markdown", 
                reply_markup=approval_keyboard(order_id, order["language"])
            )
        except Exception as e:
            logger.error(f"Failed to send to channel: {e}")
        return

    order_id = active_order_by_user.get(user_id)
    order = orders.get(order_id) if order_id else None
    if order and order["status"] == "awaiting_payment":
        return await update.message.reply_text("Please send your screenshot manually to " + SUPPORT_CHANNEL)
    await update.message.reply_text(t(context, "main_menu"), reply_markup=main_menu_keyboard(context))

async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot no longer automatically processes photos. Users must send them manually to the channel.
    await update.message.reply_text(f"⚠️ Please send your screenshot manually to our support channel: {SUPPORT_CHANNEL}\n\nThe Host will verify it there.")

async def approve_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != HOST_TELEGRAM_ID:
        return await query.answer("Only the Host can approve payments.", show_alert=True)
    order_id = query.data.split(":", 1)[1]
    order = orders.get(order_id)
    if not order or order["status"] != "awaiting_payment":
        return await query.answer("Order not found or already processed.", show_alert=True)
    for number in order["numbers"]:
        status = number_status.get(number)
        if not status or status.get("user_id") != order["user_id"]:
            return await query.answer("Reservation mismatch.", show_alert=True)
    for number in order["numbers"]:
        number_status[number] = {"status": "sold", "user_id": order["user_id"]}
    order["status"] = "approved"
    user_id = order["user_id"]
    cart = user_carts.get(user_id)
    if cart and cart["token"] == order["cart_token"]:
        user_carts.pop(user_id, None)
    active_order_by_user.pop(user_id, None)
    await query.answer("Payment approved.")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    try:
        await query.message.reply_text(user_text(order["language"], "approved_host"))
    except Exception:
        pass
    customer_message = user_text(order["language"], "payment_confirmed", numbers=", ".join(map(str, order["numbers"])))
    try:
        await context.bot.send_message(chat_id=user_id, text=customer_message, parse_mode="Markdown")
    except Exception:
        pass
    sold = sum(1 for item in number_status.values() if item["status"] == "sold")
    if sold == TOTAL_NUMBERS:
        try:
            await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=user_text(order["language"], "sold_out"))
        except Exception:
            pass
        await start_draw_timer(context)

async def reject_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != HOST_TELEGRAM_ID:
        return await query.answer("Only the Host can reject payments.", show_alert=True)
    order_id = query.data.split(":", 1)[1]
    order = orders.get(order_id)
    if not order or order["status"] != "awaiting_payment":
        return await query.answer("Order not found.", show_alert=True)
    order["status"] = "rejected"
    user_id = order["user_id"]
    cart = user_carts.get(user_id)
    if cart and cart["token"] == order["cart_token"]:
        release_cart_numbers(user_id, cart)
        user_carts.pop(user_id, None)
    active_order_by_user.pop(user_id, None)
    await query.answer("Payment rejected.")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text(user_text(order["language"], "rejected_host"))
    try:
        await context.bot.send_message(chat_id=user_id, text=user_text(order["language"], "payment_rejected"))
    except Exception:
        pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled bot exception", exc_info=context.error)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_customer_text))
    application.add_error_handler(error_handler)
    logger.info("KoshKosh Lucky Jar Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)

if __name__ == "__main__":
    main()
