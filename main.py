# main.py
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext, ConversationHandler
import sqlite3  # Unused for now, but kept as per your original

# Define conversation states
START, NAME, WAITING_APPROVAL, PHONE, WAITING_PHONE_APPROVAL, OTP, WAITING_OTP_APPROVAL, MAIN_MENU = range(8)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
from config import ADMIN_ID
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Set in config

# Enable logging
import logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Import handlers
from handlers.start_handler import start, handle_start_choice
from handlers.handle_name import handle_name  # Assume this exists
from handlers.phone_handler import handle_phone
from handlers.otp_handler import handle_otp
from handlers.button_handler import button_handler, handle_admin_approval, handle_admin_rejection  # Assume these exist

# --- MAIN FUNCTION ---
def main():
    """Main bot application"""
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start_choice)
        ],
        states={
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start_choice)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            WAITING_APPROVAL: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
            ],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            WAITING_PHONE_APPROVAL: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)
            ],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
            WAITING_OTP_APPROVAL: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)
            ],
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: MAIN_MENU)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: MAIN_MENU)
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()