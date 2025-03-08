# keyboards/main_menu_keyboard.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import users
from messages.user_messages import MESSAGES

def get_user_main_menu(user_id):
    """Generate main menu keyboard for users"""
    keyboard = [
        [InlineKeyboardButton("عرض الملف الشخصي", callback_data="profile")],
        [InlineKeyboardButton("الرموز المتبقية", callback_data="tokens")]
    ]
    
    if user_id in users and users[user_id].get("approved") and users[user_id]["tokens"] > 0:
        keyboard.append([InlineKeyboardButton(MESSAGES["add_another_number"], callback_data="send_phone")])
    
    return InlineKeyboardMarkup(keyboard)