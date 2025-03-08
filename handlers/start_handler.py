# handlers/start_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users
from messages.user_messages import MESSAGES
from keyboards.start_keyboard import get_start_keyboard
from keyboards.main_menu_keyboard import get_user_main_menu
from utils.logger import log_user_state
from handlers.conversation_states import START, WAITING_APPROVAL, MAIN_MENU

async def start(update: Update, context: CallbackContext) -> int:
    """Start command for users"""
    user_id = update.effective_user.id
    
    if user_id not in users:
        users[user_id] = {
            "name": "", 
            "phones": [], 
            "current_phone": "", 
            "current_otp": "", 
            "approved": False, 
            "tokens": 50,
            "otp_verified_numbers": [],
            "state": START
        }
        await update.message.reply_text(
            MESSAGES["welcome"],
            reply_markup=get_start_keyboard()
        )
        log_user_state(user_id, "New user started")
        return START
    else:
        log_user_state(user_id, "Existing user started")
        if not users[user_id]["approved"]:
            users[user_id]["state"] = WAITING_APPROVAL
            await update.message.reply_text(
                MESSAGES["already_started"] + "\n" + MESSAGES["name_received"],
                reply_markup=get_user_main_menu(user_id)
            )
            return WAITING_APPROVAL
        else:
            users[user_id]["state"] = MAIN_MENU
            await update.message.reply_text(
                MESSAGES["main_menu"],
                reply_markup=get_user_main_menu(user_id)
            )
            return MAIN_MENU