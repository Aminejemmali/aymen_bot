import os
import logging
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext, ConversationHandler

# Define conversation states
START, NAME, WAITING_APPROVAL, PHONE, WAITING_PHONE_APPROVAL, OTP, WAITING_OTP_APPROVAL, MAIN_MENU, SET_TOKENS_USER, SET_TOKENS_AMOUNT = range(10)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite database setup
DB_FILE = "users.db"

def init_db():
    """Initialize the SQLite database and create the users table if it doesn't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            phones TEXT DEFAULT '[]',
            current_phone TEXT DEFAULT '',
            current_otp TEXT DEFAULT '',
            approved INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 50,
            otp_verified_numbers TEXT DEFAULT '[]',
            state INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def load_users():
    """Load users from the database into memory"""
    users = {}
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        for row in rows:
            user_id, name, phones, current_phone, current_otp, approved, tokens, otp_verified_numbers, state = row
            users[user_id] = {
                "name": name,
                "phones": eval(phones) if phones else [],
                "current_phone": current_phone,
                "current_otp": current_otp,
                "approved": bool(approved),
                "tokens": tokens,
                "otp_verified_numbers": eval(otp_verified_numbers) if otp_verified_numbers else [],
                "state": state
            }
        conn.close()
        logger.info(f"Loaded {len(users)} users from database")
    except sqlite3.OperationalError as e:
        logger.error(f"Database error: {e}")
        # If table doesn't exist yet, return empty dict (it will be created later)
    return users

def save_user(user_id, user_data):
    """Save or update a user's data in the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, name, phones, current_phone, current_otp, approved, tokens, otp_verified_numbers, state)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        user_data["name"],
        str(user_data["phones"]),
        user_data["current_phone"],
        user_data["current_otp"],
        int(user_data["approved"]),
        user_data["tokens"],
        str(user_data["otp_verified_numbers"]),
        user_data["state"]
    ))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Delete a user from the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Initialize users as an empty dict; it will be populated in main()
users = {}

# --- Improved Arabic Messages with Emojis ---
MESSAGES = {
    "welcome": "🌟 مرحبًا بك! اختر خيارًا لبدء رحلتك مع الإنترنت السريع: 🚀",
    "already_started": "👋 لقد بدأت بالفعل! ننتظر خطوتك القادمة.",
    "name_prompt": "✨ من فضلك، أرسل لنا اسمك الكامل لنبدأ التسجيل!",
    "name_received": "🎉 شكرًا يا صديقي! ننتظر موافقة المشرف الآن. ⏳",
    "account_approved": "✅ تمت الموافقة على حسابك! أرسل رقم هاتفك للاشتراك في الإنترنت الآن! 📱",
    "account_rejected": "😔 عذرًا، تم رفض طلبك. حاول مرة أخرى أو تواصل مع الدعم.",
    "not_approved": "⏳ لم تتم الموافقة على حسابك بعد. انتظر قليلاً!",
    "phone_received": "📞 تم استلام رقمك بنجاح! في انتظار موافقة المشرف. ⏳",
    "phone_approved": "✅ تمت الموافقة على رقمك! أدخل رمز التحقق (OTP) الآن: 🔑",
    "phone_rejected": "❌ تم رفض الرقم. جرب رقمًا آخر! 🔄",
    "otp_received": "🔑 تم استلام رمز التحقق! ننتظر موافقة المشرف. ⏳",
    "otp_approved": "🎉 تمت الموافقة! الإنترنت مفعّل لرقم {}! الرموز المتبقية: {} 🌐",
    "otp_rejected": "❌ رمز التحقق مرفوض. حاول مرة أخرى! 🔄",
    "no_phone": "📱 لم ترسل رقم هاتف بعد! أرسله الآن.",
    "send_phone": "📞 أرسل لنا رقم هاتفك للاشتراك في الإنترنت!",
    "send_otp": "🔑 أرسل رمز التحقق الخاص بك الآن!",
    "main_menu": "🏠 القائمة الرئيسية",
    "tokens_remaining": "🎟️ الرموز المتبقية لديك: {}",
    "profile_info": "👤 معلوماتك:\nالاسم: {}\nأرقامك المشتركة: {}\nالرموز المتبقية: {} 🎟️",
    "input_not_recognized": "🤔 لم نفهم اختيارك! استخدم القائمة من فضلك.",
    "add_another_number": "➕ أضف رقم هاتف جديد للاشتراك",
    "no_tokens": "😔 نفدت الرموز! لا يمكنك إضافة أرقام جديدة الآن.",
    "set_tokens_prompt": "🎟️ أدخل عدد الرموز الجديد (مثال: /set_tokens 123456789 10):",
    "set_tokens_success": "✅ تم تحديث الرموز للمستخدم {} إلى {} بنجاح!",
    "set_tokens_invalid": "❌ تنسيق غير صحيح أو مستخدم غير موجود! حاول مجددًا.",
}

# Admin messages
ADMIN_MESSAGES = {
    "new_user": "👤 طلب مستخدم جديد:\nالاسم: {}\nالموافقة أو الرفض؟ ✅❌",
    "phone_submission": "📱 أرسل {} رقم الهاتف: {}\nالموافقة أو الرفض؟ ✅❌",
    "otp_submission": "🔑 أرسل {} رمز التحقق: {} لرقم {}\nالموافقة أو الرفض؟ ✅❌",
    "user_approved": "✅ تمت الموافقة على المستخدم {}",
    "user_rejected": "❌ تم رفض المستخدم",
    "phone_approved": "✅ تمت الموافقة على رقم الهاتف لـ {}",
    "phone_rejected": "❌ تم رفض رقم الهاتف",
    "otp_approved": "✅ تمت الموافقة على رمز التحقق لـ {} ورقم {}",
    "otp_rejected": "❌ تم رفض رمز التحقق",
    "user_not_found": "❓ المستخدم غير موجود",
}

# --- Helper Functions ---
def get_start_keyboard():
    """Generate the initial command keyboard"""
    keyboard = [
        ["بدء التسجيل"],
        ["عرض الملف الشخصي", "الرموز المتبقية"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def get_user_main_menu(user_id):
    """Generate main menu keyboard for users"""
    keyboard = [
        [InlineKeyboardButton("عرض الملف الشخصي 👤", callback_data="profile")],
        [InlineKeyboardButton("الرموز المتبقية 🎟️", callback_data="tokens")]
    ]
    if user_id in users and users[user_id].get("approved") and users[user_id]["tokens"] > 0:
        keyboard.append([InlineKeyboardButton(MESSAGES["add_another_number"], callback_data="send_phone")])
    return InlineKeyboardMarkup(keyboard)

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

# --- COMMAND HANDLERS ---
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
            "state": START
        }
        save_user(user_id, users[user_id])
        await update.message.reply_text(
            MESSAGES["welcome"],
            reply_markup=get_start_keyboard()
        )
        log_user_state(user_id, "New user started")
        return START
    else:
        log_user_state(user_id, "Existing user started")
        if not users[user_id]["approved"]:
            users[user_id]["state"] = WAITING_APPROVAL
            save_user(user_id, users[user_id])
            await update.message.reply_text(
                MESSAGES["already_started"] + "\n" + MESSAGES["name_received"],
                reply_markup=get_user_main_menu(user_id)
            )
            return WAITING_APPROVAL
        else:
            users[user_id]["state"] = MAIN_MENU
            save_user(user_id, users[user_id])
            await update.message.reply_text(
                MESSAGES["main_menu"],
                reply_markup=get_user_main_menu(user_id)
            )
            return MAIN_MENU

async def handle_start_choice(update: Update, context: CallbackContext) -> int:
    """Handle initial command choice"""
    user_id = update.effective_user.id
    choice = update.message.text
    
    if user_id not in users:
        return await start(update, context)
    
    log_user_state(user_id, f"Start choice: {choice}")
    
    if choice == "بدء التسجيل" and not users[user_id]["name"]:
        await update.message.reply_text(MESSAGES["name_prompt"])
        users[user_id]["state"] = NAME
        save_user(user_id, users[user_id])
        return NAME
    elif choice == "عرض الملف الشخصي":
        if users[user_id]["approved"]:
            phones_str = ", ".join(users[user_id]["otp_verified_numbers"]) if users[user_id]["otp_verified_numbers"] else "لا يوجد"
            await update.message.reply_text(
                MESSAGES["profile_info"].format(users[user_id]["name"], phones_str, users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            users[user_id]["state"] = MAIN_MENU
            save_user(user_id, users[user_id])
            return MAIN_MENU
        else:
            await update.message.reply_text(MESSAGES["not_approved"])
            return WAITING_APPROVAL
    elif choice == "الرموز المتبقية":
        if users[user_id]["approved"]:
            await update.message.reply_text(
                MESSAGES["tokens_remaining"].format(users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            users[user_id]["state"] = MAIN_MENU
            save_user(user_id, users[user_id])
            return MAIN_MENU
        else:
            await update.message.reply_text(MESSAGES["not_approved"])
            return WAITING_APPROVAL
    else:
        await update.message.reply_text(
            MESSAGES["input_not_recognized"],
            reply_markup=get_start_keyboard()
        )
        return START

async def handle_name(update: Update, context: CallbackContext) -> int:
    """Handle user name submission (only once)"""
    user_id = update.effective_user.id
    
    if user_id in users and not users[user_id]["name"]:
        users[user_id]["name"] = update.message.text
        users[user_id]["state"] = WAITING_APPROVAL
        save_user(user_id, users[user_id])
        await update.message.reply_text(MESSAGES["name_received"])
        
        keyboard = [
            [
                InlineKeyboardButton("موافقة ✅", callback_data=f"approve_{user_id}"), 
                InlineKeyboardButton("رفض ❌", callback_data=f"reject_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            ADMIN_ID, 
            ADMIN_MESSAGES["new_user"].format(users[user_id]["name"]), 
            reply_markup=reply_markup
        )
        log_user_state(user_id, "Name submitted")
        return WAITING_APPROVAL
    else:
        return await handle_phone(update, context)

async def button_handler(update: Update, context: CallbackContext) -> int:
    """Handle button callbacks"""
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
            return MAIN_MENU
    
    elif data == "tokens":
        if user_id in users:
            await query.edit_message_text(
                MESSAGES["tokens_remaining"].format(users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            return MAIN_MENU
    
    elif data == "send_phone":
        if users[user_id]["tokens"] > 0:
            users[user_id]["state"] = PHONE
            users[user_id]["current_phone"] = ""
            users[user_id]["current_otp"] = ""
            save_user(user_id, users[user_id])
            await query.edit_message_text(MESSAGES["send_phone"])
            return PHONE
        else:
            await query.edit_message_text(
                MESSAGES["no_tokens"],
                reply_markup=get_user_main_menu(user_id)
            )
            return MAIN_MENU
    
    elif data.startswith("approve_") or data.startswith("reject_"):
        if user_id == ADMIN_ID:
            if data.startswith("approve_"):
                return await handle_admin_approval(update, context)
            else:
                return await handle_admin_rejection(update, context)
        else:
            return users[user_id].get("state", MAIN_MENU)
    
    return users[user_id].get("state", MAIN_MENU)

async def handle_admin_approval(update: Update, context: CallbackContext) -> int:
    """Handle all admin approval actions"""
    query = update.callback_query
    data = query.data
    admin_id = update.effective_user.id
    
    if admin_id != ADMIN_ID:
        return ConversationHandler.END
    
    logger.info(f"Admin approval: {data}")
    
    if data.startswith("approve_") and "_phone_" not in data and "_otp_" not in data:
        user_id = int(data.split("_")[1])
        if user_id in users:
            users[user_id]["approved"] = True
            users[user_id]["state"] = PHONE
            save_user(user_id, users[user_id])
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
            users[user_id]["state"] = OTP
            save_user(user_id, users[user_id])
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
            users[user_id]["state"] = MAIN_MENU
            save_user(user_id, users[user_id])
            await context.bot.send_message(
                user_id, 
                MESSAGES["otp_approved"].format(phone, users[user_id]["tokens"]),
                reply_markup=get_user_main_menu(user_id)
            )
            await query.edit_message_text(ADMIN_MESSAGES["otp_approved"].format(users[user_id]["name"], phone))
            log_user_state(user_id, "OTP approved")
    
    return ConversationHandler.END

async def handle_admin_rejection(update: Update, context: CallbackContext) -> int:
    """Handle all admin rejection actions"""
    query = update.callback_query
    data = query.data
    admin_id = update.effective_user.id
    
    if admin_id != ADMIN_ID:
        return ConversationHandler.END
    
    logger.info(f"Admin rejection: {data}")
    
    if data.startswith("reject_") and "_phone_" not in data and "_otp_" not in data:
        user_id = int(data.split("_")[1])
        if user_id in users:
            del users[user_id]
            delete_user(user_id)
            await context.bot.send_message(user_id, MESSAGES["account_rejected"])
            await query.edit_message_text(ADMIN_MESSAGES["user_rejected"])
    
    elif data.startswith("reject_phone_"):
        user_id = int(data.split("_")[2])
        if user_id in users:
            users[user_id]["current_phone"] = ""
            users[user_id]["state"] = PHONE
            save_user(user_id, users[user_id])
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
            users[user_id]["state"] = OTP
            save_user(user_id, users[user_id])
            await context.bot.send_message(
                user_id, 
                MESSAGES["otp_rejected"],
                reply_markup=get_user_main_menu(user_id)
            )
            await query.edit_message_text(ADMIN_MESSAGES["otp_rejected"])
            log_user_state(user_id, "OTP rejected")
    
    return ConversationHandler.END

async def handle_phone(update: Update, context: CallbackContext) -> int:
    """Handle user phone number submission"""
    user_id = update.effective_user.id
    
    log_user_state(user_id, "Phone submission attempt")
    
    if user_id in users and users[user_id]["approved"]:
        if users[user_id]["tokens"] > 0:
            phone = update.message.text
            users[user_id]["current_phone"] = phone
            users[user_id]["state"] = WAITING_PHONE_APPROVAL
            save_user(user_id, users[user_id])
            await update.message.reply_text(MESSAGES["phone_received"])
            
            keyboard = [
                [
                    InlineKeyboardButton("موافقة ✅", callback_data=f"approve_phone_{user_id}"), 
                    InlineKeyboardButton("رفض ❌", callback_data=f"reject_phone_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                ADMIN_ID, 
                ADMIN_MESSAGES["phone_submission"].format(users[user_id]["name"], phone), 
                reply_markup=reply_markup
            )
            log_user_state(user_id, "Phone submitted")
            return WAITING_PHONE_APPROVAL
        else:
            await update.message.reply_text(
                MESSAGES["no_tokens"],
                reply_markup=get_user_main_menu(user_id)
            )
            return MAIN_MENU
    else:
        if user_id not in users:
            return await start(update, context)
        else:
            await update.message.reply_text(
                MESSAGES["not_approved"],
                reply_markup=get_user_main_menu(user_id)
            )
            return WAITING_APPROVAL

async def handle_otp(update: Update, context: CallbackContext) -> int:
    """Handle user OTP submission"""
    user_id = update.effective_user.id
    
    log_user_state(user_id, "OTP submission attempt")
    
    if user_id in users and users[user_id]["current_phone"]:
        otp = update.message.text
        users[user_id]["current_otp"] = otp
        users[user_id]["state"] = WAITING_OTP_APPROVAL
        save_user(user_id, users[user_id])
        await update.message.reply_text(MESSAGES["otp_received"])
        
        keyboard = [
            [
                InlineKeyboardButton("موافقة ✅", callback_data=f"approve_otp_{user_id}"), 
                InlineKeyboardButton("رفض ❌", callback_data=f"reject_otp_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            ADMIN_ID, 
            ADMIN_MESSAGES["otp_submission"].format(users[user_id]["name"], otp, users[user_id]["current_phone"]), 
            reply_markup=reply_markup
        )
        log_user_state(user_id, "OTP submitted")
        return WAITING_OTP_APPROVAL
    else:
        return await handle_phone(update, context)

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation"""
    user_id = update.effective_user.id
    if user_id in users:
        users[user_id]["state"] = MAIN_MENU
        save_user(user_id, users[user_id])
    
    await update.message.reply_text(
        MESSAGES["main_menu"],
        reply_markup=get_user_main_menu(user_id)
    )
    return MAIN_MENU

async def set_tokens(update: Update, context: CallbackContext) -> int:
    """Start the token-setting process for admin"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر مخصص للمشرف فقط!")
        return ConversationHandler.END
    
    logger.info(f"Admin {user_id} started /set_tokens")
    await update.message.reply_text(
        "👋 مرحبًا يا مشرف! من فضلك، أرسل معرف المستخدم (ID) للشخص الذي تريد تعديل رموزه. "
        "يمكنك الحصول على المعرف من رسائل الموافقة أو باستخدام @userinfobot! 🌟"
    )
    context.user_data["state"] = SET_TOKENS_USER
    return SET_TOKENS_USER

async def handle_set_tokens_user(update: Update, context: CallbackContext) -> int:
    """Handle the user ID input from admin"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return ConversationHandler.END
    
    text = update.message.text.strip()
    logger.info(f"Admin {user_id} entered user ID: {text}")
    try:
        target_user_id = int(text)
        if target_user_id in users:
            context.user_data["target_user_id"] = target_user_id
            await update.message.reply_text(
                f"✅ المستخدم {users[target_user_id]['name']} موجود! "
                "الآن، أرسل عدد الرموز الجديدة التي تريد تعيينها (مثال: 10). 🎟️"
            )
            logger.info(f"User {target_user_id} found, moving to SET_TOKENS_AMOUNT")
            context.user_data["state"] = SET_TOKENS_AMOUNT
            return SET_TOKENS_AMOUNT
        else:
            await update.message.reply_text(
                "❌ لم أجد هذا المستخدم! تأكد من المعرف وحاول مرة أخرى. 🔍"
            )
            return SET_TOKENS_USER
    except ValueError:
        await update.message.reply_text(
            "🤔 يبدو أن هذا ليس معرفًا صحيحًا! أرسل رقمًا فقط (مثال: 123456789). حاول مجددًا! 🔄"
        )
        return SET_TOKENS_USER

async def handle_set_tokens_amount(update: Update, context: CallbackContext) -> int:
    """Handle the token amount input from admin"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return ConversationHandler.END
    
    target_user_id = context.user_data.get("target_user_id")
    if not target_user_id or target_user_id not in users:
        await update.message.reply_text(
            "❌ حدث خطأ! ابدأ من جديد باستخدام /set_tokens. 😅"
        )
        return ConversationHandler.END
    
    text = update.message.text.strip()
    logger.info(f"Admin {user_id} entered token amount: {text} for user {target_user_id}")
    try:
        tokens = int(text)
        if tokens < 0:
            await update.message.reply_text(
                "🤨 الرموز لا يمكن أن تكون سالبة! أرسل رقمًا موجبًا (مثال: 10). 🎟️"
            )
            return SET_TOKENS_AMOUNT
        
        users[target_user_id]["tokens"] = tokens
        save_user(target_user_id, users[target_user_id])
        await update.message.reply_text(
            MESSAGES["set_tokens_success"].format(users[target_user_id]["name"], tokens)
        )
        log_user_state(target_user_id, f"Tokens set to {tokens} by admin")
        await context.bot.send_message(
            target_user_id,
            f"🎉 مرحبًا! تم تحديث رموزك بواسطة المشرف. لديك الآن {tokens} رمزًا متبقيًا! 🚀"
        )
        del context.user_data["target_user_id"]
        del context.user_data["state"]
        logger.info(f"Tokens set successfully for user {target_user_id}")
        return ConversationHandler.END
    
    except ValueError:
        await update.message.reply_text(
            "🤔 أرسل رقمًا صحيحًا للرموز (مثال: 10)! حاول مرة أخرى. 🔄"
        )
        return SET_TOKENS_AMOUNT

async def fallback(update: Update, context: CallbackContext) -> int:
    """Fallback handler"""
    user_id = update.effective_user.id
    
    if user_id not in users and user_id != ADMIN_ID:
        return await start(update, context)
    
    current_state = users.get(user_id, {}).get("state", MAIN_MENU) if user_id != ADMIN_ID else context.user_data.get("state", MAIN_MENU)
    
    if current_state == START:
        return await handle_start_choice(update, context)
    elif current_state == NAME or current_state == WAITING_APPROVAL:
        return await handle_name(update, context)
    elif current_state == PHONE or current_state == WAITING_PHONE_APPROVAL:
        return await handle_phone(update, context)
    elif current_state == OTP or current_state == WAITING_OTP_APPROVAL:
        return await handle_otp(update, context)
    elif current_state == SET_TOKENS_USER:
        return await handle_set_tokens_user(update, context)
    elif current_state == SET_TOKENS_AMOUNT:
        return await handle_set_tokens_amount(update, context)
    else:
        log_user_state(user_id, "Fallback triggered")
        await update.message.reply_text(
            MESSAGES["input_not_recognized"],
            reply_markup=get_user_main_menu(user_id) if user_id in users else get_start_keyboard()
        )
        return MAIN_MENU

# --- MAIN FUNCTION ---
def main():
    """Main bot application"""
    init_db()  # Initialize the database first
    global users
    users = load_users()  # Load users after initializing the database
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("set_tokens", set_tokens),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback)
        ],
        states={
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start_choice)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            WAITING_APPROVAL: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback)
            ],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            WAITING_PHONE_APPROVAL: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback)
            ],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
            WAITING_OTP_APPROVAL: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback)
            ],
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback)
            ],
            SET_TOKENS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_tokens_user)],
            SET_TOKENS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_tokens_amount)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.ALL, fallback)
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()