# utils/helpers.py
from config import users

def get_user_data(user_id):
    """Retrieve user data by user_id"""
    return users.get(user_id, {})

def update_user_data(user_id, data):
    """Update user data by user_id"""
    if user_id in users:
        users[user_id].update(data)
    else:
        users[user_id] = data