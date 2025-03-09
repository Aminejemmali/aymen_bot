# handlers/start_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users
from keyboards.start_keyboard import get_start_keyboard
from keyboards.main_menu_keyboard import get_user_main_menu
import logging

# Setup logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Messages (subset from main.py)
MESSAGES = {
    "welcome": "مرحبًا بك! اختر أحد الخيارات لبدء عملية الاشتراك في الإنترنت:",
    "already_started": "لقد بدأت العملية بالفعل.",
    "name_prompt": "يرجى إرسال اسمك الكامل لبدء التسجيل.",
    "name_received": "شكرًا لك! في انتظار موافقة المشرف.",
    "not_approved": "لم تتم الموافقة على حسابك بعد.",
    "input_not_recognized": "لم يتم التعرف على الإدخال. يرجى استخدام القائمة.",
    "main_menu": "القائمة الرئيسية",
    "profile_info": "معلومات الملف الشخصي:\nالاسم: {}\nأرقام الهواتف المشتركة: {}\nالرموز المتبقية: {}",
    "tokens_remaining": "الرموز المتبقية: {}",
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
            "state": 0  # START
        }
        await update.message.reply_text(
            MESSAGES["welcome"],
            reply_markup=get_start_keyboard()
        )
        log_user_state(user_id, "New user started")
        return 0  # START
    else:
        log_user_state(user_id, "Existing user started")
        if not users[user_id]["approved"]:
            users[user_id]["state"] = 2  # WAITING_APPROVAL
            await update.message.reply_text(
                MESSAGES["already_started"] + "\n" + MESSAGES["name_received"],
                reply_markup=get_user_main_menu(user_id)
            )
            return 2  # WAITING_APPROVAL
        else:
            users[user_id]["state"] = 7  # MAIN_MENU
            await update.message.reply_text(
                MESSAGES["main_menu"],
                reply_markup=get_user_main_menu(user_id)
            )
            return 7  # MAIN_MENU

async def handle_start_choice(update: Update, context: CallbackContext) -> int:
    """Handle initial command choice"""
    user_id = update.effective_user.id
    choice = update.message.text
    
    if user_id not in users:
        return await start(update, context)
    
    log_user_state(user_id, f"Start choice: {choice}")
    
    if choice == "بدء التسجيل" and not users[user_id]["name"]:
        await update.message.reply_text(MESSAGES["name_prompt"])
        users[user_id]["state"] = 1  # NAME
        return 1  # NAME
    elif choice == "عرض الملف الشخصي":
        if users[user_id]["approved"]:
            phones_str = ", ".join(users[user_id]["otp_verified_numbers"]) if users[user_id]["otp_verified_numbers"] else "لا يوجد"
            await update.message.reply_text(
                MESSAGES["profile_info"].format(users[user_id]["name"], phones_str, users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            users[user_id]["state"] = 7  # MAIN_MENU
            return 7  # MAIN_MENU
        else:
            await update.message.reply_text(MESSAGES["not_approved"])
            return 2  # WAITING_APPROVAL
    elif choice == "الرموز المتبقية":
        if users[user_id]["approved"]:
            await update.message.reply_text(
                MESSAGES["tokens_remaining"].format(users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            users[user_id]["state"] = 7  # MAIN_MENU
            return 7  # MAIN_MENU
        else:
            await update.message.reply_text(MESSAGES["not_approved"])
            return 2  # WAITING_APPROVAL
    else:
        await update.message.reply_text(
            MESSAGES["input_not_recognized"],
            reply_markup=get_start_keyboard()
        )
        return 0  # START