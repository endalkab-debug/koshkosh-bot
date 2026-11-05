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
SUPPORT_CHANNEL = "@KoshKosh_Support" 
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
        "🏺 *እንኳን ወደ ኮሽኮሽ ላኪ ጃር በደህና መጡ!* 🏺\n\n"
        "በኢትዮጵያ በጣም ግልጽ የሆነው ዲጂታል ኮሽኮሽ ጨዋታ! 🇪🇹\n\n"
        "🎯 *እንዴት እንደሚሰራ:*\n"
        "1️⃣ እድለኛ ቁጥሮችዎን ይምረጡ (1-100)።\n"
        "2️⃣ ለአንድ ቁጥር 100 ብር ይክፈሉ።\n"
        "3️⃣ አስተናጋጁ (Host) ክፍያዎን ያረጋግጣል።\n"
        "4️⃣ 3 አሸናፊዎች በቀጥታ ይጣላሉ!\n\n"
        "🏆 *ሽልማቶች:*\n"
        "🥇 1ኛ ደረጃ: 4,000 ብር\n"
        "🥈 2ኛ ደረጃ: 2,000 ብር\n"
        "🥉 3ኛ ደረጃ: 1,500 ብር\n\n"
        "👇 *ለመጀመር ከታች ያለውን ቁልፍ ይጫኑ:*"
    )
    keyboard = [
        [InlineKeyboardButton("🎟️ ኮሽኮሽ ይጫወቱ (ቁጥር ይምረጡ)", callback_data="view_grid")],
        [InlineKeyboardButton("📊 የተመረጡ ቁጥሮች ሰሌዳ", callback_data="show_board")],
        [InlineKeyboardButton("ℹ️ የጨዋታ ደንቦች", callback_data="show_rules")]
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
    keyboard.append([InlineKeyboardButton(f"💰 ክፍያ ({total_cost} ብር)", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🔙 ወደ ዋና ማውጫ ተመለስ", callback_data="main_menu")])
    
    text = (
        "🎯 *ቁጥሮችዎን ይምረጡ*\n\n"
        "መግዛት የሚፈልጉትን ቁጥሮች ይጫኑ። ወደ ✅ ይቀየራሉ።\n"
        "ለመሰረዝ እንደገና ይጫኑ።\n\n"
        f"🛒 *በአሁኑ የተመረጡ:* {len(context.user_data['my_selection'])} ቁጥሮች\n"
        f"💰 *ጠቅላላ ዋጋ:* {total_cost} ብር\n\n"
        "❌ ማለት ቁጥሩ አስቀድሞ ተሽጧል ማለት ነው።"
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
        await query.answer("❌ ምንም ቁጥር አልመረጡም!", show_alert=True)
        return
        
    total_cost = len(my_selection) * 100
    
    await query.edit_message_text(
        f"🛒 *ክፍያ (ደረጃ 1 ከ 2)*\n\n"
        f"🎟️ የተመረጡ ቁጥሮች: {', '.join(map(str, my_selection))}\n"
        f"💰 ጠቅላላ መጠን: *{total_cost} ብር*\n\n"
        f"እባክዎ ሙሉ *ስምዎን* ይላኩ።\n"
        f"(ምሳሌ: `እንዳልካቸው አበበ`)",
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
            await update.message.reply_text("❌ ስም ባዶ መሆን አይችልም። እባክዎ ሙሉ ስምዎን ያስገቡ።")
            return
            
        context.user_data['temp_name'] = text
        await update.message.reply_text(
            f"አመሰግናለሁ, {text}።\n\n"
            f"አሁን እባክዎ የስልክ *ቁጥርዎን* ይላኩ።\n"
            f"(ምሳሌ: `0911223344`)",
            parse_mode='Markdown'
        )
        context.user_data['step'] = 'awaiting_phone'

    # STEP 2: Get Phone & Finalize
    elif step == 'awaiting_phone':
        if not text:
            await update.message.reply_text("❌ የስልክ ቁጥር ባዶ መሆን አይችልም። እባክዎ የስልክ ቁጥርዎን ያስገቡ።")
            return
            
        name = context.user_data.get('temp_name', 'Unknown')
        phone = text
        safe_name = name.replace(' ', '_')
        
        # 1. Send Invoice to User
        invoice_text = (
            f"🧾 የክፍያ መጠየቂያ\n\n"
            f"👤 ስም: {name}\n"
            f"📞 ስልክ: {phone}\n"
            f"🎟️ ቁጥሮች: {', '.join(map(str, my_selection))}\n"
            f"💰 ጠቅላላ: {total_cost} ብር\n\n"
            f"💳 የክፍያ አማራጮች:\n"
            f"🏦 CBE: 1000211559277\n"
            f"📱 ቴሌብር: 0913550415\n"
            f"📱 CBEብር: 0913550415\n\n"
            f"2. የክፍያ ስክሪንሾት (Screenshot) ወደ አስተናጋጅ ቻናል ይላኩ: {SUPPORT_CHANNEL}\n\n"
            f"⏳ ሁኔታ: በማረጋገጥ ላይ\n"
            f"ቁጥሮችዎ ተይዘዋል። አስተናጋጁ ክፍያዎን በቅርቡ ያረጋግጣል።"
        )
        await update.message.reply_text(invoice_text)
        
        # 2. Send Notification to CHANNEL
        channel_text = (
            f"🚨 አዲስ የክፍያ ማረጋገጫ ያስፈልጋል 🚨\n\n"
            f"👤 ስም: {name}\n"
            f"🎟️ ቁጥሮች: {', '.join(map(str, my_selection))}\n"
            f"💰 መጠን: {total_cost} ብር\n"
            f"🆔 የተጠቃሚ መለያ: {update.effective_user.id}\n\n"
            f"👇 ስክሪንሾት በመጠበቅ ላይ። ለማጽደቅ ከታች ይጫኑ:"
        )
        approve_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ክፍያውን አጽድቅ", callback_data=f"approve_{update.effective_user.id}_{','.join(map(str, my_selection))}_{safe_name}_{phone}")]
        ])
        
        try:
            await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=channel_text, reply_markup=approve_btn)
        except Exception as e:
            logger.error(f"Failed to send to channel: {e}")
            await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=f"⚠️ Channel error.\n\n" + channel_text, reply_markup=approve_btn)
        
        # Clear state
        context.user_data['step'] = None
        context.user_data['my_selection'] = []
        context.user_data.pop('temp_name', None)

# ==========================================
# 4. ONE-CLICK BUTTON APPROVAL & LIVE UPDATES
# ==========================================
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("በማጽደቅ ላይ...")
    
    data_parts = query.data.split('_')
    user_id = int(data_parts[1])
    numbers = [int(n) for n in data_parts[2].split(',')]
    name = data_parts[3].replace('_', ' ')
    phone = data_parts[4]
    
    for n in numbers:
        game_data['numbers'][n] = {'user_id': user_id, 'name': name, 'phone': phone}
        
    new_text = query.message.text + f"\n\n✅ በአስተናጋጁ ጸድቋል።"
    await query.edit_message_text(text=new_text, reply_markup=None)
    
    await context.bot.send_message(
        chat_id=user_id, 
        text=f"🎉 *ክፍያዎ ተረጋግጧል!*\n\nቁጥሮችዎ ({', '.join(map(str, numbers))}) በይፋዊነት ተቆልፈዋል። መልካም እድል!", 
        parse_mode='Markdown'
    )
    
    sold = len(game_data['numbers'])
    remaining = 100 - sold
    
    sales_text = (
        f"🔥 *የቀጥታ ሽያጭ ማሻሻያ*\n\n"
        f"🟢 የተሸጡ ቁጥሮች: *{sold} / 100*\n"
        f"🔴 የቀሩ: *{remaining}*\n\n"
        f"👉 @KoshKosh_LuckyJar_bot"
    )
    try:
        await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=sales_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to send sales update: {e}")
    
    if sold == 100:
        await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text="🚨 *ሁሉም 100 ተሽጠዋል!* 30 ደቂቃ ይጠብቁ, ከዚያ /draw ይተይቡ።")
        await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text="🚨 *ሁሉም 100 ተሽጠዋል!* ዕጣው በቅርቡ ይካሄዳል። ይዘጋጁ!")

# ==========================================
# 5. SELECTION BOARD & RULES
# ==========================================
async def show_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_count = len(game_data['numbers'])
    remaining_count = 100 - selected_count
    text = (
        f"📊 *የኮሽኮሽ ምርጫ ሰሌዳ*\n\n"
        f"⏰ የምርጫ ጊዜ: ከ ጠዋት 3:30 እስከ ከሰዐት 9:00\n"
        f"🟢 የተመረጡ ቁጥሮች: *{selected_count} / 100*\n"
        f"🔴 የቀሩ ቁጥሮች: *{remaining_count}*\n\n"
    )
    if game_data['extensions'] > 0:
        text += f"⚠️ 9:00 ደርሷል! በ {game_data['extensions']} ሰዓት ተራዝሟል።\n"
    keyboard = [
        [InlineKeyboardButton("🔄 ሰሌዳውን አድስ", callback_data="show_board")],
        [InlineKeyboardButton("🔙 ወደ ዋና ማውጫ ተመለስ", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rules_text = (
        "📖 *የኮሽኮሽ ጨዋታ ደንቦች*\n\n"
        "1️⃣ *ጃክፖት:* 100 ቁጥሮች አሉ። እያንዳንዱ 100 ብር ነው።\n"
        "2️⃣ *ምርጫ:* ቁጥሮችዎን ለመምረጥ ቁልፎቹን ይጫኑ።\n"
        "3️⃣ *ክፍያ:* ጠቅላላውን ወደ አስተናጋጁ የ CBE አካውንት ያስተላልፉ እና ስክሪንሾቱን ይላኩ።\n"
        "4️⃣ *ማጽደቅ:* አስተናጋጁ ክፍያውን ያረጋግጣል እና ቁጥሮችዎን ይቆልፋል።\n"
        "5️⃣ *ዕጣው:* ሁሉም 100 ቁጥሮች ሲሸጡ, የ30 ደቂቃ ቆጣሪ ይጀምራል።\n"
        "6️⃣ *አሸናፊዎች:* 3 ቁጥሮች ይወጣሉ። 1ኛ 4,000 ብር፣ 2ኛ 2,000 ብር፣ 3ኛ 1,500 ብር ያገኛሉ።\n"
        "7️⃣ *የጊዜ ገደብ:* ምርጫ በ 9:00 ማታ ይዘጋል። ካልተሸጠ በ1 ሰዓት ይራዘማል።"
    )
    keyboard = [[InlineKeyboardButton("🔙 ወደ ዋና ማውጫ ተመለስ", callback_data="main_menu")]]
    await query.edit_message_text(rules_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ==========================================
# 6. HOST DRAW COMMAND
# ==========================================
async def execute_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != HOST_TELEGRAM_ID: return
    if len(game_data['numbers']) < 100:
        await update.message.reply_text("❌ ዕጣ ማውጣት አይቻልም። ቁጥሮች ሙሉ በሙሉ አልተሸጡም።")
        return
    available = list(game_data['numbers'].keys())
    win_nums = random.sample(available, 3)
    r1, r2, r3 = game_data['numbers'][win_nums[0]], game_data['numbers'][win_nums[1]], game_data['numbers'][win_nums[2]]
    announcement = (
        "🎉 *የኮሽኮሽ ዕጣ ውጤቶች!* 🎉\n\n"
        f"🥇 *1ኛ ደረጃ (4,000 ብር)*\n👤 {r1['name']}\n📞 {r1['phone']}\n🔢 {win_nums[0]}\n\n"
        f"🥈 *2ኛ ደረጃ (2,000 ብር)*\n👤 {r2['name']}\n📞 {r2['phone']}\n🔢 {win_nums[1]}\n\n"
        f"🥉 *3ኛ ደረጃ (1,500 ብር)*\n👤 {r3['name']}\n📞 {r3['phone']}\n🔢 {win_nums[2]}\n\n"
        "📢 *ማሳሰቢያ:* አሸናፊዎች እባክዎ የባንክ አካውንትዎን ለአስተናጋጁ ይላኩ!"
    )
    await update.message.reply_text(announcement, parse_mode='Markdown')
    await context.bot.send_message(chat_id=SUPPORT_CHANNEL, text=announcement, parse_mode='Markdown')
    await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=f"🚨 አሸናፊዎች ተመርጠዋል! 1ኛ: {r1['name']}, 2ኛ: {r2['name']}, 3ኛ: {r3['name']}")

# --- MAIN ---
def main():
    if not BOT_TOKEN: return
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("draw", execute_draw))
    
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(view_grid, pattern="^view_grid$"))
    app.add_handler(CallbackQueryHandler(toggle_number, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(checkout, pattern="^checkout$"))
    app.add_handler(CallbackQueryHandler(approve_payment, pattern="^approve_")) 
    app.add_handler(CallbackQueryHandler(show_board, pattern="^show_board$"))
    app.add_handler(CallbackQueryHandler(show_rules, pattern="^show_rules$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer("❌ አስቀድሞ ተሽጧል!", show_alert=True), pattern="^taken$"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, handle_text_input))
    
    logger.info("KoshKosh GUI Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
