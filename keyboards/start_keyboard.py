# keyboards/start_keyboard.py
from telegram import ReplyKeyboardMarkup

def get_start_keyboard():
    keyboard = [
        ["بدء التسجيل"],
        ["عرض الملف الشخصي", "الرموز المتبقية"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)