# handlers/fallback_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users
from messages.user_messages import *
from keyboards.main_menu_keyboard import get_user_main_menu
from utils.logger import log_user_state
from handlers.conversation_states import *
from handlers.start_handler import *
from handlers.otp_handler import *
from handlers.phone_handler import *
async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation"""
    user_id = update.effective_user.id
    if user_id in users:
        users[user_id]["state"] = MAIN_MENU
    
    await update.message.reply_text(
        MESSAGES["main_menu"],
        reply_markup=get_user_main_menu(user_id)
    )
    return MAIN_MENU

async def fallback(update: Update, context: CallbackContext) -> int:
    """Fallback handler"""
    user_id = update.effective_user.id
    
    if user_id not in users:
        return await start(update, context)
    
    current_state = users[user_id].get("state", MAIN_MENU)
    
    if current_state == START:
        return await handle_start_choice(update, context)
    elif current_state == NAME or current_state == WAITING_APPROVAL:
        return await handle_name(update, context)
    elif current_state == PHONE or current_state == WAITING_PHONE_APPROVAL:
        return await handle_phone(update, context)
    elif current_state == OTP or current_state == WAITING_OTP_APPROVAL:
        return await handle_otp(update, context)
    else:
        log_user_state(user_id, "Fallback triggered")
        await update.message.reply_text(
            MESSAGES["input_not_recognized"],
            reply_markup=get_user_main_menu(user_id)
        )
        return MAIN_MENU