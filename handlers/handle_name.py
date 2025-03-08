# handlers/name_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from config import users, ADMIN_ID
from messages.user_messages import MESSAGES
from messages.admin_messages import ADMIN_MESSAGES
from utils.logger import log_user_state
from handlers.conversation_states import WAITING_APPROVAL, PHONE
from handlers.phone_handler import *
async def handle_name(update: Update, context: CallbackContext) -> int:
    """Handle user name submission (only once)"""
    user_id = update.effective_user.id
    
    if user_id in users and not users[user_id]["name"]:
        users[user_id]["name"] = update.message.text
        users[user_id]["state"] = WAITING_APPROVAL
        await update.message.reply_text(MESSAGES["name_received"])
        
        keyboard = [
            [
                InlineKeyboardButton("موافقة", callback_data=f"approve_{user_id}"), 
                InlineKeyboardButton("رفض", callback_data=f"reject_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            ADMIN_ID, 
            ADMIN_MESSAGES["new_user"].format(users[user_id]["name"]), 
            reply_markup=reply_markup
        )
        log_user_state(user_id, "Name submitted")
        return WAITING_APPROVAL
    else:
        return await handle_phone(update, context)  # If name already exists, treat as phone input