# handlers/phone_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users
from messages.user_messages import MESSAGES
from keyboards.main_menu_keyboard import get_user_main_menu
from utils.logger import log_user_state
from handlers.conversation_states import *

async def handle_phone(update: Update, context: CallbackContext) -> int:
    """Handle phone number submission"""
    user_id = update.effective_user.id
    
    if user_id in users and users[user_id]["approved"]:
        if users[user_id]["tokens"] > 0:
            phone = update.message.text
            users[user_id]["current_phone"] = phone
            users[user_id]["state"] = WAITING_PHONE_APPROVAL
            await update.message.reply_text(MESSAGES["phone_received"])
            return WAITING_PHONE_APPROVAL
        else:
            await update.message.reply_text(MESSAGES["no_tokens"])
            return MAIN_MENU
    else:
        await update.message.reply_text(MESSAGES["not_approved"])
        return WAITING_APPROVAL