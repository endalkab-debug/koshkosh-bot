async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') != 'awaiting_contact':
        return
        
    text = update.message.text
    my_selection = context.user_data.get('my_selection', [])
    total_cost = len(my_selection) * 100
    
    # Smart parsing: works even if you forget the comma!
    try:
        if ',' in text:
            name, phone = text.split(',', 1)
        else:
            # Split by the last space if no comma is found
            name, phone = text.rsplit(' ', 1)
            
        name = name.strip()
        phone = phone.strip()
        
        if not name or not phone:
            raise ValueError("Empty name or phone")
            
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
        
        # Only clear the step AFTER successful processing
        context.user_data['step'] = None
        context.user_data['my_selection'] = []
        
    except Exception:
        await update.message.reply_text("❌ Format incorrect. Please type: `Name, Phone` (e.g., `Abebe, 0911223344`)")
