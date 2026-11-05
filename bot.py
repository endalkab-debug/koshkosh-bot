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
        
        # 1. Send Invoice to User
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
        
        # 2. Send Notification to Host (Removed all formatting to prevent crash)
        host_text = (
            f"🚨 NEW PAYMENT VERIFICATION NEEDED 🚨\n\n"
            f"👤 Name: {name}\n"
            f"📞 Phone: {phone}\n"
            f"🎟️ Numbers: {', '.join(map(str, my_selection))}\n"
            f"💰 Amount: {total_cost} Birr\n"
            f"🆔 User ID: {update.effective_user.id}\n\n"
            f"👇 COPY THIS COMMAND TO APPROVE:\n"
            f"/approve {update.effective_user.id} {','.join(map(str, my_selection))} {safe_name} {phone}"
        )
        # Notice we removed parse_mode='Markdown' here to ensure it doesn't crash
        await context.bot.send_message(chat_id=HOST_TELEGRAM_ID, text=host_text)
        
        # Clear state
        context.user_data['step'] = None
        context.user_data['my_selection'] = []
        context.user_data.pop('temp_name', None)
