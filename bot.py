
import os
import uuid
import random
import logging
import threading
from datetime import datetime

import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================================================
# CONFIGURATION
# =====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

HOST_TELEGRAM_ID = 446176588
SUPPORT_CHANNEL = "@KoshKoshSupport"
BOT_USERNAME = "@KoshKosh_LuckyJar_bot"

CBE_ACCOUNT = "1000211559277"
TELEBIRR_NUMBER = "0913550415"
CBEBIRR_NUMBER = "0913550415"

NUMBER_PRICE = 100
TOTAL_NUMBERS = 100

PRIZES = {
    1: 4000,
    2: 2000,
    3: 1500,
}

TIMEZONE = pytz.timezone("Africa/Addis_Ababa")

# =====================================================
# GAME DATA
# =====================================================

# NOTE: This version stores game data in RAM.
# Restarting the service will erase orders and sales.
# Use a database for permanent production storage.

game_data = {
    "numbers": {},          # Approved/sold numbers
    "pending_orders": {},   # Orders awaiting host approval
    "extensions": 0,
    "draw_completed": False,
}

# =====================================================
# BILINGUAL TEXT
# =====================================================

LANGUAGES = {
    "en": {
        "language_name": "🇬🇧 English",
        "welcome": (
            "🏺 *WELCOME TO KOSHKOSH LUCKY JAR* 🏺\n\n"
            "The transparent digital KoshKosh game in Ethiopia! 🇪🇹\n\n"
            "🎯 *How it works:*\n"
            "1️⃣ Pick your lucky numbers (1–100).\n"
            "2️⃣ Pay 100 Birr per number.\n"
            "3️⃣ The Host verifies your payment.\n"
            "4️⃣ Three winners are drawn!\n\n"
            "🏆 *Prizes:*\n"
            "🥇 1st Place: 4,000 ETB\n"
            "🥈 2nd Place: 2,000 ETB\n"
            "🥉 3rd Place: 1,500 ETB\n\n"
            "👇 Choose an option below:"
        ),
        "play": "🎟️ Play KoshKosh (Pick Numbers)",
        "board": "📊 View Selection Board",
        "rules": "ℹ️ Game Rules",
        "language": "🌐 Change Language",
        "select_title": "🎯 *SELECT YOUR NUMBERS*",
        "select_help": (
            "Tap the numbers you want to buy. They turn ✅.\n"
            "Tap again to deselect.\n\n"
            "❌ means unavailable (sold or reserved)."
        ),
        "selected": "🛒 *Currently Selected:* {count} numbers",
        "total": "💰 *Total Price:* {amount} Birr",
        "checkout": "💰 Checkout ({amount} Birr)",
        "back": "🔙 Back to Main Menu",
        "empty_selection": "❌ You haven't selected any numbers!",
        "checkout_title": "🛒 *CHECKOUT — Step 1 of 2*",
        "enter_name": "Please enter your *Full Name*.",
        "enter_phone": "Please enter your *Phone Number*.",
        "name_empty": "❌ Name cannot be empty. Please enter your full name.",
        "phone_empty": "❌ Phone number cannot be empty.",
        "thank_you": "Thank you, {name}.",
        "invoice": (
            "🧾 *OFFICIAL KOSHKOSH INVOICE*\n\n"
            "👤 Name: {name}\n"
            "📞 Phone: {phone}\n"
            "🎟️ Numbers: {numbers}\n"
            "💰 Total: *{amount} Birr*\n\n"
            "💳 *PAYMENT OPTIONS:*\n"
            "🏦 CBE: `{cbe}`\n"
            "📱 Telebirr: `{telebirr}`\n"
            "📱 CBEBirr: `{cbebirr}`\n\n"
            "📸 *Next step:*\n"
            "Send your payment screenshot to {channel}.\n\n"
            "⏳ *Status: PENDING APPROVAL*\n"
            "Your selected numbers are temporarily reserved.\n"
            "The Host will verify your payment."
        ),
        "order_sent": (
            "✅ Your payment request has been sent to the Host.\n\n"
            "Please send your payment screenshot to {channel}."
        ),
        "board_title": "📊 *KOSHKOSH SELECTION BOARD*",
        "sold": "🟢 Approved/Sold: *{sold} / 100*",
        "reserved": "🟡 Pending reservations: *{reserved}*",
        "remaining": "🔴 Available: *{remaining}*",
        "refresh": "🔄 Refresh Board",
        "rules_text": (
            "📖 *KOSHKOSH GAME RULES*\n\n"
            "1️⃣ *The Jackpot:* 100 numbers are available. Each costs 100 Birr.\n"
            "2️⃣ *Selection:* Choose your numbers using the buttons.\n"
            "3️⃣ *Payment:* Transfer the total to one of the Host's accounts.\n"
            "4️⃣ *Verification:* Send your payment screenshot to the Host.\n"
            "5️⃣ *Approval:* The Host verifies payment and confirms your numbers.\n"
            "6️⃣ *The Draw:* Once all 100 numbers are sold, the Host announces the draw.\n"
            "7️⃣ *Winners:* Three numbers are drawn.\n\n"
            "🏆 1st: 4,000 ETB\n"
            "🥈 2nd: 2,000 ETB\n"
            "🥉 3rd: 1,500 ETB\n\n"
            "⏰ Selection closes at 9:00 PM EAT. "
            "If not sold out, the Host may announce an extension."
        ),
        "language_changed": "✅ Language changed to English.",
        "payment_confirmed": (
            "🎉 *PAYMENT CONFIRMED!*\n\n"
            "Your numbers ({numbers}) are officially confirmed.\n"
            "Good luck! 🍀"
        ),
        "sold_out": "🚨 ALL 100 NUMBERS HAVE BEEN SOLD!",
        "draw_not_ready": "❌ Cannot draw. All 100 numbers must be sold first.",
        "draw_already_done": "⚠️ The draw has already been completed.",
        "draw_results": (
            "🎉 *KOSHKOSH DRAW RESULTS!* 🎉\n\n"
            "🥇 *1st Place — 4,000 ETB*\n"
            "👤 {name1}\n"
            "🔢 Number: {number1}\n\n"
            "🥈 *2nd Place — 2,000 ETB*\n"
            "👤 {name2}\n"
            "🔢 Number: {number2}\n\n"
            "🥉 *3rd Place — 1,500 ETB*\n"
            "👤 {name3}\n"
            "🔢 Number: {number3}\n\n"
            "📢 Winners, please contact the Host to claim your prizes."
        ),
        "not_host": "⛔ This command is restricted to the Host.",
        "approved": "✅ Payment approved successfully.",
        "already_processed": "⚠️ This order has already been processed.",
        "order_missing": "❌ Order not found or no longer available.",
        "taken_alert": "❌ This number is already sold or reserved!",
        "language_prompt": "🌐 *Choose your preferred language:*",
        "selection_conflict": (
            "❌ One or more selected numbers are no longer available. "
            "Please select again."
        ),
    },

    "am": {
        "language_name": "🇪🇹 አማርኛ",
        "welcome": (
            "🏺 *እንኳን ወደ KOSHKOSH LUCKY JAR በደህና መጡ!* 🏺\n\n"
            "በኢትዮጵያ የተዘጋጀው ግልጽ የዲጂታል ኮሽኮሽ ጨዋታ! 🇪🇹\n\n"
            "🎯 *እንዴት ይሳተፋሉ?*\n"
            "1️⃣ ከ1–100 ያሉትን ቁጥሮች ይምረጡ።\n"
            "2️⃣ ለእያንዳንዱ ቁጥር 100 ብር ይክፈሉ።\n"
            "3️⃣ አስተናጋጁ ክፍያዎን ያረጋግጣል።\n"
            "4️⃣ ሶስት አሸናፊዎች ይወጣሉ!\n\n"
            "🏆 *ሽልማቶች፦*\n"
            "🥇 1ኛ ደረጃ፦ 4,000 ብር\n"
            "🥈 2ኛ ደረጃ፦ 2,000 ብር\n"
            "🥉 3ኛ ደረጃ፦ 1,500 ብር\n\n"
            "👇 ከታች ያለውን አማራጭ ይምረጡ፦"
        ),
        "play": "🎟️ ኮሽኮሽ ይጫወቱ (ቁጥር ይምረጡ)",
        "board": "📊 የቁጥር ምርጫ ሰሌዳ",
        "rules": "ℹ️ የጨዋታ ህጎች",
        "language": "🌐 ቋንቋ ይቀይሩ",
        "select_title": "🎯 *ቁጥሮችዎን ይምረጡ*",
        "select_help": (
            "መግዛት የሚፈልጉትን ቁጥር ይጫኑ። ✅ ይሆናል።\n"
            "እንደገና በመጫን ምርጫዎን ማጥፋት ይችላሉ።\n\n"
            "❌ ማለት ቁጥሩ ተሽጧል ወይም ተይዟል ማለት ነው።"
        ),
        "selected": "🛒 *የመረጧቸው ቁጥሮች:* {count}",
        "total": "💰 *ጠቅላላ ዋጋ:* {amount} ብር",
        "checkout": "💰 ክፍያ ({amount} ብር)",
        "back": "🔙 ወደ ዋናው ማውጫ",
        "empty_selection": "❌ ምንም ቁጥር አልመረጡም!",
        "checkout_title": "🛒 *የክፍያ ሂደት — ደረጃ 1 ከ2*",
        "enter_name": "እባክዎ ሙሉ ስምዎን ያስገቡ።",
        "enter_phone": "እባክዎ ስልክ ቁጥርዎን ያስገቡ።",
        "name_empty": "❌ ስም ባዶ መሆን የለበትም።",
        "phone_empty": "❌ ስልክ ቁጥር ባዶ መሆን የለበትም።",
        "thank_you": "እናመሰግናለን {name}።",
        "invoice": (
            "🧾 *ይፋዊ የኮሽኮሽ ደረሰኝ*\n\n"
            "👤 ስም፦ {name}\n"
            "📞 ስልክ፦ {phone}\n"
            "🎟️ ቁጥሮች፦ {numbers}\n"
            "💰 ጠቅላላ፦ *{amount} ብር*\n\n"
            "💳 *የክፍያ አማራጮች፦*\n"
            "🏦 CBE፦ `{cbe}`\n"
            "📱 Telebirr፦ `{telebirr}`\n"
            "📱 CBEBirr፦ `{cbebirr}`\n\n"
            "📸 *ቀጣይ እርምጃ፦*\n"
            "የክፍያ ማረጋገጫ ምስሉን ወደ {channel} ይላኩ።\n\n"
            "⏳ *ሁኔታ፦ ማረጋገጫ በመጠባበቅ ላይ*\n"
            "የመረጧቸው ቁጥሮች ለጊዜው ተይዘዋል።"
        ),
        "order_sent": (
            "✅ የክፍያ ጥያቄዎ ለአስተናጋጁ ተልኳል።\n\n"
            "እባክዎ የክፍያ ማረጋገጫ ምስሉን ወደ {channel} ይላኩ።"
        ),
        "board_title": "📊 *የKOSHKOSH የቁጥር ምርጫ ሰሌዳ*",
        "sold": "🟢 የተሸጡ ቁጥሮች፦ *{sold} / 100*",
        "reserved": "🟡 ማረጋገጫ የሚጠብቁ፦ *{reserved}*",
        "remaining": "🔴 ያልተያዙ፦ *{remaining}*",
        "refresh": "🔄 ሰሌዳውን አድስ",
        "rules_text": (
            "📖 *የKOSHKOSH ጨዋታ ህጎች*\n\n"
            "1️⃣ *ቁጥሮች፦* 100 ቁጥሮች አሉ። እያንዳንዱ 100 ብር ነው።\n"
            "2️⃣ *ምርጫ፦* ቁጥሮችዎን በቦታው ያሉትን አዝራሮች በመጫን ይምረጡ።\n"
            "3️⃣ *ክፍያ፦* ጠቅላላ ክፍያውን ወደ አስተናጋጁ ሂሳብ ያስተላልፉ።\n"
            "4️⃣ *ማረጋገጫ፦* የክፍያ ማስረጃውን ይላኩ።\n"
            "5️⃣ *ይሁንታ፦* አስተናጋጁ ክፍያውን አረጋግጦ ቁጥሮችዎን ያጸድቃል።\n"
            "6️⃣ *ዕጣ፦* 100 ቁጥሮች ሲሸጡ ዕጣው ይካሄዳል።\n\n"
            "🏆 1ኛ፦ 4,000 ብር\n"
            "🥈 2ኛ፦ 2,000 ብር\n"
            "🥉 3ኛ፦ 1,500 ብር\n\n"
            "⏰ የቁጥር ምርጫው ከምሽቱ 9:00 ላይ ይዘጋል። "
            "ሁሉም ቁጥሮች ካልተሸጡ አስተናጋጁ ተጨማሪ ጊዜ ሊያሳውቅ ይችላል።"
        ),
        "language_changed": "✅ ቋንቋው ወደ አማርኛ ተቀይሯል።",
        "payment_confirmed": (
            "🎉 *ክፍያዎ ተረጋግጧል!*\n\n"
            "ቁጥሮችዎ ({numbers}) በይፋ ተረጋግጠዋል።\n"
            "መልካም ዕድል! 🍀"
        ),
        "sold_out": "🚨 100 ቁጥሮች በሙሉ ተሽጠዋል!",
        "draw_not_ready": "❌ ዕጣ ማውጣት አይቻልም። 100 ቁጥሮች በሙሉ መሸጥ አለባቸው።",
        "draw_already_done": "⚠️ ዕጣው አስቀድሞ ተካሂዷል።",
        "draw_results": (
            "🎉 *የKOSHKOSH ዕጣ ውጤት!* 🎉\n\n"
            "🥇 *1ኛ ደረጃ — 4,000 ብር*\n"
            "👤 {name1}\n"
            "🔢 ቁጥር፦ {number1}\n\n"
            "🥈 *2ኛ ደረጃ — 2,000 ብር*\n"
            "👤 {name2}\n"
            "🔢 ቁጥር፦ {number2}\n\n"
            "🥉 *3ኛ ደረጃ — 1,500 ብር*\n"
            "👤 {name3}\n"
            "🔢 ቁጥር፦ {number3}\n\n"
            "📢 አሸናፊዎች ሽልማታቸውን ለመቀበል አስተናጋጁን ያነጋግሩ።"
        ),
        "not_host": "⛔ ይህንን ትዕዛዝ መጠቀም የሚችለው አስተናጋጁ ብቻ ነው።",
        "approved": "✅ ክፍያው በተሳካ ሁኔታ ጸድቋል።",
        "already_processed": "⚠️ ይህ ትዕዛዝ አስቀድሞ ተከናውኗል።",
        "order_missing": "❌ ትዕዛዙ አልተገኘም ወይም ከእንግዲህ አይገኝም።",
        "taken_alert": "❌ ይህ ቁጥር ተሽጧል ወይም ተይዟል!",
        "language_prompt": "🌐 *የሚመርጡትን ቋንቋ ይምረጡ፦*",
        "selection_conflict": "❌ ከመረጧቸው ቁጥሮች አንዳንዶቹ ከእንግዲህ አይገኙም። እባክዎ እንደገና ይምረጡ።",
    },
}


def get_lang(context):
    return context.user_data.get("language", "en")


def t(context, key, **kwargs):
    lang = get_lang(context)
    template = LANGUAGES.get(lang, LANGUAGES["en"]).get(
        key, LANGUAGES["en"].get(key, key)
    )
    return template.format(**kwargs)


def is_unavailable(number):
    if number in game_data["numbers"]:
        return True

    for order in game_data["pending_orders"].values():
        if order["status"] == "pending" and number in order["numbers"]:
            return True

    return False


def get_pending_number_count():
    reserved = set()

    for order in game_data["pending_orders"].values():
        if order["status"] == "pending":
            reserved.update(order["numbers"])

    return len(reserved)


# =====================================================
# WEB SERVER / HEALTH CHECK
# =====================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "KoshKosh Bot is running!"


def run_web_server():
    port = int(os.getenv("PORT", 10000))
    web_app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False,
    )


# =====================================================
# LANGUAGE SELECTION
# =====================================================

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
        ]
    ]

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        t(context, "language_prompt"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.split("_", 1)[1]

    if lang not in LANGUAGES:
        return

    context.user_data["language"] = lang

    await query.edit_message_text(
        t(context, "language_changed"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                t(context, "back"),
                callback_data="main_menu",
            )]
        ]),
    )


# =====================================================
# MAIN MENU
# =====================================================

def main_menu_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "play"), callback_data="view_grid")],
        [InlineKeyboardButton(t(context, "board"), callback_data="show_board")],
        [InlineKeyboardButton(t(context, "rules"), callback_data="show_rules")],
        [InlineKeyboardButton(t(context, "language"), callback_data="change_language")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Preserve the user's language preference.
    context.user_data.pop("step", None)
    context.user_data.pop("my_selection", None)
    context.user_data.pop("temp_name", None)

    if "language" not in context.user_data:
        context.user_data["language"] = "en"

    text = t(context, "welcome")

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=main_menu_keyboard(context),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard(context),
            parse_mode="Markdown",
        )


# =====================================================
# NUMBER GRID
# =====================================================

async def view_grid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "my_selection" not in context.user_data:
        context.user_data["my_selection"] = []

    keyboard = []

    for row in range(10):
        row_buttons = []

        for col in range(1, 11):
            number = row * 10 + col
            selected = context.user_data["my_selection"]

            if number in game_data["numbers"]:
                button_text = f"❌{number}"
                callback = "taken"

            elif number in selected:
                button_text = f"✅{number}"
                callback = f"toggle_{number}"

            elif is_unavailable(number):
                button_text = f"⏳{number}"
                callback = "taken"

            else:
                button_text = str(number)
                callback = f"toggle_{number}"

            row_buttons.append(
                InlineKeyboardButton(button_text, callback_data=callback)
            )

        keyboard.append(row_buttons)

    total_cost = len(context.user_data["my_selection"]) * NUMBER_PRICE

    keyboard.append([
        InlineKeyboardButton(
            t(context, "checkout", amount=total_cost),
            callback_data="checkout",
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            t(context, "back"),
            callback_data="main_menu",
        )
    ])

    text = (
        f"{t(context, 'select_title')}\n\n"
        f"{t(context, 'select_help')}\n\n"
        f"{t(context, 'selected', count=len(context.user_data['my_selection']))}\n"
        f"{t(context, 'total', amount=total_cost)}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def toggle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    number = int(query.data.split("_")[1])
    selected = context.user_data.setdefault("my_selection", [])

    if number in selected:
        selected.remove(number)

    elif not is_unavailable(number):
        selected.append(number)

    else:
        await query.answer(t(context, "taken_alert"), show_alert=True)
        return

    # Refresh the grid without answering the callback twice.
    await render_grid(query, context)


async def render_grid(query, context):
    selected = context.user_data.setdefault("my_selection", [])
    keyboard = []

    for row in range(10):
        row_buttons = []

        for col in range(1, 11):
            number = row * 10 + col

            if number in game_data["numbers"]:
                button_text = f"❌{number}"
                callback = "taken"

            elif number in selected:
                button_text = f"✅{number}"
                callback = f"toggle_{number}"

            elif is_unavailable(number):
                button_text = f"⏳{number}"
                callback = "taken"

            else:
                button_text = str(number)
                callback = f"toggle_{number}"

            row_buttons.append(
                InlineKeyboardButton(button_text, callback_data=callback)
            )

        keyboard.append(row_buttons)

    total_cost = len(selected) * NUMBER_PRICE

    keyboard.append([
        InlineKeyboardButton(
            t(context, "checkout", amount=total_cost),
            callback_data="checkout",
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            t(context, "back"),
            callback_data="main_menu",
        )
    ])

    text = (
        f"{t(context, 'select_title')}\n\n"
        f"{t(context, 'select_help')}\n\n"
        f"{t(context, 'selected', count=len(selected))}\n"
        f"{t(context, 'total', amount=total_cost)}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def taken_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer(
        t(context, "taken_alert"),
        show_alert=True,
    )


# =====================================================
# CHECKOUT
# =====================================================

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = context.user_data.get("my_selection", [])

    if not selected:
        await query.answer(t(context, "empty_selection"), show_alert=True)
        return

    # Verify availability again before checkout.
    if any(is_unavailable(number) for number in selected):
        context.user_data["my_selection"] = []
        await query.edit_message_text(
            t(context, "selection_conflict"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    t(context, "back"),
                    callback_data="view_grid",
                )]
            ]),
        )
        return

    total_cost = len(selected) * NUMBER_PRICE

    await query.edit_message_text(
        f"{t(context, 'checkout_title')}\n\n"
        f"🎟️ {', '.join(map(str, selected))}\n"
        f"💰 *{total_cost} Birr*\n\n"
        f"{t(context, 'enter_name')}",
        parse_mode="Markdown",
    )

    context.user_data["step"] = "awaiting_name"


# =====================================================
# CUSTOMER NAME AND PHONE INPUT
# =====================================================

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")

    if not step:
        return

    message_text = update.message.text.strip()

    if not message_text:
        await update.message.reply_text(t(context, "name_empty"))
        return

    if step == "awaiting_name":
        context.user_data["temp_name"] = message_text
        context.user_data["step"] = "awaiting_phone"

        await update.message.reply_text(
            f"{t(context, 'thank_you', name=message_text)}\n\n"
            f"{t(context, 'enter_phone')}",
        )
        return

    if step == "awaiting_phone":
        name = context.user_data.get("temp_name", "Unknown")
        phone = message_text
        selected = sorted(context.user_data.get("my_selection", []))

        if not selected:
            context.user_data["step"] = None
            await update.message.reply_text(t(context, "empty_selection"))
            return

        # Recheck availability before creating the order.
        if any(is_unavailable(number) for number in selected):
            context.user_data["step"] = None
            context.user_data["my_selection"] = []
            await update.message.reply_text(t(context, "selection_conflict"))
            return

        total_cost = len(selected) * NUMBER_PRICE

        # Unique order ID: avoids long callback data and parsing errors.
        order_id = str(uuid.uuid4())

        game_data["pending_orders"][order_id] = {
            "user_id": update.effective_user.id,
            "name": name,
            "phone": phone,
            "numbers": selected,
            "amount": total_cost,
            "status": "pending",
            "created_at": datetime.now(TIMEZONE).isoformat(),
        }

        invoice = t(
            context,
            "invoice",
            name=name,
            phone=phone,
            numbers=", ".join(map(str, selected)),
            amount=total_cost,
            cbe=CBE_ACCOUNT,
            telebirr=TELEBIRR_NUMBER,
            cbebirr=CBEBIRR_NUMBER,
            channel=SUPPORT_CHANNEL,
        )

        await update.message.reply_text(invoice, parse_mode="Markdown")

        # -------------------------------------------------
        # NOTIFICATION TO SUPPORT CHANNEL
        # -------------------------------------------------

        channel_text = (
            "🚨 *NEW PAYMENT VERIFICATION REQUEST* 🚨\n\n"
            f"👤 Name: {name}\n"
            f"🎟️ Numbers: {', '.join(map(str, selected))}\n"
            f"💰 Amount: {total_cost} Birr\n"
            f"🆔 User ID: {update.effective_user.id}\n"
            f"📋 Order ID: `{order_id}`\n\n"
            "📸 Awaiting payment screenshot.\n"
            "👇 Verify the payment and approve below."
        )

        approve_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Approve Payment",
                    callback_data=f"approve:{order_id}",
                )
            ]
        ])

        try:
            await context.bot.send_message(
                chat_id=SUPPORT_CHANNEL,
                text=channel_text,
                reply_markup=approve_keyboard,
                parse_mode="Markdown",
            )

        except Exception as error:
            logger.exception("Failed to notify support channel")

            # Fallback notification to the Host privately.
            await context.bot.send_message(
                chat_id=HOST_TELEGRAM_ID,
                text=(
                    "⚠️ *CHANNEL NOTIFICATION FAILED*\n\n"
                    f"Error: {error}\n\n"
                    f"{channel_text}"
                ),
                reply_markup=approve_keyboard,
                parse_mode="Markdown",
            )

        await update.message.reply_text(
            t(context, "order_sent", channel=SUPPORT_CHANNEL)
        )

        # Clear checkout state, but keep language preference.
        context.user_data["step"] = None
        context.user_data["my_selection"] = []
        context.user_data.pop("temp_name", None)


# =====================================================
# HOST PAYMENT APPROVAL
# =====================================================

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Only the authorized Host can approve payments.
    if query.from_user.id != HOST_TELEGRAM_ID:
        await query.answer(t(context, "not_host"), show_alert=True)
        return

    await query.answer("Processing approval...")

    order_id = query.data.split(":", 1)[1]
    order = game_data["pending_orders"].get(order_id)

    if not order:
        await query.answer(t(context, "order_missing"), show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer(t(context, "already_processed"), show_alert=True)
        return

    numbers = order["numbers"]

    # Final availability check.
    if any(number in game_data["numbers"] for number in numbers):
        await query.edit_message_text(
            query.message.text + "\n\n❌ APPROVAL FAILED: Number conflict.",
        )
        order["status"] = "conflict"
        return

    # Lock numbers permanently as sold.
    for number in numbers:
        game_data["numbers"][number] = {
            "user_id": order["user_id"],
            "name": order["name"],
            "phone": order["phone"],
            "order_id": order_id,
        }

    order["status"] = "approved"
    order["approved_at"] = datetime.now(TIMEZONE).isoformat()

    # Update original channel notification.
    try:
        await query.edit_message_text(
            query.message.text + "\n\n✅ *PAYMENT APPROVED BY HOST*",
            parse_mode="Markdown",
            reply_markup=None,
        )
    except Exception:
        logger.exception("Could not update channel approval message")

    # Notify customer in their selected language.
    user_lang = "en"

    try:
        # User language is not available from the Host's context.
        # Retrieve it from the order when available in future database version.
        user_text = LANGUAGES[user_lang]["payment_confirmed"].format(
            numbers=", ".join(map(str, numbers))
        )

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=user_text,
            parse_mode="Markdown",
        )

    except Exception:
        logger.exception("Could not notify customer of approval")

    await query.message.reply_text(t(context, "approved"))

    # -------------------------------------------------
    # LIVE SALES UPDATE TO CHANNEL
    # -------------------------------------------------

    sold = len(game_data["numbers"])
    reserved = get_pending_number_count()
    remaining = TOTAL_NUMBERS - sold - reserved

    sales_text = (
        "🔥 *KOSHKOSH LIVE SALES UPDATE* 🔥\n\n"
        f"🟢 Numbers Sold: *{sold} / 100*\n"
        f"🟡 Pending Reservations: *{reserved}*\n"
        f"🔴 Available Numbers: *{remaining}*\n\n"
        f"👉 {BOT_USERNAME}"
    )

    try:
        await context.bot.send_message(
            chat_id=SUPPORT_CHANNEL,
            text=sales_text,
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Failed to send live sales update")

    # -------------------------------------------------
    # SOLD-OUT NOTIFICATION
    # -------------------------------------------------

    if sold == TOTAL_NUMBERS:
        sold_out_message = (
            "🚨 *ALL 100 NUMBERS HAVE BEEN SOLD!* 🚨\n\n"
            "The KoshKosh game is now fully sold out.\n"
            "The Host will announce the draw after the required waiting period."
        )

        await context.bot.send_message(
            chat_id=HOST_TELEGRAM_ID,
            text=sold_out_message,
            parse_mode="Markdown",
        )

        await context.bot.send_message(
            chat_id=SUPPORT_CHANNEL,
            text=sold_out_message,
            parse_mode="Markdown",
        )


# =====================================================
# SELECTION BOARD
# =====================================================

async def show_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sold = len(game_data["numbers"])
    reserved = get_pending_number_count()
    remaining = TOTAL_NUMBERS - sold - reserved

    text = (
        f"{t(context, 'board_title')}\n\n"
        f"⏰ Selection Window: 3:30 AM – 9:00 PM EAT\n"
        f"{t(context, 'sold', sold=sold)}\n"
        f"{t(context, 'reserved', reserved=reserved)}\n"
        f"{t(context, 'remaining', remaining=remaining)}\n"
    )

    if game_data["extensions"] > 0:
        text += (
            f"\n⚠️ Selection extended by "
            f"{game_data['extensions']} hour(s)."
        )

    keyboard = [
        [
            InlineKeyboardButton(
                t(context, "refresh"),
                callback_data="show_board",
            )
        ],
        [
            InlineKeyboardButton(
                t(context, "back"),
                callback_data="main_menu",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =====================================================
# GAME RULES
# =====================================================

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[
        InlineKeyboardButton(
            t(context, "back"),
            callback_data="main_menu",
        )
    ]]

    await query.edit_message_text(
        t(context, "rules_text"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =====================================================
# HOST DRAW COMMAND
# =====================================================

async def execute_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID:
        await update.message.reply_text(t(context, "not_host"))
        return

    if game_data["draw_completed"]:
        await update.message.reply_text(t(context, "draw_already_done"))
        return

    if len(game_data["numbers"]) < TOTAL_NUMBERS:
        await update.message.reply_text(t(context, "draw_not_ready"))
        return

    available_numbers = list(game_data["numbers"].keys())

    winning_numbers = random.sample(available_numbers, 3)

    winners = [
        game_data["numbers"][number]
        for number in winning_numbers
    ]

    # Public announcement does not expose full phone numbers.
    announcement = LANGUAGES["en"]["draw_results"].format(
        name1=winners[0]["name"],
        number1=winning_numbers[0],
        name2=winners[1]["name"],
        number2=winning_numbers[1],
        name3=winners[2]["name"],
        number3=winning_numbers[2],
    )

    # Host receives private winner contact details.
    private_host_report = (
        "🔐 *PRIVATE HOST WINNER REPORT*\n\n"
        f"🥇 1st: {winners[0]['name']}\n"
        f"📞 {winners[0]['phone']}\n"
        f"🔢 Number: {winning_numbers[0]}\n\n"
        f"🥈 2nd: {winners[1]['name']}\n"
        f"📞 {winners[1]['phone']}\n"
        f"🔢 Number: {winning_numbers[1]}\n\n"
        f"🥉 3rd: {winners[2]['name']}\n"
        f"📞 {winners[2]['phone']}\n"
        f"🔢 Number: {winning_numbers[2]}"
    )

    game_data["draw_completed"] = True

    # Host command response.
    await update.message.reply_text(
        announcement,
        parse_mode="Markdown",
    )

    # Public channel announcement.
    await context.bot.send_message(
        chat_id=SUPPORT_CHANNEL,
        text=announcement,
        parse_mode="Markdown",
    )

    # Private Host report.
    await context.bot.send_message(
        chat_id=HOST_TELEGRAM_ID,
        text=private_host_report,
        parse_mode="Markdown",
    )


# =====================================================
# HOST COMMAND: SALES STATUS
# =====================================================

async def host_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID:
        await update.message.reply_text(t(context, "not_host"))
        return

    sold = len(game_data["numbers"])
    reserved = get_pending_number_count()
    remaining = TOTAL_NUMBERS - sold - reserved

    await update.message.reply_text(
        "📊 *KOSHKOSH HOST STATUS*\n\n"
        f"🟢 Sold: {sold}/100\n"
        f"🟡 Pending: {reserved}\n"
        f"🔴 Available: {remaining}\n"
        f"📋 Pending orders: "
        f"{sum(1 for o in game_data['pending_orders'].values() if o['status'] == 'pending')}\n"
        f"🏆 Draw completed: {game_data['draw_completed']}",
        parse_mode="Markdown",
    )


# =====================================================
# APPLICATION STARTUP
# =====================================================

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is missing!")
        return

    threading.Thread(
        target=run_web_server,
        daemon=True,
    ).start()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("draw", execute_draw))
    application.add_handler(CommandHandler("status", host_status))
    application.add_handler(CommandHandler("language", choose_language))

    # Main menu and language
    application.add_handler(
        CallbackQueryHandler(start, pattern="^main_menu$")
    )
    application.add_handler(
        CallbackQueryHandler(choose_language, pattern="^change_language$")
    )
    application.add_handler(
        CallbackQueryHandler(set_language, pattern="^lang_(en|am)$")
    )

    # Game functions
    application.add_handler(
        CallbackQueryHandler(view_grid, pattern="^view_grid$")
    )
    application.add_handler(
        CallbackQueryHandler(toggle_number, pattern="^toggle_")
    )
    application.add_handler(
        CallbackQueryHandler(checkout, pattern="^checkout$")
    )
    application.add_handler(
        CallbackQueryHandler(show_board, pattern="^show_board$")
    )
    application.add_handler(
        CallbackQueryHandler(show_rules, pattern="^show_rules$")
    )
    application.add_handler(
        CallbackQueryHandler(taken_number, pattern="^taken$")
    )

    # Host approval
    application.add_handler(
        CallbackQueryHandler(approve_payment, pattern="^approve:")
    )

    # Customer text input
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_input,
        )
    )

    logger.info("KoshKosh bilingual bot is starting...")

    application.run_polling()


if __name__ == "__main__":
    main()
