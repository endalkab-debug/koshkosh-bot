import os
import logging
import random
import threading
from datetime import datetime, timedelta
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST_TELEGRAM_ID = 446176588 
BOT_TOKEN = os.getenv('BOT_TOKEN')

game_data = {'numbers': {}, 'extensions': 0}

# --- WEB SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "KoshKosh Bot is running!"

def run_web_server():
    port = int(os.getenv('PORT', 8080))
    web_app.run(host='0.0.0.0', port=port, use_reloader=False)

# ==========================================
# 1. WELCOME SCREEN & MAIN MENU
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    welcome_text = (
        "🏺 *WELCOME TO KOSHKOSH LUCKY JAR* 🏺\n\n"
        "The most transparent digital KoshKosh game in Ethiopia! 🇪🇹\n\n"
        "🎯 *How it works:*\n"
        "1️⃣ Pick your lucky numbers (1-100).\n"
        "2️⃣ Pay 100 Birr per number.\n"
        "3️⃣ The Host verifies your payment.\n"
        "4️⃣ 3 Winners are drawn live!\n\n"
        "🏆 *Prizes:*\n"
        "🥇 1st Place: 4,000 ETB\n"
        "🥈 2nd Place: 2,000 ETB\n"
        "🥉 3rd Place: 1,500 ETB\n\n"
        "👇 *Tap a button below to begin:*"
    )
    keyboard = [
        [InlineKeyboardButton("🎟️ Play KoshKosh (Pick Numbers)", callback_data="view_grid")],
        [InlineKeyboardButton("📊 View Selection Board", callback_data="show_board")],
        [InlineKeyboardButton("ℹ️ Game Rules", callback_data="show_rules")]
    ]
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==========================================
# 2. INTERACTIVE NUMBER GRID
# ==========================================
async def view_grid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if 'my_selection' not in context.user_data:
        context.user_data['my_selection'] = []

    keyboard = []
    for row in range(10):
        row_buttons = []
        for col in range(1, 11):
            num = row * 10 + col
            if num in game_data['numbers']:
                btn_text = f"❌{num}"
                callback = "taken"
            elif num in context.user_data['my_selection']:
                btn_text = f"✅{num}"
                callback = f"toggle_{num}"
            else:
                btn_text = f"{num}"
                callback = f"toggle_{num}"
            row_buttons.append(InlineKeyboardButton(btn_text, callback_data=callback))
        keyboard.append(row_buttons)

    total_cost = len(context.user_data['my_selection']) * 100
    keyboard.append([InlineKeyboardButton(f"💰 Checkout ({total_cost} Birr)", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
    
    text = (
        "🎯 *SELECT YOUR NUMBERS*\n\n"
        "Tap the numbers you want to buy. They will turn ✅.\n"
        "Tap again to deselect.\n\n"
        f"🛒 *Currently Selected:* {len(context.user_data['my_selection'])} numbers\n"
        f"💰 *Total Price:* {total_cost} Birr\n\n"
        "❌ means the number is already sold."
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def toggle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    num = int(query.data.split('_')[1])
    my_selection = context.user_data.get('my_selection', [])
    if num in my_selection:
        my_selection.remove(num)
    else:
        my_selection.append(num)
    await view_grid(update, context)

# ==========================================
# 3. STEP-BY-STEP CHECKOUT
# ==========================================
async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    my_selection = context.user_data.get('my_selection', [])
    if not my_selection:
        await query.answer("❌ You haven't selected any numbers!", show_alert=True)
        return
        
    total_cost = len(my_selection) * 100
    
    await query.edit_message_text(
        f"🛒 *CHECKOUT (Step 1 of 2)*\n\n"
        f"🎟️ Selected Numbers: {', '.join(map(str, my_selection))}\n"
        f"💰 Total Amount: *{total_cost} Birr*\n\n"
        f"Please reply with your *Full Name*.\n"
        f"(Example: `Endalkachew Abebe`)",
        parse_mode='Markdown'
    )
    context.user_data['step'] = 'awaiting_name'

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')
    text = update.message.text.strip()
    my_selection = context.user_data.get('my_selection', [])
    total_cost = len(my_selection) * 100

    # STEP 1: Get Name
    if step == 'awaiting_name':
        if not text:
            await update.message.reply_text("❌ Name cannot be empty. Please enter your Full Name.")
            return
            
        context.user_data['temp_name'] = text
        await update.message.reply_text(
            f"Thank you, {text}.\n\n"
            f"Now please reply with your *Phone Number*.\n"
            f"(Example: `0911223344`)",
            parse_mode='Markdown'
        )
        context.user_data['step'] = 'awaiting_phone'

    # STEP 2: Get Phone & Finalize
    elif step == 'awaiting_phone':
        if not text:
            await update.message.reply_text("❌ Phone number cannot be empty. Please enter your phone number.")
            return
            
        name = context.user_data.get('temp_name', 'Unknown')
        phone = text
        safe_name = name.replace(' ', '_')
        
        invoice_text = (
            f"🧾 *OFFICIAL INVOICE*\n\n"
            f"👤 Name: {name}\n"
            f"📞 Phone: {phone}\n"
            f"🎟️ Numbers: {', '.join(map(str, my_selection))}\n"
            f"💰 Total: *{total_cost} Birr*\n\n"
            f"💳 *Payment Instructions:*\n"
            f"1. Transfer {total_cost} Birr to Commercial Bank of Ethiopia:\n"
            f"`1000123456789` (KoshKosh Official)\n\n"
            f"2. Send the payment screenshot to the Host: @KoshKosh_Support\n\n"
            f"⏳ *Status:* PENDING APPROVAL\n"
            f"Your numbers are reserved. The Host will verify your payment shortly."
        )
        
        await update.message.reply_text(invoice_text, parse_mode='Markdown')
        
        host_text = (
            f"🚨 *NEW PAYMENT VERIFICATION NEEDED*\n\n"
            f"👤 Name: {name}\n"
            f"📞 Phone: {phone}\n"
            f"🎟️ Numbers: {', '.join(map(str, my_selection))}\n"
            f"💰 Amount: {total_cost} Birr\n"
            f"🆔 User ID: `{update.effective_user.id}`\n\n"
            f"👇 Click to copy the approval command:\n"
            f"`/approve {update.effective_user.id} {','.join(map(str, my_selection))} {safe_name} {phone}`"
        )
        await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=host_text, parse_mode='Markdown')
        
        # Clear state
        context.user_data['step'] = None
        context.user_data['my_selection'] = []
        context.user_data.pop('temp_name', None)

# ==========================================
# 4. SELECTION BOARD & RULES
# ==========================================
async def show_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_count = len(game_data['numbers'])
    remaining_count = 100 - selected_count
    text = (
        f"📊 *KOSHKOSH SELECTION BOARD*\n\n"
        f"⏰ Selection Window: ከ ጠዋት 3:30 እስከ ከሰዐት 9:00\n"
        f"🟢 Numbers Selected: *{selected_count} / 100*\n"
        f"🔴 Remaining Numbers: *{remaining_count}*\n\n"
    )
    if game_data['extensions'] > 0:
        text += f"⚠️ 9:00 Reached! Extended by {game_data['extensions']} hour(s).\n"
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Board", callback_data="show_board")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rules_text = (
        "📖 *KOSHKOSH GAME RULES*\n\n"
        "1️⃣ *The Jackpot:* 100 numbers are available. Each costs 100 Birr.\n"
        "2️⃣ *Selection:* Tap the buttons to pick your numbers.\n"
        "3️⃣ *Payment:* Transfer the total to the Host's CBE account and send the screenshot.\n"
        "4️⃣ *Approval:* The Host verifies the payment and locks in your numbers.\n"
        "5️⃣ *The Draw:* Once all 100 numbers are sold, a 30-minute timer starts.\n"
        "6️⃣ *Winners:* 3 numbers are drawn. 1st gets 4,000 ETB, 2nd gets 2,000 ETB, 3rd gets 1,500 ETB.\n"
        "7️⃣ *Time Limit:* Selection closes at 9:00 PM EAT. If not sold out, it extends by 1 hour."
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
    await query.edit_message_text(rules_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==========================================
# 5. HOST COMMANDS
# ==========================================
async def host_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID: return
    try:
        user_id = int(context.args[0])
        numbers = [int(n) for n in context.args[1].split(',')]
        name = context.args[2].replace('_', ' ')
        phone = context.args[3]
        for n in numbers:
            game_data['numbers'][n] = {'user_id': user_id, 'name': name, 'phone': phone}
        await update.message.reply_text(f"✅ Approved {len(numbers)} numbers for {name}.")
        await context.bot.send_message(chat_id=user_id, text=f"🎉 *Payment Confirmed!*\n\nYour numbers ({', '.join(map(str, numbers))}) are officially locked in. Good luck!", parse_mode='Markdown')
        if len(game_data['numbers']) == 100:
            await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text="🚨 *ALL 100 SOLD!* Wait 30 minutes, then type /draw.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error. Format: `/approve 123 5,6 Name 0911`")

async def execute_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID: return
    if len(game_data['numbers']) < 100:
        await update.message.reply_text("❌ Cannot draw. Numbers are not fully sold.")
        return
    available = list(game_data['numbers'].keys())
    win_nums = random.sample(available, 3)
    r1, r2, r3 = game_data['numbers'][win_nums[0]], game_data['numbers'][win_nums[1]], game_data['numbers'][win_nums[2]]
    announcement = (
        "🎉 *KOSHKOSH DRAW RESULTS!* 🎉\n\n"
        f"🥇 *1st Place (4,000 ETB)*\n👤 {r1['name']}\n📞 {r1['phone']}\n🔢 {win_nums[0]}\n\n"
        f"🥈 *2nd Place (2,000 ETB)*\n👤 {r2['name']}\n📞 {r2['phone']}\n🔢 {win_nums[1]}\n\n"
        f"🥉 *3rd Place (1,500 ETB)*\n👤 {r3['name']}\n📞 {r3['phone']}\n🔢 {win_nums[2]}\n\n"
        "📢 *NOTICE:* Winners, please send your bank account number to the Host!"
    )
    await update.message.reply_text(announcement, parse_mode='Markdown')
    await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=f"🚨 Winners drawn! 1st: {r1['name']}, 2nd: {r2['name']}, 3rd: {r3['name']}")

# --- MAIN ---
def main():
    if not BOT_TOKEN: return
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", host_approve))
    app.add_handler(CommandHandler("draw", execute_draw))
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(view_grid, pattern="^view_grid$"))
    app.add_handler(CallbackQueryHandler(toggle_number, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    app.add_handler(CallbackQueryHandler(show_board, pattern="^show_board$"))
    app.add_handler(CallbackQueryHandler(show_rules, pattern="^show_rules$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer("❌ Already sold!", show_alert=True), pattern="^taken$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, handle_text_input))
    logger.info("KoshKosh GUI Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
