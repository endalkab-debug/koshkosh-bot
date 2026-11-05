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

# Timezone for East Africa Time (EAT)
EAT = pytz.timezone('Africa/Addis_Ababa')
TRANSACTION_MINUTES = 15
DRAW_DELAY_MINUTES = 15  # Delay after full sale before drawing

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("koshkosh-bot")

# ============================================================
# FLASK HEALTH CHECK (FOR RENDER)
# ============================================================

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "KoshKosh Lucky Jar Bot is running.", 200

@flask_app.route("/health")
def health():
    return {"status": "ok", "service": "KoshKosh Lucky Jar Bot"}, 200

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    flask_app.run(host="0.0.0.0", port=port)


# ============================================================
# IN-MEMORY GAME DATA
# ============================================================

number_status = {}
user_carts = {}
orders = {}
active_order_by_user = {}
game_drawn = False
extensions = 0
game_postponed_today = False
draw_task = None

# ============================================================
# BILINGUAL TEXT
# ============================================================

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
        "select_numbers": "🎟️ Select your lucky number(s).\n\nPrice: {price} Birr per number.\n15-minute transaction period starts on first selection.\n\n🟢 Available   🟠 Your selection   🔴 Sold   ⏳ Reserved",
        "selected": "Selected numbers: {numbers}\nTotal: {total} Birr",
        "no_selection": "Please select at least one available number.",
        "number_taken": "Sorry, number {number} is no longer available.",
        "number_added": "Number {number} added to your selection.",
        "number_removed": "Number {number} removed from your selection.",
        "checkout": "✅ Continue to Checkout",
        "cancel": "❌ Cancel Selection",
        "name_prompt": "Please enter your full name.\n\n⏳ Your 15-minute transaction period is running.",
        "phone_prompt": "Please enter your phone number.",
        "invoice": "🧾 **KoshKosh Lucky Jar – Payment Invoice**\n\nOrder ID: `{order_id}`\nName: {name}\nPhone: {phone}\nSelected number(s): {numbers}\nQuantity: {quantity}\nPrice per number: {price} Birr\nTotal amount: **{total} Birr**\n\n💳 **Payment methods**\nCBE: `{cbe}`\nTelebirr: `{telebirr}`\nCBEBirr: `{cbebirr}`\n\nAfter making the payment, send your payment screenshot directly here in this bot.",
        "invoice_sent": "✅ Your invoice has been created.\n\nPlease complete the payment and send the screenshot here before your 15-minute transaction period expires.",
        "expired": "⌛ **Transaction expired.**\n\nYour 15-minute transaction period has ended without a payment screenshot. Your reserved number(s) have been released.",
        "proof_received": "📩 Your payment screenshot has been received and sent to the Host for verification.\n\nYour selected numbers remain reserved while the Host reviews your payment.",
        "payment_confirmed": "🎉 **Payment approved!**\n\nYour payment has been verified successfully.\nConfirmed number(s): {numbers}\n\nGood luck! 🍀",
        "payment_rejected": "⚠️ Your payment submission could not be approved.\n\nPlease contact the Host/Support channel for assistance.",
        "rules_text": "📜 **Rules & Prizes**\n\n• Each number costs 100 Birr.\n• Game runs once a day (3:30 AM – 9:00 PM EAT).\n• 15-minute transaction period.\n• If unsold at 9:00 PM, it extends by 1 hour.\n• 15-minute draw countdown begins once 100 are sold.\n\n🏆 **Prizes**\n🥇 1st: 4,000 ETB\n🥈 2nd: 2,000 ETB\n🥉 3rd: 1,500 ETB",
        "board_text": "📊 **Number Board**\n\n🟢 Available: {available}\n⏳ Reserved: {reserved}\n🔴 Sold: {sold}",
        "main_menu": "Main menu:",
        "support_info": "For assistance, contact @KoshKoshSupport",
        "host_only": "This command is available to the Host only.",
        "status_text": "📊 **Game Status**\n\nAvailable: {available}\nReserved: {reserved}\nSold: {sold}\nActive orders: {active}\nDrawn: {drawn}",
        "order_channel": "💳 **New Payment Submission**\n\nOrder ID: `{order_id}`\nName: {name}\nPhone: {phone}\nTelegram ID: `{user_id}`\nNumbers: {numbers}\nAmount: {total} Birr\n\nPlease verify below.",
        "approved_host": "Payment approved and numbers marked as sold.",
        "rejected_host": "Payment rejected.",
        "sold_out": "🎉 All 100 numbers have been sold! The 15-minute draw countdown has started.",
        "approved_button": "✅ Approve Payment",
        "rejected_button": "❌ Reject Payment",
        "view_board_button": "📊 View Board",
        "screenshot_prompt": "Please send your payment screenshot as a photo to this bot.",
        "scheduled_draw": "⏰ The draw will happen in 15 minutes automatically.",
        "time_extended": "⚠️ 9:00 PM reached but numbers remain. The game has been extended by 1 hour!",
        "game_postponed": "😔 No numbers were sold today. The game has been postponed to tomorrow at 3:30 AM.",
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
        "select_numbers": "🎟️ የዕድል ቁጥርዎን/ቁጥሮችዎን ይምረጡ።\n\nየአንድ ቁጥር ዋጋ፦ {price} ብር።\n\n🟢 ክፍት   🟠 የመረጡት   🔴 የተሸጠ   ⏳ በጊዜያዊነት የተያዘ",
        "selected": "የመረጡት ቁጥሮች፦ {numbers}\nጠቅላላ፦ {total} ብር",
        "no_selection": "እባክዎ ቢያንስ አንድ ክፍት ቁጥር ይምረጡ።",
        "number_taken": "ይቅርታ፣ ቁጥር {number} ከእንግዲህ ክፍት አይደለም።",
        "number_added": "ቁጥር {number} ወደ ምርጫዎ ተጨምሯል።",
        "number_removed": "ቁጥር {number} ከምርጫዎ ተወግዷል።",
        "checkout": "✅ ወደ ክፍያ ይቀጥሉ",
        "cancel": "❌ ምርጫውን ይሰርዙ",
        "name_prompt": "እባክዎ ሙሉ ስምዎን ያስገቡ።",
        "phone_prompt": "እባክዎ ስልክ ቁጥርዎን ያስገቡ።",
        "invoice": "🧾 **ኮሽኮሽ ሎተሪ – የክፍያ ደረሰኝ**\n\nየትዕዛዝ መለያ፦ `{order_id}`\nስም፦ {name}\nስልክ፦ {phone}\nቁጥሮች፦ {numbers}\nብዛት፦ {quantity}\nየአንድ ቁጥር ዋጋ፦ {price} ብር\nጠቅላላ፦ **{total} ብር**\n\n💳 **የክፍያ አማራጮች**\nCBE፦ `{cbe}`\nTelebirr፦ `{telebirr}`\nCBEBirr፦ `{cbebirr}`\n\nክፍያውን ከፈጸሙ በኋላ ስክሪንሾቱን እዚህ ይላኩ።",
        "invoice_sent": "✅ የክፍያ ደረሰኝዎ ተዘጋጅቷል።",
        "expired": "⌛ **ጊዜው አልቋል።** ቁጥሮቹ ተለቀዋል።",
        "proof_received": "📩 ስክሪንሾትዎ ደርሷል።",
        "payment_confirmed": "🎉 **ክፍያዎ ተረጋግጧል!**\nቁጥሮች፦ {numbers}",
        "payment_rejected": "⚠️ ክፍያው ውድቅ ተደርጓል።",
        "rules_text": "📜 **ደንቦች**\n\n• 100 ብር ለአንድ ቁጥር\n• 15 ደቂቃ ጊዜ\n\n🏆 **ሽልማቶች**\n🥇 4,000 ብር\n🥈 2,000 ብር\n🥉 1,500 ብር",
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
        "view_board_button": "📊 ሰንጠረዥ",
        "screenshot_prompt": "እባክዎ ስክሪንሾት ይላኩ።",
        "scheduled_draw": "⏰ ዕጣው በ15 ደቂቃ ውስጥ ይወጣል።",
        "time_extended": "⚠️ 9:00 ሰዓት ደርሷል! ጨዋታው በ1 ሰዓት ተራዝሟል።",
        "game_postponed": "😔 ዛሬ ምንም አልተሸጠም። ጨዋታው ለነገ ተላልፏል።",
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

# ============================================================
# KEYBOARDS
# ============================================================

def main_menu_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "play"), callback_data="play")],
        [InlineKeyboardButton(t(context, "board"), callback_data="show_board")],
        [InlineKeyboardButton(t(context, "rules"), callback_data="show_rules")],
        [InlineKeyboardButton(t(context, "language"), callback_data="change_language")],
        [InlineKeyboardButton(t(context, "contact"), callback_data="contact_support")],
    ])

def customer_navigation_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "back"), callback_data="main_menu")],
        [InlineKeyboardButton(t(context, "board"), callback_data="show_board")],
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

def number_grid_keyboard(user_id: int, context):
    cart = user_carts.get(user_id)
    selected = cart["numbers"] if cart else set()
    rows = []
    row = []
    for number in range(1, TOTAL_NUMBERS + 1):
        status = number_status.get(number)
        if number in selected:
            label = f"🟠 {number}"
            callback = f"toggle:{number}"
        elif status and status["status"] == "sold":
            label = f"🔴 {number}"
            callback = "unavailable"
        elif status and status["status"] == "reserved":
            label = f"⏳ {number}"
            callback = "unavailable"
        else:
            label = f"🟢 {number}"
            callback = f"toggle:{number}"
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
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

# ============================================================
# TIMERS & GAME LOGIC
# ============================================================

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
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(user_text(cart.get("language", "en"), "back"), callback_data="main_menu")],
                [InlineKeyboardButton(user_text(cart.get("language", "en"), "board"), callback_data="show_board")],
            ]),
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

async def monitor_9pm_deadline(context: ContextTypes.DEFAULT_TYPE):
    """Background task: Checks if 9 PM reached. Extends by 1 hr, or postpones."""
    global extensions, game_postponed_today
    while not game_drawn:
        await asyncio.sleep(60) # Check every 60 seconds
        now = datetime.now(EAT)
        
        # 9:00 PM EAT
        if now.hour == 21 and now.minute < 5 and not game_postponed_today:
            sold = sum(1 for item in number_status.values() if item["status"] == "sold")
            if sold == 0:
                # Postpone
                game_postponed_today = True
                try:
                    await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=user_text("am", "game_postponed"), parse_mode="Markdown")
                    await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=user_text("en", "game_postponed"), parse_mode="Markdown")
                except: pass
            elif sold < TOTAL_NUMBERS:
                # Extend
                extensions += 1
                game_postponed_today = True # Prevents looping within the same minute
                try:
                    await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=user_text("am", "time_extended"), parse_mode="Markdown")
                except: pass
            else:
                # Sold out, wait for drawing
                game_postponed_today = True # Stop checking 9pm

async def start_draw_timer(context: ContextTypes.DEFAULT_TYPE):
    global draw_task
    await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text="🎉 All 100 numbers sold! The draw will happen in 15 minutes.", parse_mode="Markdown")
    draw_task = asyncio.create_task(execute_scheduled_draw(context))

async def execute_scheduled_draw(context: ContextTypes.DEFAULT_TYPE):
    global game_drawn
    await asyncio.sleep(DRAW_DELAY_MINUTES * 60) # Wait exactly 15 minutes
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

# ============================================================
# MAIN COMMANDS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("language", "en")
    await update.message.reply_text(t(context, "welcome"), reply_markup=main_menu_keyboard(context))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(context, "choose_language"), reply_markup=language_keyboard())

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID:
        return await update.message.reply_text(t(context, "host_only"))
    sold = sum(1 for item in number_status.values() if item["status"] == "sold")
    reserved = sum(1 for item in number_status.values() if item["status"] == "reserved")
    available = TOTAL_NUMBERS - sold - reserved
    active = sum(1 for order in orders.values() if order["status"] in ("awaiting_payment", "proof_submitted"))
    await update.message.reply_text(
        t(context, "status_text", available=available, reserved=reserved, sold=sold, active=active, drawn="Yes" if game_drawn else "No"),
        parse_mode="Markdown",
    )

async def show_number_grid(update: Update, context):
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
    markup = number_grid_keyboard(user_id, context)
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
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=customer_navigation_keyboard(context))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=customer_navigation_keyboard(context))

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
        return await show_number_grid(update, context)
    if data == "show_board":
        await query.answer()
        return await show_board(update, context)
    if data == "show_rules":
        await query.answer()
        return await query.edit_message_text(t(context, "rules_text"), parse_mode="Markdown", reply_markup=customer_navigation_keyboard(context))
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
        return await query.message.reply_text(t(context, "support_info"), reply_markup=customer_navigation_keyboard(context))
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
            return await show_number_grid(update, context)
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
        return await show_number_grid(update, context)
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
            return await query.edit_message_text(t(context, "expired"), reply_markup=customer_navigation_keyboard(context))
        await query.answer()
        context.user_data["checkout_name"] = None
        context.user_data["checkout_order_token"] = cart["token"]
        context.user_data["awaiting_name"] = True
        return await query.message.reply_text(t(context, "name_prompt"), reply_markup=customer_navigation_keyboard(context))
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
            return await update.message.reply_text(t(context, "expired"), reply_markup=customer_navigation_keyboard(context))
        if len(text) < 2:
            return await update.message.reply_text("Please enter a valid full name.")
        context.user_data["checkout_name"] = text
        context.user_data["awaiting_name"] = False
        context.user_data["awaiting_phone"] = True
        return await update.message.reply_text(t(context, "phone_prompt"), reply_markup=customer_navigation_keyboard(context))

    if context.user_data.get("awaiting_phone"):
        cart = user_carts.get(user_id)
        if not cart or cart_is_expired(cart):
            context.user_data.pop("awaiting_phone", None)
            return await update.message.reply_text(t(context, "expired"), reply_markup=customer_navigation_keyboard(context))
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
        invoice = user_text(order["language"], "invoice", order_id=order_id, name=name, phone=phone, numbers=", ".join(map(str, numbers)), quantity=len(numbers), price=PRICE_PER_NUMBER, total=total, cbe=CBE_ACCOUNT, telebirr=TELEBIRR_NUMBER, cbebirr=CBEBIRR_NUMBER)
        await update.message.reply_text(invoice, parse_mode="Markdown", reply_markup=customer_navigation_keyboard(context))
        await update.message.reply_text(user_text(order["language"], "invoice_sent"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(user_text(order["language"], "back"), callback_data="main_menu")],[InlineKeyboardButton(user_text(order["language"], "board"), callback_data="show_board")]]))
        return

    order_id = active_order_by_user.get(user_id)
    order = orders.get(order_id) if order_id else None
    if order and order["status"] == "awaiting_payment":
        return await update.message.reply_text(t(context, "screenshot_prompt"), reply_markup=customer_navigation_keyboard(context))
    await update.message.reply_text(t(context, "main_menu"), reply_markup=main_menu_keyboard(context))

async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    order_id = active_order_by_user.get(user_id)
    order = orders.get(order_id) if order_id else None
    if not order:
        return await update.message.reply_text(t(context, "screenshot_prompt"), reply_markup=main_menu_keyboard(context))
    if order["status"] == "proof_submitted":
        return await update.message.reply_text(user_text(order["language"], "already_submitted"), reply_markup=customer_navigation_keyboard(context))
    if order["status"] != "awaiting_payment":
        return await update.message.reply_text(t(context, "screenshot_prompt"), reply_markup=main_menu_keyboard(context))
    cart = user_carts.get(user_id)
    if not cart or cart_is_expired(cart):
        if cart:
            release_cart_numbers(user_id, cart)
            user_carts.pop(user_id, None)
        order["status"] = "expired"
        active_order_by_user.pop(user_id, None)
        return await update.message.reply_text(user_text(order["language"], "expired"), reply_markup=customer_navigation_keyboard(context))
    task = cart.get("task")
    if task and not task.done():
        task.cancel()
    order["status"] = "proof_submitted"
    order["proof_file_id"] = update.message.photo[-1].file_id
    order["proof_submitted_at"] = datetime.now(timezone.utc)
    channel_text = user_text(order["language"], "order_channel", order_id=order_id, name=order["name"], phone=order["phone"], user_id=user_id, numbers=", ".join(map(str, order["numbers"])), total=order["total"])
    try:
        sent = await context.bot.send_photo(chat_id=SUPPORT_CHANNEL, photo=order["proof_file_id"], caption=channel_text, parse_mode="Markdown", reply_markup=approval_keyboard(order_id, order["language"]))
        order["channel_message_id"] = sent.message_id
    except Exception:
        if datetime.now(timezone.utc) < cart["expires_at"]:
            order["status"] = "awaiting_payment"
            start_cart_timer(user_id, cart, context)
            return await update.message.reply_text("We could not forward your screenshot. Please try again.", reply_markup=customer_navigation_keyboard(context))
        else:
            release_cart_numbers(user_id, cart)
            user_carts.pop(user_id, None)
            order["status"] = "expired"
            active_order_by_user.pop(user_id, None)
            return await update.message.reply_text(user_text(order["language"], "expired"), reply_markup=customer_navigation_keyboard(context))
    await update.message.reply_text(user_text(order["language"], "proof_received"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(user_text(order["language"], "back"), callback_data="main_menu")],[InlineKeyboardButton(user_text(order["language"], "board"), callback_data="show_board")]]))

async def approve_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != HOST_TELEGRAM_ID:
        return await query.answer("Only the Host can approve payments.", show_alert=True)
    order_id = query.data.split(":", 1)[1]
    order = orders.get(order_id)
    if not order or order["status"] != "proof_submitted":
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
        await context.bot.send_message(chat_id=user_id, text=customer_message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(user_text(order["language"], "back"), callback_data="main_menu")],[InlineKeyboardButton(user_text(order["language"], "board"), callback_data="show_board")]]))
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
    if not order or order["status"] != "proof_submitted":
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
        await context.bot.send_message(chat_id=user_id, text=user_text(order["language"], "payment_rejected"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(user_text(order["language"], "back"), callback_data="main_menu")],[InlineKeyboardButton(user_text(order["language"], "contact"), callback_data="contact_support")]]))
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
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_customer_text))
    application.add_error_handler(error_handler)
    logger.info("KoshKosh Lucky Jar Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)

if __name__ == "__main__":
    main()
