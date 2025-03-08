# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Shared variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Store user data
users = {}  # {user_id: {"name": "", "phones": [], "approved": False, "tokens": 3, "otp_verified_numbers": []}}