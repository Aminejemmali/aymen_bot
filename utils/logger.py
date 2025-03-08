# utils/logger.py
import logging

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