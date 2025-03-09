# handlers/phone_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from config import users, ADMIN_ID
from keyboards.main_menu_keyboard import get_user_main_menu
import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

MESSAGES = {
    "phone_received": "تم استلام رقم الهاتف. في انتظار موافقة المشرف.",
    "no_tokens": "لقد نفدت الرموز المتاحة لديك. لا يمكنك إضافة المزيد من الأرقام.",
    "not_approved": "لم تتم الموافقة على حسابك بعد.",
}

ADMIN_MESSAGES = {
    "phone_submission": "أرسل المستخدم {} رقم الهاتف: {} للاشتراك في الإنترنت.\nالموافقة أو الرفض؟",
}

def log_user_state(user_id, message=""):
    if user_id in users:
        state_info = f"User ID: {user_id}, Name: {users[user_id].get('name', 'None')}, "
        state_info += f"Approved: {users[user_id].get('approved', False)}, "
        state_info += f"Phones: {users[user_id].get('phones', [])}, "
        state_info += f"OTP Verified Numbers: {users[user_id].get('otp_verified_numbers', [])}"
        if message:
            state_info = f"{message}: {state_info}"
        logger.info(state_info)

async def handle_phone(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    log_user_state(user_id, "Phone submission attempt")
    
    if user_id in users and users[user_id]["approved"]:
        if users[user_id]["tokens"] > 0:
            phone = update.message.text
            users[user_id]["current_phone"] = phone
            users[user_id]["state"] = 4  # WAITING_PHONE_APPROVAL
            await update.message.reply_text(MESSAGES["phone_received"])
            
            keyboard = [
                [
                    InlineKeyboardButton("موافقة", callback_data=f"approve_phone_{user_id}"), 
                    InlineKeyboardButton("رفض", callback_data=f"reject_phone_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                ADMIN_ID, 
                ADMIN_MESSAGES["phone_submission"].format(users[user_id]["name"], phone), 
                reply_markup=reply_markup
            )
            log_user_state(user_id, "Phone submitted")
            return 4  # WAITING_PHONE_APPROVAL
        else:
            await update.message.reply_text(
                MESSAGES["no_tokens"],
                reply_markup=get_user_main_menu(user_id)
            )
            return 7  # MAIN_MENU
    else:
        if user_id not in users:
            from handlers.start_handler import start
            return await start(update, context)
        else:
            await update.message.reply_text(
                MESSAGES["not_approved"],
                reply_markup=get_user_main_menu(user_id)
            )
            return 2  # WAITING_APPROVAL