import os
import logging
import sqlite3
import json
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [8136590901]

# ==================== LOGGING ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def create_user(user_id, username, full_name):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# ==================== KEYBOARD ====================
def main_menu_keyboard(user_id):
    if user_id in ADMIN_IDS:
        keyboard = [
            ["👤 My Profile", "💰 Add Balance"],
            ["🔧 Admin Panel"]
        ]
    else:
        keyboard = [
            ["👤 My Profile", "💰 Add Balance"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username, user.full_name)

    await update.message.reply_text(
        "🎮 Welcome to your Telegram Bot!\n\nChoose an option:",
        reply_markup=main_menu_keyboard(user.id)
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "👤 My Profile":
        user = get_user(user_id)
        if user:
            await update.message.reply_text(
                f"👤 Profile\n\n"
                f"ID: {user[0]}\n"
                f"Username: @{user[1]}\n"
                f"Name: {user[2]}\n"
                f"Balance: ₹{user[3]}"
            )

    elif text == "💰 Add Balance":
        await update.message.reply_text("💸 Payment feature coming soon")

# ==================== MAIN ====================
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    app.run_polling()

if __name__ == "__main__":
    main()
