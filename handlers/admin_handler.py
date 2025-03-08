# handlers/admin_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from config import users, ADMIN_ID
from messages.admin_messages import *
from utils.logger import log_user_state
from handlers.conversation_states import MAIN_MENU
from messages.user_messages import *
async def handle_admin_approval(update: Update, context: CallbackContext) -> int:
    """Handle admin approval actions"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[1])
    if user_id in users:
        users[user_id]["approved"] = True
        await context.bot.send_message(user_id, MESSAGES["account_approved"])
        await query.edit_message_text(ADMIN_MESSAGES["user_approved"].format(users[user_id]["name"]))
        log_user_state(user_id, "User approved")
    
    return MAIN_MENU

async def handle_admin_rejection(update: Update, context: CallbackContext) -> int:
    """Handle admin rejection actions"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[1])
    if user_id in users:
        del users[user_id]
        await context.bot.send_message(user_id, MESSAGES["account_rejected"])
        await query.edit_message_text(ADMIN_MESSAGES["user_rejected"])
    
    return MAIN_MENU