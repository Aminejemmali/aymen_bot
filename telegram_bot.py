import os
import logging
import sqlite3
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext, ConversationHandler

# Define conversation states
START, NAME, WAITING_APPROVAL, PHONE, WAITING_PHONE_APPROVAL, OTP, WAITING_OTP_APPROVAL, MAIN_MENU, SET_TOKENS_USER, SET_TOKENS_AMOUNT = range(10)

# --- Configuration ---
class Config:
    """Configuration class for environment variables and constants"""
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
    DB_FILE = "users.db"

    # Logging setup
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)

# --- Database Handler ---
class Database:
    """SQLite database handler"""
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_file) as conn:
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
        Config.logger.info("Database initialized")

    def load_users(self):
        """Load users from the database into memory with compatibility for old data"""
        users = {}
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
                for row in cursor.fetchall():
                    user_id, name, phones, current_phone, current_otp, approved, tokens, otp_verified_numbers, state = row
                    # Handle legacy data: if json.loads fails, assume it's a Python str(list) and use eval
                    try:
                        phones_list = json.loads(phones) if phones else []
                    except json.JSONDecodeError:
                        Config.logger.warning(f"Invalid JSON in phones for user {user_id}: {phones}. Attempting eval.")
                        phones_list = eval(phones) if phones else []  # Fallback to eval for old data
                    try:
                        otp_verified_list = json.loads(otp_verified_numbers) if otp_verified_numbers else []
                    except json.JSONDecodeError:
                        Config.logger.warning(f"Invalid JSON in otp_verified_numbers for user {user_id}: {otp_verified_numbers}. Attempting eval.")
                        otp_verified_list = eval(otp_verified_numbers) if otp_verified_numbers else []  # Fallback to eval for old data

                    users[user_id] = {
                        "name": name,
                        "phones": phones_list,
                        "current_phone": current_phone,
                        "current_otp": current_otp,
                        "approved": bool(approved),
                        "tokens": tokens,
                        "otp_verified_numbers": otp_verified_list,
                        "state": state
                    }
            Config.logger.info(f"Loaded {len(users)} users from database")
        except sqlite3.OperationalError as e:
            Config.logger.error(f"Database error: {e}")
        return users

    def save_user(self, user_id, user_data):
        """Save or update a user's data in the database"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, name, phones, current_phone, current_otp, approved, tokens, otp_verified_numbers, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                user_data["name"],
                json.dumps(user_data["phones"]),  # Always save as valid JSON
                user_data["current_phone"],
                user_data["current_otp"],
                int(user_data["approved"]),
                user_data["tokens"],
                json.dumps(user_data["otp_verified_numbers"]),  # Always save as valid JSON
                user_data["state"]
            ))
            conn.commit()

    def delete_user(self, user_id):
        """Delete a user from the database"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()

# --- Messages ---
class Messages:
    """Message definitions"""
    USER_MESSAGES = {
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
        "send_phone": "📞 أرسل لنا رقم هاتفك للاشتراك في الإنترنت!",
        "main_menu": "🏠 القائمة الرئيسية",
        "tokens_remaining": "🎟️ الرموز المتبقية لديك: {}",
        "profile_info": "👤 معلوماتك:\nالاسم: {}\nأرقامك المشتركة: {}\nالرموز المتبقية: {} 🎟️",
        "input_not_recognized": "🤔 لم نفهم اختيارك! استخدم القائمة من فضلك.",
        "add_another_number": "➕ أضف رقم هاتف جديد للاشتراك",
        "no_tokens": "😔 نفدت الرموز! لا يمكنك إضافة أرقام جديدة الآن.",
        "set_tokens_success": "✅ تم تحديث الرموز للمستخدم {} إلى {} بنجاح!",
    }

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
        "admin_menu": "🏠 مرحبًا يا مشرف! اختر خيارًا:",
        "users_with_tokens": "👥 المستخدمون الذين لديهم رموز:\n{}",
        "no_users_with_tokens": "⚠️ لا يوجد مستخدمين لديهم رموز حاليًا.",
        "set_tokens_prompt": "🎟️ أرسل معرف المستخدم (ID) لتعديل رموزه (مثال: 123456789):",
    }

# --- Bot Logic ---
class InternetBot:
    """Main bot logic"""
    def __init__(self):
        self.db = Database(Config.DB_FILE)
        self.users = self.db.load_users()
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        self.messages = Messages()

    def get_start_keyboard(self):
        """Generate the initial command keyboard for regular users"""
        return ReplyKeyboardMarkup([["بدء التسجيل"], ["عرض الملف الشخصي", "الرموز المتبقية"]], one_time_keyboard=True, resize_keyboard=True)

    def get_user_main_menu(self, user_id):
        """Generate main menu keyboard for regular users"""
        keyboard = [
            [InlineKeyboardButton("عرض الملف الشخصي 👤", callback_data="profile")],
            [InlineKeyboardButton("الرموز المتبقية 🎟️", callback_data="tokens")]
        ]
        if user_id in self.users and self.users[user_id].get("approved") and self.users[user_id]["tokens"] > 0:
            keyboard.append([InlineKeyboardButton(self.messages.USER_MESSAGES["add_another_number"], callback_data="send_phone")])
        return InlineKeyboardMarkup(keyboard)

    def get_admin_main_menu(self):
        """Generate main menu keyboard for admin"""
        keyboard = [
            [InlineKeyboardButton("👥 التحقق من المستخدمين برموز", callback_data="check_users_with_tokens")],
            [InlineKeyboardButton("🎟️ تعيين رموز لمستخدم", callback_data="set_tokens")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id == Config.ADMIN_ID:
            await update.message.reply_text(self.messages.ADMIN_MESSAGES["admin_menu"], reply_markup=self.get_admin_main_menu())
            return MAIN_MENU
        if user_id not in self.users:
            self.users[user_id] = {"name": "", "phones": [], "current_phone": "", "current_otp": "", "approved": False, "tokens": 50, "otp_verified_numbers": [], "state": START}
            self.db.save_user(user_id, self.users[user_id])
            await update.message.reply_text(self.messages.USER_MESSAGES["welcome"], reply_markup=self.get_start_keyboard())
            Config.logger.info(f"New user started: {user_id}")
            return START
        if not self.users[user_id]["approved"]:
            self.users[user_id]["state"] = WAITING_APPROVAL
            self.db.save_user(user_id, self.users[user_id])
            await update.message.reply_text(self.messages.USER_MESSAGES["already_started"] + "\n" + self.messages.USER_MESSAGES["name_received"], reply_markup=self.get_user_main_menu(user_id))
            return WAITING_APPROVAL
        self.users[user_id]["state"] = MAIN_MENU
        self.db.save_user(user_id, self.users[user_id])
        await update.message.reply_text(self.messages.USER_MESSAGES["main_menu"], reply_markup=self.get_user_main_menu(user_id))
        return MAIN_MENU

    async def handle_start_choice(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        choice = update.message.text
        if user_id not in self.users:
            return await self.start(update, context)
        Config.logger.info(f"User {user_id} chose: {choice}")
        if choice == "بدء التسجيل" and not self.users[user_id]["name"]:
            await update.message.reply_text(self.messages.USER_MESSAGES["name_prompt"])
            self.users[user_id]["state"] = NAME
            self.db.save_user(user_id, self.users[user_id])
            return NAME
        elif choice == "عرض الملف الشخصي" and self.users[user_id]["approved"]:
            phones_str = ", ".join(self.users[user_id]["otp_verified_numbers"]) if self.users[user_id]["otp_verified_numbers"] else "لا يوجد"
            await update.message.reply_text(self.messages.USER_MESSAGES["profile_info"].format(self.users[user_id]["name"], phones_str, self.users[user_id]["tokens"]), reply_markup=self.get_user_main_menu(user_id))
            self.users[user_id]["state"] = MAIN_MENU
            self.db.save_user(user_id, self.users[user_id])
            return MAIN_MENU
        elif choice == "الرموز المتبقية" and self.users[user_id]["approved"]:
            await update.message.reply_text(self.messages.USER_MESSAGES["tokens_remaining"].format(self.users[user_id]["tokens"]), reply_markup=self.get_user_main_menu(user_id))
            self.users[user_id]["state"] = MAIN_MENU
            self.db.save_user(user_id, self.users[user_id])
            return MAIN_MENU
        await update.message.reply_text(self.messages.USER_MESSAGES["input_not_recognized"], reply_markup=self.get_start_keyboard())
        return START

    async def handle_name(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id in self.users and not self.users[user_id]["name"]:
            self.users[user_id]["name"] = update.message.text
            self.users[user_id]["state"] = WAITING_APPROVAL
            self.db.save_user(user_id, self.users[user_id])
            await update.message.reply_text(self.messages.USER_MESSAGES["name_received"])
            keyboard = [[InlineKeyboardButton("موافقة ✅", callback_data=f"approve_{user_id}"), InlineKeyboardButton("رفض ❌", callback_data=f"reject_{user_id}")]]
            await context.bot.send_message(Config.ADMIN_ID, self.messages.ADMIN_MESSAGES["new_user"].format(self.users[user_id]["name"]), reply_markup=InlineKeyboardMarkup(keyboard))
            Config.logger.info(f"Name submitted for user {user_id}")
            return WAITING_APPROVAL
        return await self.handle_phone(update, context)

    async def handle_phone(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id in self.users and self.users[user_id]["approved"]:
            if self.users[user_id]["tokens"] > 0:
                phone = update.message.text
                self.users[user_id]["current_phone"] = phone
                self.users[user_id]["state"] = WAITING_PHONE_APPROVAL
                self.db.save_user(user_id, self.users[user_id])
                await update.message.reply_text(self.messages.USER_MESSAGES["phone_received"])
                keyboard = [[InlineKeyboardButton("موافقة ✅", callback_data=f"approve_phone_{user_id}"), InlineKeyboardButton("رفض ❌", callback_data=f"reject_phone_{user_id}")]]
                await context.bot.send_message(Config.ADMIN_ID, self.messages.ADMIN_MESSAGES["phone_submission"].format(self.users[user_id]["name"], phone), reply_markup=InlineKeyboardMarkup(keyboard))
                Config.logger.info(f"Phone submitted for user {user_id}")
                return WAITING_PHONE_APPROVAL
            await update.message.reply_text(self.messages.USER_MESSAGES["no_tokens"], reply_markup=self.get_user_main_menu(user_id))
            return MAIN_MENU
        if user_id not in self.users:
            return await self.start(update, context)
        await update.message.reply_text(self.messages.USER_MESSAGES["not_approved"], reply_markup=self.get_user_main_menu(user_id))
        return WAITING_APPROVAL

    async def handle_otp(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id in self.users and self.users[user_id]["current_phone"]:
            otp = update.message.text
            self.users[user_id]["current_otp"] = otp
            self.users[user_id]["state"] = WAITING_OTP_APPROVAL
            self.db.save_user(user_id, self.users[user_id])
            await update.message.reply_text(self.messages.USER_MESSAGES["otp_received"])
            keyboard = [[InlineKeyboardButton("موافقة ✅", callback_data=f"approve_otp_{user_id}"), InlineKeyboardButton("رفض ❌", callback_data=f"reject_otp_{user_id}")]]
            await context.bot.send_message(Config.ADMIN_ID, self.messages.ADMIN_MESSAGES["otp_submission"].format(self.users[user_id]["name"], otp, self.users[user_id]["current_phone"]), reply_markup=InlineKeyboardMarkup(keyboard))
            Config.logger.info(f"OTP submitted for user {user_id}")
            return WAITING_OTP_APPROVAL
        return await self.handle_phone(update, context)

    async def button_handler(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        data = query.data
        Config.logger.info(f"Button pressed by {user_id}: {data}")

        # User buttons
        if data == "profile" and user_id in self.users:
            phones_str = ", ".join(self.users[user_id]["otp_verified_numbers"]) if self.users[user_id]["otp_verified_numbers"] else "لا يوجد"
            await query.edit_message_text(self.messages.USER_MESSAGES["profile_info"].format(self.users[user_id]["name"], phones_str, self.users[user_id]["tokens"]), reply_markup=self.get_user_main_menu(user_id))
            return MAIN_MENU
        elif data == "tokens" and user_id in self.users:
            await query.edit_message_text(self.messages.USER_MESSAGES["tokens_remaining"].format(self.users[user_id]["tokens"]), reply_markup=self.get_user_main_menu(user_id))
            return MAIN_MENU
        elif data == "send_phone" and self.users[user_id]["tokens"] > 0:
            self.users[user_id]["state"] = PHONE
            self.users[user_id]["current_phone"] = ""
            self.users[user_id]["current_otp"] = ""
            self.db.save_user(user_id, self.users[user_id])
            await query.edit_message_text(self.messages.USER_MESSAGES["send_phone"])
            return PHONE

        # Admin buttons
        if user_id == Config.ADMIN_ID:
            if data == "check_users_with_tokens":
                users_with_tokens = [f"👤 {user_data['name']} (ID: {uid}) - 🎟️ {user_data['tokens']}" for uid, user_data in self.users.items() if user_data["tokens"] > 0]
                response = self.messages.ADMIN_MESSAGES["users_with_tokens"].format("\n".join(users_with_tokens)) if users_with_tokens else self.messages.ADMIN_MESSAGES["no_users_with_tokens"]
                await query.edit_message_text(response, reply_markup=self.get_admin_main_menu())
                Config.logger.info(f"Admin {user_id} checked users with tokens")
                return MAIN_MENU
            elif data == "set_tokens":
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["set_tokens_prompt"], reply_markup=self.get_admin_main_menu())
                context.user_data["state"] = SET_TOKENS_USER
                Config.logger.info(f"Admin {user_id} initiated set tokens")
                return SET_TOKENS_USER
            elif data.startswith("approve_") or data.startswith("reject_"):
                if data.startswith("approve_"):
                    return await self.handle_admin_approval(update, context)
                return await self.handle_admin_rejection(update, context)

        return self.users[user_id].get("state", MAIN_MENU) if user_id in self.users else MAIN_MENU

    async def handle_admin_approval(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        data = query.data
        if update.effective_user.id != Config.ADMIN_ID:
            return ConversationHandler.END
        Config.logger.info(f"Admin approval: {data}")
        if data.startswith("approve_") and "_phone_" not in data and "_otp_" not in data:
            user_id = int(data.split("_")[1])
            if user_id in self.users:
                self.users[user_id]["approved"] = True
                self.users[user_id]["state"] = PHONE
                self.db.save_user(user_id, self.users[user_id])
                await context.bot.send_message(user_id, self.messages.USER_MESSAGES["account_approved"], reply_markup=self.get_user_main_menu(user_id))
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["user_approved"].format(self.users[user_id]["name"]))
                Config.logger.info(f"User approved: {user_id}")
        elif data.startswith("approve_phone_"):
            user_id = int(data.split("_")[2])
            if user_id in self.users:
                self.users[user_id]["state"] = OTP
                self.db.save_user(user_id, self.users[user_id])
                await context.bot.send_message(user_id, self.messages.USER_MESSAGES["phone_approved"])
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["phone_approved"].format(self.users[user_id]["name"]))
                Config.logger.info(f"Phone approved for user {user_id}")
        elif data.startswith("approve_otp_"):
            user_id = int(data.split("_")[2])
            if user_id in self.users:
                phone = self.users[user_id]["current_phone"]
                self.users[user_id]["phones"].append(phone)
                self.users[user_id]["otp_verified_numbers"].append(phone)
                self.users[user_id]["tokens"] -= 1
                self.users[user_id]["state"] = MAIN_MENU
                self.db.save_user(user_id, self.users[user_id])
                await context.bot.send_message(user_id, self.messages.USER_MESSAGES["otp_approved"].format(phone, self.users[user_id]["tokens"]), reply_markup=self.get_user_main_menu(user_id))
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["otp_approved"].format(self.users[user_id]["name"], phone))
                Config.logger.info(f"OTP approved for user {user_id}")
        return ConversationHandler.END

    async def handle_admin_rejection(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        data = query.data
        if update.effective_user.id != Config.ADMIN_ID:
            return ConversationHandler.END
        Config.logger.info(f"Admin rejection: {data}")
        if data.startswith("reject_") and "_phone_" not in data and "_otp_" not in data:
            user_id = int(data.split("_")[1])
            if user_id in self.users:
                del self.users[user_id]
                self.db.delete_user(user_id)
                await context.bot.send_message(user_id, self.messages.USER_MESSAGES["account_rejected"])
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["user_rejected"])
        elif data.startswith("reject_phone_"):
            user_id = int(data.split("_")[2])
            if user_id in self.users:
                self.users[user_id]["current_phone"] = ""
                self.users[user_id]["state"] = PHONE
                self.db.save_user(user_id, self.users[user_id])
                await context.bot.send_message(user_id, self.messages.USER_MESSAGES["phone_rejected"], reply_markup=self.get_user_main_menu(user_id))
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["phone_rejected"])
                Config.logger.info(f"Phone rejected for user {user_id}")
        elif data.startswith("reject_otp_"):
            user_id = int(data.split("_")[2])
            if user_id in self.users:
                self.users[user_id]["current_otp"] = ""
                self.users[user_id]["state"] = OTP
                self.db.save_user(user_id, self.users[user_id])
                await context.bot.send_message(user_id, self.messages.USER_MESSAGES["otp_rejected"], reply_markup=self.get_user_main_menu(user_id))
                await query.edit_message_text(self.messages.ADMIN_MESSAGES["otp_rejected"])
                Config.logger.info(f"OTP rejected for user {user_id}")
        return ConversationHandler.END

    async def handle_set_tokens_user(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id != Config.ADMIN_ID:
            return ConversationHandler.END
        text = update.message.text.strip()
        Config.logger.info(f"Admin {user_id} entered user ID: {text}")
        try:
            target_user_id = int(text)
            if target_user_id in self.users:
                context.user_data["target_user_id"] = target_user_id
                await update.message.reply_text(f"✅ المستخدم {self.users[target_user_id]['name']} موجود! الآن، أرسل عدد الرموز الجديدة (مثال: 10). 🎟️", reply_markup=self.get_admin_main_menu())
                context.user_data["state"] = SET_TOKENS_AMOUNT
                return SET_TOKENS_AMOUNT
            await update.message.reply_text("❌ لم أجد هذا المستخدم! تأكد من المعرف وحاول مرة أخرى. 🔍", reply_markup=self.get_admin_main_menu())
            return SET_TOKENS_USER
        except ValueError:
            await update.message.reply_text("🤔 يبدو أن هذا ليس معرفًا صحيحًا! أرسل رقمًا فقط (مثال: 123456789). 🔄", reply_markup=self.get_admin_main_menu())
            return SET_TOKENS_USER

    async def handle_set_tokens_amount(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id != Config.ADMIN_ID:
            return ConversationHandler.END
        target_user_id = context.user_data.get("target_user_id")
        if not target_user_id or target_user_id not in self.users:
            await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى من القائمة. 😅", reply_markup=self.get_admin_main_menu())
            return ConversationHandler.END
        text = update.message.text.strip()
        Config.logger.info(f"Admin {user_id} entered token amount: {text} for user {target_user_id}")
        try:
            tokens = int(text)
            if tokens < 0:
                await update.message.reply_text("🤨 الرموز لا يمكن أن تكون سالبة! أرسل رقمًا موجبًا (مثال: 10). 🎟️", reply_markup=self.get_admin_main_menu())
                return SET_TOKENS_AMOUNT
            self.users[target_user_id]["tokens"] = tokens
            self.db.save_user(target_user_id, self.users[target_user_id])
            await update.message.reply_text(self.messages.USER_MESSAGES["set_tokens_success"].format(self.users[target_user_id]["name"], tokens), reply_markup=self.get_admin_main_menu())
            await context.bot.send_message(target_user_id, f"🎉 مرحبًا! تم تحديث رموزك بواسطة المشرف. لديك الآن {tokens} رمزًا متبقيًا! 🚀")
            del context.user_data["target_user_id"]
            del context.user_data["state"]
            Config.logger.info(f"Tokens set successfully for user {target_user_id}")
            return MAIN_MENU
        except ValueError:
            await update.message.reply_text("🤔 أرسل رقمًا صحيحًا للرموز (مثال: 10)! حاول مرة أخرى. 🔄", reply_markup=self.get_admin_main_menu())
            return SET_TOKENS_AMOUNT

    async def cancel(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id in self.users:
            self.users[user_id]["state"] = MAIN_MENU
            self.db.save_user(user_id, self.users[user_id])
        await update.message.reply_text(self.messages.USER_MESSAGES["main_menu"] if user_id != Config.ADMIN_ID else self.messages.ADMIN_MESSAGES["admin_menu"], 
                                        reply_markup=self.get_user_main_menu(user_id) if user_id != Config.ADMIN_ID else self.get_admin_main_menu())
        return MAIN_MENU

    async def fallback(self, update: Update, context: CallbackContext) -> int:
        user_id = update.effective_user.id
        if user_id not in self.users and user_id != Config.ADMIN_ID:
            return await self.start(update, context)
        current_state = self.users.get(user_id, {}).get("state", MAIN_MENU) if user_id != Config.ADMIN_ID else context.user_data.get("state", MAIN_MENU)
        handlers = {
            START: self.handle_start_choice,
            NAME: self.handle_name,
            PHONE: self.handle_phone,
            OTP: self.handle_otp,
            SET_TOKENS_USER: self.handle_set_tokens_user,
            SET_TOKENS_AMOUNT: self.handle_set_tokens_amount
        }
        if current_state in handlers:
            return await handlers[current_state](update, context)
        Config.logger.info(f"Fallback triggered for user {user_id}")
        await update.message.reply_text(self.messages.USER_MESSAGES["input_not_recognized"], 
                                        reply_markup=self.get_user_main_menu(user_id) if user_id in self.users and user_id != Config.ADMIN_ID else self.get_admin_main_menu())
        return MAIN_MENU

    def run(self):
        """Set up and run the bot"""
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback)
            ],
            states={
                START: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_start_choice)],
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_name)],
                WAITING_APPROVAL: [CallbackQueryHandler(self.button_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback)],
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_phone)],
                WAITING_PHONE_APPROVAL: [CallbackQueryHandler(self.button_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback)],
                OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_otp)],
                WAITING_OTP_APPROVAL: [CallbackQueryHandler(self.button_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback)],
                MAIN_MENU: [CallbackQueryHandler(self.button_handler), MessageHandler(filters.TEXT & ~filters.COMMAND, self.fallback)],
                SET_TOKENS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_set_tokens_user)],
                SET_TOKENS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_set_tokens_amount)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), MessageHandler(filters.ALL, self.fallback)],
            allow_reentry=True,
        )
        self.app.add_handler(conv_handler)
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        Config.logger.info("Bot started")
        self.app.run_polling()

# --- Main Execution ---
if __name__ == "__main__":
    bot = InternetBot()
    bot.run()