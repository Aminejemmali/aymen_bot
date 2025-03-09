# handlers/name_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from config import users, ADMIN_ID
import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

MESSAGES = {
    "name_received": "شكرًا لك! في انتظار موافقة المشرف.",
}

ADMIN_MESSAGES = {
    "new_user": "طلب مستخدم جديد:\nالاسم: {}\nالموافقة أو الرفض؟",
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

async def handle_name(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    if user_id in users and not users[user_id]["name"]:
        users[user_id]["name"] = update.message.text
        users[user_id]["state"] = 2  # WAITING_APPROVAL
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
        return 2  # WAITING_APPROVAL
    else:
        from handlers.phone_handler import handle_phone
        return await handle_phone(update, context)