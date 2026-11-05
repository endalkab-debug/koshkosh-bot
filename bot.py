import os
import logging
import random
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
HOST_TELEGRAM_ID = 446176588  # Your Telegram ID is set here!
BOT_TOKEN = os.getenv('BOT_TOKEN')

# --- GAME DATA ---
game_data = {
    'status': 'open', 
    'numbers': {},    
    'extensions': 0
}

EAT = pytz.timezone('Africa/Addis_Ababa')

def get_eat_now():
    return datetime.now(EAT)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎟️ Pick Numbers", callback_data="pick_numbers")],
        [InlineKeyboardButton("📊 Selection Board", callback_data="board")],
        [InlineKeyboardButton("ℹ️ How to Play", callback_data="how_to_play")]
    ]
    await update.message.reply_text(
        "🎰 *Welcome to KoshKosh!*\n\n"
        "Every ticket is 100 Birr. Pick your lucky numbers (1-100).\n"
        "3 Winners will be drawn at the end!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def how_to_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *How to Play KoshKosh*\n\n"
        "1. Tap 'Pick Numbers'.\n"
        "2. Choose your numbers (1 to 100).\n"
        "3. Transfer the total amount to the Host's bank account.\n"
        "4. Send the screenshot to the Host on Telegram.\n"
        "5. The Host will verify and approve your numbers.\n"
        "6. Selection time: ከ ጠዋት 3:30 እስከ ከሰዐት 9:00\n"
        "7. Drawing happens 30 mins after all 100 numbers are sold."
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def selection_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
    keyboard = [[InlineKeyboardButton("🔄 Refresh Board", callback_data="board")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def pick_numbers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(game_data['numbers']) >= 100:
        await update.message.reply_text("❌ All 100 numbers are sold out! Wait for the draw.")
        return
    await update.message.reply_text("✍️ Type the numbers you want to buy, separated by commas. Example: `5, 12, 45`")
    context.user_data['awaiting_numbers'] = True

async def handle_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_numbers'): return
    context.user_data['awaiting_numbers'] = False
    text = update.message.text
    try:
        selected_numbers = [int(n.strip()) for n in text.split(',')]
        for n in selected_numbers:
            if n < 1 or n > 100: raise ValueError("Numbers must be 1-100.")
            if n in game_data['numbers']: raise ValueError(f"Number {n} is taken!")
            
        context.user_data['temp_numbers'] = selected_numbers
        await update.message.reply_text(f"✅ Numbers: *{selected_numbers}*\n\nSend your *Full Name* and *Phone*.\nFormat: `Name, Phone`", parse_mode='Markdown')
        context.user_data['awaiting_contact'] = True
    except ValueError as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_contact_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_contact'): return
    context.user_data['awaiting_contact'] = False
    text = update.message.text
    selected_numbers = context.user_data.get('temp_numbers')
    
    try:
        name, phone = text.split(',')
        name = name.strip(); phone = phone.strip()
    except:
        await update.message.reply_text("❌ Format incorrect. Use: `Name, Phone`")
        return
        
    await update.message.reply_text("🧾 Invoice created. Send screenshot to Host. Pending Approval.")
    
    # Notify Host
    host_text = (
        f"🚨 *New Request!*\n"
        f"User ID: `{update.effective_user.id}`\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Numbers: {selected_numbers}\n\n"
        f"Approve: `/approve {update.effective_user.id} {','.join(map(str, selected_numbers))} {name.replace(' ', '_')} {phone}`"
    )
    await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=host_text, parse_mode='Markdown')

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
        await context.bot.send_message(chat_id=user_id, text=f"🎉 *Approved!* Numbers registered.", parse_mode='Markdown')
        
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

def main():
    if not BOT_TOKEN: return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", host_approve))
    app.add_handler(CommandHandler("draw", execute_draw))
    app.add_handler(CallbackQueryHandler(pick_numbers_menu, pattern="^pick_numbers$"))
    app.add_handler(CallbackQueryHandler(selection_board, pattern="^board$"))
    app.add_handler(CallbackQueryHandler(how_to_play, pattern="^how_to_play$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, handle_number_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, handle_contact_input))
    app.run_polling()

if __name__ == '__main__':
    main()
