# handlers/start_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users
from messages.user_messages import MESSAGES
from keyboards.start_keyboard import get_start_keyboard
from keyboards.main_menu_keyboard import get_user_main_menu
from utils.logger import log_user_state
from handlers.conversation_states import START, NAME, WAITING_APPROVAL, MAIN_MENU
from handlers.handle_name import *
from handlers.start_handler import start

async def handle_start_choice(update: Update, context: CallbackContext) -> int:
    """Handle initial command choice"""
    user_id = update.effective_user.id
    choice = update.message.text
    
    if user_id not in users:
        return await start(update, context)
    
    log_user_state(user_id, f"Start choice: {choice}")
    
    if choice == "بدء التسجيل" and not users[user_id]["name"]:
        await update.message.reply_text(MESSAGES["name_prompt"])
        users[user_id]["state"] = NAME
        return NAME
    elif choice == "عرض الملف الشخصي":
        if users[user_id]["approved"]:
            phones_str = ", ".join(users[user_id]["otp_verified_numbers"]) if users[user_id]["otp_verified_numbers"] else "لا يوجد"
            await update.message.reply_text(
                MESSAGES["profile_info"].format(users[user_id]["name"], phones_str, users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            users[user_id]["state"] = MAIN_MENU
            return MAIN_MENU
        else:
            await update.message.reply_text(MESSAGES["not_approved"])
            return WAITING_APPROVAL
    elif choice == "الرموز المتبقية":
        if users[user_id]["approved"]:
            await update.message.reply_text(
                MESSAGES["tokens_remaining"].format(users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            users[user_id]["state"] = MAIN_MENU
            return MAIN_MENU
        else:
            await update.message.reply_text(MESSAGES["not_approved"])
            return WAITING_APPROVAL
    else:
        await update.message.reply_text(
            MESSAGES["input_not_recognized"],
            reply_markup=get_start_keyboard()
        )
        return START