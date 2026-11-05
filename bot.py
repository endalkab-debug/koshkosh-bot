import os
import logging
import random
import threading
import uuid

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST_TELEGRAM_ID = 446176588
SUPPORT_CHANNEL = "@KoshKosh_Support"
BOT_TOKEN = os.getenv("BOT_TOKEN")

game_data = {
    "numbers": {},
    "extensions": 0,
    "pending_orders": {}
}

LANGUAGES = {
    "en": {
        "choose_language": "🌐 Please choose your language:",
        "language_button": "🌐 Change Language",
        "welcome_title": "🏺 *WELCOME TO KOSHKOSH LUCKY JAR* 🏺",
        "welcome_body": (
            "The digital KoshKosh game! 🇪🇹\n\n"
            "🎯 *How it works:*\n"
            "1️⃣ Pick your lucky numbers (1–100).\n"
            "2️⃣ Pay 100 Birr per number.\n"
            "3️⃣ The Host verifies your payment.\n"
            "4️⃣ 3 winners are drawn.\n\n"
            "🏆 *Prizes:*\n"
            "🥇 1st Place: 4,000 ETB\n"
            "🥈 2nd Place: 2,000 ETB\n"
            "🥉 3rd Place: 1,500 ETB\n\n"
            "👇 Tap a button below to begin:"
        ),
        "play": "🎟️ Play KoshKosh (Pick Numbers)",
        "board": "📊 View Selection Board",
        "rules": "ℹ️ Game Rules",
        "back": "🔙 Back to Menu",
        "select_title": "🎯 *SELECT YOUR NUMBERS*",
        "select_instructions": (
            "Tap numbers to select them. Tap again to deselect.\n"
            "❌ means the number is sold or pending approval."
        ),
        "selected": "🛒 *Currently Selected:* {count} numbers",
        "total": "💰 *Total Price:* {total} Birr",
        "checkout": "💰 Checkout ({total} Birr)",
        "empty_selection": "❌ You haven't selected any numbers!",
        "checkout_title": "🛒 *CHECKOUT (Step 1 of 2)*",
        "selected_numbers": "🎟️ Selected Numbers:",
        "total_amount": "💰 Total Amount:",
        "ask_name": (
            "Please enter your *Full Name*.\n"
            "(Example: `Endalkachew Abebe`)"
        ),
        "name_empty": "❌ Name cannot be empty. Please enter your full name.",
        "thanks_name": "Thank you, {name}.\n\nNow please enter your *Phone Number*.",
        "phone_example": "(Example: `0911223344`)",
        "phone_empty": "❌ Phone number cannot be empty. Please enter your phone number.",
        "invoice": (
            "🧾 *OFFICIAL INVOICE*\n\n"
            "👤 Name: {name}\n"
            "📞 Phone: {phone}\n"
            "🎟️ Numbers: {numbers}\n"
            "💰 Total: {total} Birr\n\n"
            "💳 *Payment Options:*\n"
            "🏦 CBE: 1000211559277\n"
            "📱 Telebirr: 0913550415\n"
            "📱 CBEBirr: 0913550415\n\n"
            "2. Send your payment screenshot to {channel}\n\n"
            "⏳ Status: PENDING APPROVAL\n"
            "Your numbers will be confirmed after the Host verifies payment."
        ),
        "payment_confirmed": (
            "🎉 *Payment Confirmed!*\n\n"
            "Your numbers ({numbers}) are officially locked in. Good luck!"
        ),
        "board_title": "📊 *KOSHKOSH SELECTION BOARD*",
        "selection_window": "⏰ Selection Window: 3:30 AM – 9:00 PM",
        "numbers_selected": "🟢 Numbers Selected: *{sold} / 100*",
        "numbers_remaining": "🔴 Remaining Numbers: *{remaining}*",
        "extended": "⚠️ 9:00 PM reached! Extended by {hours} hour(s).",
        "refresh": "🔄 Refresh Board",
        "rules_text": (
            "📖 *KOSHKOSH GAME RULES*\n\n"
            "1️⃣ *The Jackpot:* 100 numbers are available. Each costs 100 Birr.\n"
            "2️⃣ *Selection:* Tap buttons to pick your numbers.\n"
            "3️⃣ *Payment:* Transfer the total and send your screenshot.\n"
            "4️⃣ *Approval:* The Host verifies payment and confirms your numbers.\n"
            "5️⃣ *The Draw:* Once all 100 numbers are sold, a 30-minute timer starts.\n"
            "6️⃣ *Winners:* 3 numbers are drawn. Prizes are 4,000, 2,000 and 1,500 ETB.\n"
            "7️⃣ *Time Limit:* Selection closes at 9:00 PM EAT. If not sold out, "
            "it extends by 1 hour."
        ),
        "sold_alert": "❌ This number is already sold or pending approval!",
        "draw_not_full": "❌ Cannot draw. Numbers are not fully sold.",
        "draw_full_notice": "🚨 ALL 100 SOLD! Wait 30 minutes, then type /draw.",
        "draw_results": "🎉 *KOSHKOSH DRAW RESULTS!* 🎉",
        "first": "🥇 *1st Place (4,000 ETB)*",
        "second": "🥈 *2nd Place (2,000 ETB)*",
        "third": "🥉 *3rd Place (1,500 ETB)*",
        "winner_notice": "📢 *NOTICE:* Winners, please send your bank account number to the Host!",
        "live_sales": (
            "🔥 *LIVE SALES UPDATE*\n\n"
            "🟢 Numbers Sold: *{sold} / 100*\n"
            "🔴 Remaining: *{remaining}*\n\n"
            "👉 @KoshKosh_LuckyJar_bot"
        ),
        "approved": "✅ APPROVED BY HOST.",
        "approval_conflict": "⚠️ Approval cancelled: one or more numbers are no longer available.",
        "language_saved": "✅ Language updated to English."
    },
    "am": {
        "choose_language": "🌐 እባክዎ ቋንቋዎን ይምረጡ:",
        "language_button": "🌐 ቋንቋ ቀይር",
        "welcome_title": "🏺 *እንኳን ወደ ኮሽኮሽ ዕድለኛ ማሰሮ በደህና መጡ* 🏺",
        "welcome_body": (
            "የኮሽኮሽ ዲጂታል ጨዋታ! 🇪🇹\n\n"
            "🎯 *እንዴት ይጫወታሉ?*\n"
            "1️⃣ ከ1–100 የዕድል ቁጥሮችን ይምረጡ።\n"
            "2️⃣ ለእያንዳንዱ ቁጥር 100 ብር ይክፈሉ።\n"
            "3️⃣ አስተናጋጁ ክፍያዎን ያረጋግጣል።\n"
            "4️⃣ 3 አሸናፊዎች ይወጣሉ።\n\n"
            "🏆 *ሽልማቶች:*\n"
            "🥇 1ኛ ደረጃ: 4,000 ብር\n"
            "🥈 2ኛ ደረጃ: 2,000 ብር\n"
            "🥉 3ኛ ደረጃ: 1,500 ብር\n\n"
            "👇 ለመጀመር ከታች ያለውን ይጫኑ:"
        ),
        "play": "🎟️ ኮሽኮሽ ይጫወቱ (ቁጥር ይምረጡ)",
        "board": "📊 የቁጥር ምርጫ ሰሌዳ",
        "rules": "ℹ️ የጨዋታ ህጎች",
        "back": "🔙 ወደ ዋናው ማውጫ",
        "select_title": "🎯 *ቁጥሮችዎን ይምረጡ*",
        "select_instructions": (
            "ቁጥሮችን ለመምረጥ ይጫኑ። እንደገና በመጫን ምርጫውን ያስወግዱ።\n"
            "❌ ማለት ቁጥሩ ተሽጧል ወይም ማረጋገጫ እየጠበቀ ነው።"
        ),
        "selected": "🛒 *የመረጧቸው ቁጥሮች:* {count}",
        "total": "💰 *ጠቅላላ ዋጋ:* {total} ብር",
        "checkout": "💰 ክፍያ ({total} ብር)",
        "empty_selection": "❌ ምንም ቁጥር አልመረጡም!",
        "checkout_title": "🛒 *ክፍያ (ደረጃ 1 ከ2)*",
        "selected_numbers": "🎟️ የተመረጡ ቁጥሮች:",
        "total_amount": "💰 ጠቅላላ ክፍያ:",
        "ask_name": "እባክዎ *ሙሉ ስምዎን* ይጻፉ።\n(ምሳሌ: `Endalkachew Abebe`)",
        "name_empty": "❌ ስም ባዶ መሆን አይችልም። ሙሉ ስምዎን ያስገቡ።",
        "thanks_name": "እናመሰግናለን {name}።\n\nአሁን *ስልክ ቁጥርዎን* ያስገቡ።",
        "phone_example": "(ምሳሌ: `0911223344`)",
        "phone_empty": "❌ ስልክ ቁጥር ባዶ መሆን አይችልም። ያስገቡ።",
        "invoice": (
            "🧾 *የክፍያ ደረሰኝ*\n\n"
            "👤 ስም: {name}\n"
            "📞 ስልክ: {phone}\n"
            "🎟️ ቁጥሮች: {numbers}\n"
            "💰 ጠቅላላ: {total} ብር\n\n"
            "💳 *የክፍያ አማራጮች:*\n"
            "🏦 CBE: 1000211559277\n"
            "📱 Telebirr: 0913550415\n"
            "📱 CBEBirr: 0913550415\n\n"
            "2. የክፍያ ስክሪንሾት ወደ {channel} ይላኩ።\n\n"
            "⏳ ሁኔታ: ማረጋገጫ እየጠበቀ ነው\n"
            "አስተናጋጁ ክፍያዎን ካረጋገጠ በኋላ ቁጥሮችዎ ይረጋገጣሉ።"
        ),
        "payment_confirmed": (
            "🎉 *ክፍያዎ ተረጋግጧል!*\n\n"
            "ቁጥሮችዎ ({numbers}) በይፋ ተመዝግበዋል። መልካም ዕድል!"
        ),
        "board_title": "📊 *የኮሽኮሽ ቁጥር ምርጫ ሰሌዳ*",
        "selection_window": "⏰ የምርጫ ጊዜ: ከጠዋቱ 3:30 – ከምሽቱ 9:00",
        "numbers_selected": "🟢 የተመረጡ ቁጥሮች: *{sold} / 100*",
        "numbers_remaining": "🔴 የቀሩ ቁጥሮች: *{remaining}*",
        "extended": "⚠️ 9:00 ደርሷል! በ{hours} ሰዓት ተራዝሟል።",
        "refresh": "🔄 ሰሌዳውን አድስ",
        "rules_text": (
            "📖 *የኮሽኮሽ ጨዋታ ህጎች*\n\n"
            "1️⃣ *ቁጥሮች:* 100 ቁጥሮች ይገኛሉ። እያንዳንዱ 100 ብር ነው።\n"
            "2️⃣ *ምርጫ:* ቁጥሮችን ለመምረጥ የቁጥር ቁልፎችን ይጫኑ።\n"
            "3️⃣ *ክፍያ:* ጠቅላላውን ወደ አስተናጋጁ ሂሳብ ያስተላልፉና ስክሪንሾት ይላኩ።\n"
            "4️⃣ *ማረጋገጫ:* አስተናጋጁ ክፍያውን አረጋግጦ ቁጥሮችዎን ያስመዘግባል።\n"
            "5️⃣ *ዕጣ:* 100 ቁጥሮች ሲሸጡ የ30 ደቂቃ ቆጣሪ ይጀምራል።\n"
            "6️⃣ *አሸናፊዎች:* 3 ቁጥሮች ይወጣሉ። ሽልማቶች 4,000፣ 2,000 እና 1,500 ብር ናቸው።\n"
            "7️⃣ *የጊዜ ገደብ:* ምርጫው ከምሽቱ 9:00 ይዘጋል። ሁሉም ካልተሸጡ በ1 ሰዓት ይራዘማል።"
        ),
        "sold_alert": "❌ ይህ ቁጥር ተሽጧል ወይም ማረጋገጫ እየጠበቀ ነው!",
        "draw_not_full": "❌ ዕጣ ማውጣት አይቻልም። ሁሉም ቁጥሮች አልተሸጡም።",
        "draw_full_notice": "🚨 100ቱም ተሽጠዋል! 30 ደቂቃ ይጠብቁና /draw ይጻፉ።",
        "draw_results": "🎉 *የኮሽኮሽ ዕጣ ውጤቶች!* 🎉",
        "first": "🥇 *1ኛ ደረጃ (4,000 ብር)*",
        "second": "🥈 *2ኛ ደረጃ (2,000 ብር)*",
        "third": "🥉 *3ኛ ደረጃ (1,500 ብር)*",
        "winner_notice": "📢 *ማሳሰቢያ:* አሸናፊዎች የባንክ ሂሳባችሁን ለአስተናጋጁ ይላኩ!",
        "live_sales": (
            "🔥 *የቀጥታ ሽያጭ ማሻሻያ*\n\n"
            "🟢 የተሸጡ: *{sold} / 100*\n"
            "🔴 የቀሩ: *{remaining}*\n\n"
            "👉 @KoshKosh_LuckyJar_bot"
        ),
        "approved": "✅ በአስተናጋጁ ተረጋግጧል።",
        "approval_conflict": "⚠️ ማረጋገጫው ተሰርዟል፤ አንዳንድ ቁጥሮች ከእንግዲህ በኋላ አይገኙም።",
        "language_saved": "✅ ቋንቋው ወደ አማርኛ ተቀይሯል።"
    }
}

def t(context, key, **kwargs):
    lang = context.user_data.get("language", "en")
    template = LANGUAGES.get(lang, LANGUAGES["en"]).get(key, key)
    return template.format(**kwargs)

def get_lang_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am")
        ]
    ])

def get_main_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "play"), callback_data="view_grid")],
        [InlineKeyboardButton(t(context, "board"), callback_data="show_board")],
        [InlineKeyboardButton(t(context, "rules"), callback_data="show_rules")],
        [InlineKeyboardButton(t(context, "language_button"), callback_data="choose_language")]
    ])

def get_back_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]
    ])

def is_unavailable(num):
    if num in game_data["numbers"]:
        return True
    return any(
        num in order["numbers"]
        for order in game_data["pending_orders"].values()
    )

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "KoshKosh Bot is running!"

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    saved_language = context.user_data.get("language")
    context.user_data.clear()
    if saved_language:
        context.user_data["language"] = saved_language

    if not context.user_data.get("language"):
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "🌐 Choose your language / ቋንቋ ይምረጡ:",
                reply_markup=get_lang_keyboard()
            )
        else:
            await update.message.reply_text(
                "🌐 Choose your language / ቋንቋ ይምረጡ:",
                reply_markup=get_lang_keyboard()
            )
        return

    await show_main_menu(update, context)

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🌐 Choose your language / ቋንቋ ይምረጡ:",
            reply_markup=get_lang_keyboard()
        )
    else:
        await update.message.reply_text(
            "🌐 Choose your language / ቋንቋ ይምረጡ:",
            reply_markup=get_lang_keyboard()
        )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = query.data.split("_")[1]
    context.user_data["language"] = lang
    context.user_data.pop("step", None)
    context.user_data.pop("my_selection", None)
    context.user_data.pop("temp_name", None)

    await query.answer()
    await query.edit_message_text(
        t(context, "language_saved"),
        reply_markup=get_back_keyboard(context)
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = t(context, "welcome_title") + "\n\n" + t(context, "welcome_body")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, reply_markup=get_main_keyboard(context), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=get_main_keyboard(context), parse_mode="Markdown"
        )

async def view_grid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "my_selection" not in context.user_data:
        context.user_data["my_selection"] = []

    keyboard = []
    for row in range(10):
        row_buttons = []
        for col in range(1, 11):
            num = row * 10 + col
            if is_unavailable(num):
                btn_text = f"❌{num}"
                callback = "taken"
            elif num in context.user_data["my_selection"]:
                btn_text = f"✅{num}"
                callback = f"toggle_{num}"
            else:
                btn_text = str(num)
                callback = f"toggle_{num}"
            row_buttons.append(
                InlineKeyboardButton(btn_text, callback_data=callback)
            )
        keyboard.append(row_buttons)

    total_cost = len(context.user_data["my_selection"]) * 100
    keyboard.append([
        InlineKeyboardButton(
            t(context, "checkout", total=total_cost),
            callback_data="checkout"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(t(context, "back"), callback_data="main_menu")
    ])

    text = (
        t(context, "select_title") + "\n\n" +
        t(context, "select_instructions") + "\n\n" +
        t(context, "selected", count=len(context.user_data["my_selection"])) + "\n" +
        t(context, "total", total=total_cost)
    )

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def toggle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    num = int(query.data.split("_")[1])

    if is_unavailable(num):
        await query.answer(t(context, "sold_alert"), show_alert=True)
        return

    selection = context.user_data.setdefault("my_selection", [])
    if num in selection:
        selection.remove(num)
    else:
        selection.append(num)

    await view_grid(update, context)

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selection = context.user_data.get("my_selection", [])
    if not selection:
        await query.answer(t(context, "empty_selection"), show_alert=True)
        return

    unavailable = [n for n in selection if is_unavailable(n)]
    if unavailable:
        context.user_data["my_selection"] = [
            n for n in selection if n not in unavailable
        ]
        await query.answer(t(context, "sold_alert"), show_alert=True)
        await view_grid(update, context)
        return

    total = len(selection) * 100
    await query.edit_message_text(
        f"{t(context, 'checkout_title')}\n\n"
        f"{t(context, 'selected_numbers')} {', '.join(map(str, selection))}\n"
        f"{t(context, 'total_amount')} *{total} Birr*\n\n"
        f"{t(context, 'ask_name')}",
        parse_mode="Markdown"
    )
    context.user_data["step"] = "awaiting_name"

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    if not step:
        return

    text = update.message.text.strip()
    selection = context.user_data.get("my_selection", [])
    total = len(selection) * 100

    if step == "awaiting_name":
        if not text:
            await update.message.reply_text(t(context, "name_empty"))
            return

        context.user_data["temp_name"] = text
        await update.message.reply_text(
            t(context, "thanks_name", name=text) + "\n" +
            t(context, "phone_example"),
            parse_mode="Markdown"
        )
        context.user_data["step"] = "awaiting_phone"

    elif step == "awaiting_phone":
        if not text:
            await update.message.reply_text(t(context, "phone_empty"))
            return

        unavailable = [n for n in selection if is_unavailable(n)]
        if unavailable:
            context.user_data["step"] = None
            context.user_data["my_selection"] = [
                n for n in selection if n not in unavailable
            ]
            await update.message.reply_text(t(context, "sold_alert"))
            return

        name = context.user_data.get("temp_name", "Unknown")
        phone = text
        order_id = uuid.uuid4().hex[:12]

        order = {
            "user_id": update.effective_user.id,
            "name": name,
            "phone": phone,
            "numbers": list(selection),
            "total": total,
            "language": context.user_data.get("language", "en")
        }
        game_data["pending_orders"][order_id] = order

        invoice = t(
            context, "invoice",
            name=name,
            phone=phone,
            numbers=", ".join(map(str, selection)),
            total=total,
            channel=SUPPORT_CHANNEL
        )
        await update.message.reply_text(invoice, parse_mode="Markdown")

        channel_text = (
            "🚨 NEW PAYMENT VERIFICATION NEEDED 🚨\n\n"
            f"👤 Name: {name}\n"
            f"🎟️ Numbers: {', '.join(map(str, selection))}\n"
            f"💰 Amount: {total} Birr\n"
            f"🆔 User ID: {update.effective_user.id}\n"
            f"🌐 Language: {order['language']}\n\n"
            "👇 Awaiting screenshot. Click below to approve:"
        )
        approve_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✅ Approve Payment",
                callback_data=f"approve_{order_id}"
            )]
        ])

        try:
            await context.bot.send_message(
                chat_id=SUPPORT_CHANNEL,
                text=channel_text,
                reply_markup=approve_btn
            )
        except Exception as e:
            logger.error("Failed to send to channel: %s", e)
            await context.bot.send_message(
                chat_id=HOST_TELEGRAM_ID,
                text="⚠️ Channel error.\n\n" + channel_text,
                reply_markup=approve_btn
            )

        context.user_data["step"] = None
        context.user_data["my_selection"] = []
        context.user_data.pop("temp_name", None)

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != HOST_TELEGRAM_ID:
        await query.answer("Only the Host can approve payments.", show_alert=True)
        return

    await query.answer("Processing approval...")
    order_id = query.data.replace("approve_", "", 1)
    order = game_data["pending_orders"].get(order_id)

    if not order:
        await query.answer("Order not found or already processed.", show_alert=True)
        return

    numbers = order["numbers"]

    if any(n in game_data["numbers"] for n in numbers):
        await query.edit_message_text(
            query.message.text + "\n\n⚠️ CONFLICT: Numbers already sold."
        )
        game_data["pending_orders"].pop(order_id, None)
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=LANGUAGES[order["language"]]["approval_conflict"]
        )
        return

    for n in numbers:
        game_data["numbers"][n] = {
            "user_id": order["user_id"],
            "name": order["name"],
            "phone": order["phone"]
        }

    game_data["pending_orders"].pop(order_id, None)

    await query.edit_message_text(
        query.message.text + "\n\n" + LANGUAGES["en"]["approved"],
        reply_markup=None
    )

    lang = order["language"]
    await context.bot.send_message(
        chat_id=order["user_id"],
        text=LANGUAGES[lang]["payment_confirmed"].format(
            numbers=", ".join(map(str, numbers))
        ),
        parse_mode="Markdown"
    )

    sold = len(game_data["numbers"])
    remaining = 100 - sold
    sales_text = LANGUAGES["en"]["live_sales"].format(
        sold=sold, remaining=remaining
    )

    try:
        await context.bot.send_message(
            chat_id=SUPPORT_CHANNEL,
            text=sales_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error("Failed to send sales update: %s", e)

    if sold == 100:
        notice = LANGUAGES["en"]["draw_full_notice"]
        await context.bot.send_message(
            chat_id=HOST_TELEGRAM_ID, text=notice
        )
        await context.bot.send_message(
            chat_id=SUPPORT_CHANNEL, text=notice
        )

async def show_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sold = len(game_data["numbers"])
    remaining = 100 - sold

    text = (
        t(context, "board_title") + "\n\n" +
        t(context, "selection_window") + "\n" +
        t(context, "numbers_selected", sold=sold) + "\n" +
        t(context, "numbers_remaining", remaining=remaining) + "\n"
    )

    if game_data["extensions"] > 0:
        text += "\n" + t(
            context, "extended", hours=game_data["extensions"]
        )

    keyboard = [
        [InlineKeyboardButton(t(context, "refresh"), callback_data="show_board")],
        [InlineKeyboardButton(t(context, "back"), callback_data="main_menu")]
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        t(context, "rules_text"),
        reply_markup=get_back_keyboard(context),
        parse_mode="Markdown"
    )

async def execute_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID:
        return

    if len(game_data["numbers"]) < 100:
        await update.message.reply_text(
            LANGUAGES["en"]["draw_not_full"]
        )
        return

    available = list(game_data["numbers"].keys())
    win_nums = random.sample(available, 3)
    winners = [game_data["numbers"][n] for n in win_nums]

    announcement = (
        LANGUAGES["en"]["draw_results"] + "\n\n" +
        LANGUAGES["en"]["first"] + "\n"
        f"👤 {winners[0]['name']}\n"
        f"📞 {winners[0]['phone']}\n"
        f"🔢 {win_nums[0]}\n\n" +
        LANGUAGES["en"]["second"] + "\n"
        f"👤 {winners[1]['name']}\n"
        f"📞 {winners[1]['phone']}\n"
        f"🔢 {win_nums[1]}\n\n" +
        LANGUAGES["en"]["third"] + "\n"
        f"👤 {winners[2]['name']}\n"
        f"📞 {winners[2]['phone']}\n"
        f"🔢 {win_nums[2]}\n\n" +
        LANGUAGES["en"]["winner_notice"]
    )

    am_announcement = (
        LANGUAGES["am"]["draw_results"] + "\n\n" +
        LANGUAGES["am"]["first"] + "\n"
        f"👤 {winners[0]['name']}\n"
        f"📞 {winners[0]['phone']}\n"
        f"🔢 {win_nums[0]}\n\n" +
        LANGUAGES["am"]["second"] + "\n"
        f"👤 {winners[1]['name']}\n"
        f"📞 {winners[1]['phone']}\n"
        f"🔢 {win_nums[1]}\n\n" +
        LANGUAGES["am"]["third"] + "\n"
        f"👤 {winners[2]['name']}\n"
        f"📞 {winners[2]['phone']}\n"
        f"🔢 {win_nums[2]}\n\n" +
        LANGUAGES["am"]["winner_notice"]
    )

    await update.message.reply_text(announcement, parse_mode="Markdown")
    await context.bot.send_message(
        chat_id=SUPPORT_CHANNEL,
        text=announcement + "\n\n" + am_announcement,
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=HOST_TELEGRAM_ID,
        text=(
            f"🚨 Winners drawn! 1st: {winners[0]['name']}, "
            f"2nd: {winners[1]['name']}, 3rd: {winners[2]['name']}"
        )
    )

async def reset_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID:
        return
    
    game_data["numbers"].clear()
    game_data["pending_orders"].clear()
    game_data["extensions"] = 0
    
    await update.message.reply_text("🔄 *GAME RESET SUCCESSFUL!*\nAll numbers are now available again.", parse_mode="Markdown")
    try:
        await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text="🔄 The game has been reset by the Host. All numbers are available!")
    except:
        pass

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is missing.")
        return

    threading.Thread(target=run_web_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("draw", execute_draw))
    app.add_handler(CommandHandler("language", choose_language))
    app.add_handler(CommandHandler("reset", reset_game))

    app.add_handler(CallbackQueryHandler(choose_language, pattern="^choose_language$"))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_(en|am)$"))
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(view_grid, pattern="^view_grid$"))
    app.add_handler(CallbackQueryHandler(toggle_number, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    app.add_handler(CallbackQueryHandler(approve_payment, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(show_board, pattern="^show_board$"))
    app.add_handler(CallbackQueryHandler(show_rules, pattern="^show_rules$"))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: u.callback_query.answer(
            t(c, "sold_alert"), show_alert=True
        ),
        pattern="^taken$"
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_input
    ))

    logger.info("KoshKosh bilingual bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
