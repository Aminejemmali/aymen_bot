# main.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from handlers.start_handler import start
from handlers.conversation_states import START
from config import BOT_TOKEN

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main bot application"""
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )
    app.add_handler(conv_handler)

    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()