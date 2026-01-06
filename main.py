import os
import logging
import sqlite3
import json
import random
import string
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in environment variables")
ADMIN_IDS = [5678991839]
DEFAULT_UPI = "yourupi@upi"
DEFAULT_UPI_NAME = "Your Brand Name"
DEFAULT_CRYPTO = {
    "USDT TRC20": "THb4Q7Cb4qk5Uq5Z5Q5q5Q5q5Q5q5Q5q5Q5",
    "USDT ERC20": "0x5b5Q5q5Q5q5Q5q5Q5q5Q5q5Q5q5Q5q5Q5q5",
    "Bitcoin": "bc1q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5q5"
}

# Conversation states
MAIN_MENU, ADD_BALANCE, DEPOSIT_AMOUNT, DEPOSIT_SCREENSHOT, DEPOSIT_CRYPTO_TXID = range(5)
ADMIN_MENU, ADMIN_DEPOSITS, ADMIN_ORDERS, ADMIN_PRODUCTS, ADMIN_SETTINGS, ADMIN_USERS = range(10, 16)
ADMIN_ADD_STOCK, ADMIN_EDIT_PRICE = range(16, 18)

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Countries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            flag TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Telegram accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER,
            account_type TEXT,
            price REAL,
            stock INTEGER DEFAULT 0,
            description TEXT,
            details_template TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (country_id) REFERENCES countries (id)
        )
    ''')
    
    # Game Numbers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price REAL DEFAULT 50,
            duration_hours INTEGER DEFAULT 24,
            description TEXT DEFAULT 'Game Registration Number',
            details_template TEXT DEFAULT 'Phone: +91XXXXXXXXXX\nOTP will be sent after admin approval',
            stock INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            user_id INTEGER,
            product_type TEXT,
            product_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            phone_number TEXT,
            otp_code TEXT,
            details TEXT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivered_by INTEGER,
            delivery_date TIMESTAMP
        )
    ''')
    
    # Deposits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deposit_id TEXT UNIQUE,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            transaction_id TEXT,
            screenshot TEXT,
            status TEXT DEFAULT 'pending',
            admin_id INTEGER,
            admin_note TEXT,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            process_date TIMESTAMP
        )
    ''')
    
    # Payment methods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_type TEXT,
            details TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Insert default data
    cursor.execute("SELECT COUNT(*) FROM countries")
    if cursor.fetchone()[0] == 0:
        countries = [
            ('India', '🇮🇳'), ('Brazil', '🇧🇷'), ('Tanzania', '🇹🇿'),
            ('Ecuador', '🇪🇨'), ('Malaysia', '🇲🇾'), ('Thailand', '🇹🇭'),
            ('USA', '🇺🇸'), ('UK', '🇬🇧'), ('Russia', '🇷🇺'),
            ('China', '🇨🇳'), ('Japan', '🇯🇵'), ('Germany', '🇩🇪')
        ]
        cursor.executemany("INSERT INTO countries (name, flag) VALUES (?, ?)", countries)
    
    cursor.execute("SELECT COUNT(*) FROM telegram_accounts")
    if cursor.fetchone()[0] == 0:
        telegram_data = [
            (1, 'Fresh Account', 120, 100, 'Telegram Account - India 🇮🇳', 'Phone: +91XXXXXXXXXX\nOTP will be sent\nValid: 24 hours'),
            (2, 'Fresh Account', 58, 50, 'Telegram Account - Brazil 🇧🇷', 'Phone: +55XXXXXXXXXX\nFull access'),
            (3, 'Fresh Account', 4, 30, 'Telegram Account - Tanzania 🇹🇿', 'Phone: +255XXXXXXXX\nReady to use'),
            (4, 'Fresh Account', 60, 40, 'Telegram Account - Ecuador 🇪🇨', 'Phone: +593XXXXXXXX\nNew number'),
            (5, 'Fresh Account', 62, 45, 'Telegram Account - Malaysia 🇲🇾', 'Phone: +60XXXXXXXX\nFresh SIM'),
            (6, 'Fresh Account', 62, 50, 'Telegram Account - Thailand 🇹🇭', 'Phone: +66XXXXXXXX\nActive number'),
            (7, 'Premium Account', 200, 20, 'Telegram Account - USA 🇺🇸', 'Phone: +1XXXXXXXXXX\nPremium USA number'),
            (8, 'Fresh Account', 150, 60, 'Telegram Account - UK 🇬🇧', 'Phone: +44XXXXXXXXXX\nUK virtual'),
            (9, 'Fresh Account', 80, 70, 'Telegram Account - Russia 🇷🇺', 'Phone: +7XXXXXXXXXX\nRussian number'),
            (10, 'Fresh Account', 100, 40, 'Telegram Account - China 🇨🇳', 'Phone: +86XXXXXXXXXX\nChina mobile'),
            (11, 'Fresh Account', 180, 25, 'Telegram Account - Japan 🇯🇵', 'Phone: +81XXXXXXXXXX\nJapan SIM'),
            (12, 'Premium Account', 140, 35, 'Telegram Account - Germany 🇩🇪', 'Phone: +49XXXXXXXXXX\nGermany number')
        ]
        cursor.executemany(
            "INSERT INTO telegram_accounts (country_id, account_type, price, stock, description, details_template) VALUES (?, ?, ?, ?, ?, ?)",
            telegram_data
        )
    
    cursor.execute("SELECT COUNT(*) FROM game_numbers")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO game_numbers (price, description) VALUES (?, ?)",
            (50, 'Game Registration Number - Any Game')
        )
    
    cursor.execute("SELECT COUNT(*) FROM payment_methods")
    if cursor.fetchone()[0] == 0:
        payment_methods = [
            ('upi', json.dumps({'upi_id': DEFAULT_UPI, 'name': DEFAULT_UPI_NAME})),
            ('crypto', json.dumps(DEFAULT_CRYPTO))
        ]
        cursor.executemany(
            "INSERT INTO payment_methods (method_type, details) VALUES (?, ?)",
            payment_methods
        )
    
    conn.commit()
    conn.close()

# ==================== DATABASE FUNCTIONS ====================
def get_db():
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    result = cursor.fetchall()
    conn.close()
    return [dict(row) for row in result]

def get_user(user_id):
    result = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return result[0] if result else None

def create_user(user_id, username, full_name):
    execute_query(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
        (user_id, username, full_name)
    )

def update_balance(user_id, amount):
    execute_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

def get_balance(user_id):
    result = execute_query("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    return result[0]['balance'] if result else 0

def get_countries():
    return execute_query("SELECT * FROM countries WHERE is_active = 1 LIMIT 12")

def get_telegram_accounts(country_id=None):
    if country_id:
        return execute_query('''
            SELECT ta.*, c.name as country_name, c.flag 
            FROM telegram_accounts ta 
            JOIN countries c ON ta.country_id = c.id 
            WHERE ta.country_id = ? AND ta.is_active = 1
        ''', (country_id,))
    return execute_query('''
        SELECT ta.*, c.name as country_name, c.flag 
        FROM telegram_accounts ta 
        JOIN countries c ON ta.country_id = c.id 
        WHERE ta.is_active = 1
    ''')

def get_game_number_product():
    result = execute_query("SELECT * FROM game_numbers WHERE is_active = 1 LIMIT 1")
    return result[0] if result else None

def create_order(user_id, product_type, product_id, amount, details=""):
    order_id = f"ORD{random.randint(10000, 99999)}{datetime.now().strftime('%H%M%S')}"
    execute_query(
        "INSERT INTO orders (order_id, user_id, product_type, product_id, amount, details) VALUES (?, ?, ?, ?, ?, ?)",
        (order_id, user_id, product_type, product_id, amount, details)
    )
    execute_query("UPDATE users SET total_orders = total_orders + 1, total_spent = total_spent + ? WHERE user_id = ?", (amount, user_id))
    return order_id

def create_deposit(user_id, amount, method, transaction_id="", screenshot=""):
    deposit_id = f"DEP{random.randint(10000, 99999)}{datetime.now().strftime('%H%M%S')}"
    execute_query(
        "INSERT INTO deposits (deposit_id, user_id, amount, method, transaction_id, screenshot) VALUES (?, ?, ?, ?, ?, ?)",
        (deposit_id, user_id, amount, method, transaction_id, screenshot)
    )
    return deposit_id

def get_pending_deposits():
    return execute_query("SELECT * FROM deposits WHERE status = 'pending' ORDER BY request_date")

def get_pending_orders():
    return execute_query("SELECT * FROM orders WHERE status = 'pending' ORDER BY order_date")

def get_all_users():
    return execute_query("SELECT * FROM users ORDER BY join_date DESC")

def update_stock(product_type, product_id, quantity):
    if product_type == 'game':
        execute_query("UPDATE game_numbers SET stock = stock + ? WHERE id = ?", (quantity, product_id))
    elif product_type == 'telegram':
        execute_query("UPDATE telegram_accounts SET stock = stock + ? WHERE id = ?", (quantity, product_id))

def update_price(product_type, product_id, price):
    if product_type == 'game':
        execute_query("UPDATE game_numbers SET price = ? WHERE id = ?", (price, product_id))
    elif product_type == 'telegram':
        execute_query("UPDATE telegram_accounts SET price = ? WHERE id = ?", (price, product_id))

def update_upi(upi_id, upi_name):
    new_details = json.dumps({'upi_id': upi_id, 'name': upi_name})
    execute_query("UPDATE payment_methods SET details = ? WHERE method_type = 'upi'", (new_details,))

def update_crypto(coin, address):
    payment_methods = execute_query("SELECT * FROM payment_methods WHERE method_type = 'crypto'")
    if payment_methods:
        crypto_method = json.loads(payment_methods[0]['details'])
        crypto_method[coin] = address
        execute_query("UPDATE payment_methods SET details = ? WHERE method_type = 'crypto'", (json.dumps(crypto_method),))

def get_system_stats():
    stats = {}
    stats['total_users'] = execute_query("SELECT COUNT(*) as count FROM users")[0]['count']
    stats['total_orders'] = execute_query("SELECT COUNT(*) as count FROM orders")[0]['count']
    stats['total_sales'] = execute_query("SELECT SUM(amount) as total FROM orders WHERE status = 'delivered'")[0]['total'] or 0
    stats['pending_deposits'] = execute_query("SELECT COUNT(*) as count FROM deposits WHERE status = 'pending'")[0]['count']
    stats['pending_orders'] = execute_query("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")[0]['count']
    stats['total_balance'] = execute_query("SELECT SUM(balance) as total FROM users")[0]['total'] or 0
    return stats

def approve_deposit(deposit_id, admin_id):
    deposit = execute_query("SELECT * FROM deposits WHERE deposit_id = ?", (deposit_id,))[0]
    if deposit:
        # Update deposit status
        execute_query(
            "UPDATE deposits SET status = 'approved', admin_id = ?, process_date = CURRENT_TIMESTAMP WHERE deposit_id = ?",
            (admin_id, deposit_id)
        )
        # Add balance to user
        update_balance(deposit['user_id'], deposit['amount'])
        return True
    return False

def reject_deposit(deposit_id, admin_id):
    execute_query(
        "UPDATE deposits SET status = 'rejected', admin_id = ?, process_date = CURRENT_TIMESTAMP WHERE deposit_id = ?",
        (admin_id, deposit_id)
    )
    return True

def complete_order(order_id, admin_id, phone_number=None, otp_code=None):
    updates = []
    params = []
    
    if phone_number:
        updates.append("phone_number = ?")
        params.append(phone_number)
    
    if otp_code:
        updates.append("otp_code = ?")
        params.append(otp_code)
    
    updates.append("status = 'delivered'")
    updates.append("delivery_date = CURRENT_TIMESTAMP")
    updates.append("delivered_by = ?")
    params.append(admin_id)
    
    params.append(order_id)
    
    query = f"UPDATE orders SET {', '.join(updates)} WHERE order_id = ?"
    execute_query(query, params)
    return True

# ==================== KEYBOARD FUNCTIONS ====================
def main_menu_keyboard(user_id):
    if user_id in ADMIN_IDS:
        keyboard = [
            ["👤 My Profile", "💰 Add Balance"],
            ["🛒 Telegram Accounts", "📱 Buy Game Number"],
            ["📜 My Orders", "📞 Support"],
            ["🔧 Admin Panel"]
        ]
    else:
        keyboard = [
            ["👤 My Profile", "💰 Add Balance"],
            ["🛒 Telegram Accounts", "📱 Buy Game Number"],
            ["📜 My Orders", "📞 Support"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def back_to_main_keyboard(user_id):
    keyboard = [["🔙 Main Menu"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def payment_methods_keyboard():
    keyboard = [
        ["💸 UPI Payment", "₿ Crypto Payment"],
        ["🔙 Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def countries_keyboard():
    countries = get_countries()
    keyboard = []
    row = []
    for i, country in enumerate(countries):
        btn_text = f"{country['flag']} {country['name']}"
        row.append(btn_text)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(["🔙 Main Menu"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_menu_keyboard():
    keyboard = [
        ["📊 Dashboard", "💰 Pending Deposits"],
        ["📱 Pending Orders", "👤 All Users"],
        ["🛒 Products", "⚙️ Settings"],
        ["➕ Add Stock", "✏️ Edit Price"],
        ["🔙 Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def admin_back_keyboard():
    keyboard = [["🔙 Admin Panel"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_settings_keyboard():
    keyboard = [
        ["💸 UPI Settings", "₿ Crypto Settings"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_products_keyboard():
    keyboard = [
        ["🛒 Telegram Accounts", "📱 Game Numbers"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def telegram_accounts_keyboard(country_id):
    accounts = get_telegram_accounts(country_id)
    keyboard = []
    for account in accounts:
        keyboard.append([f"📱 {account['account_type']} - ₹{account['price']}"])
    keyboard.append(["🔙 Countries", "🔙 Main Menu"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def confirm_purchase_keyboard():
    keyboard = [
        ["✅ Confirm Purchase", "❌ Cancel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_deposit_actions_keyboard(deposit_id):
    keyboard = [
        ["✅ Approve", "❌ Reject"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_order_actions_keyboard():
    keyboard = [
        ["📱 Send Phone", "🔢 Send OTP"],
        ["✅ Mark Complete", "🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_stock_keyboard():
    keyboard = [
        ["➕ Game Stock", "➕ Telegram Stock"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def admin_price_keyboard():
    keyboard = [
        ["✏️ Game Price", "✏️ Telegram Price"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def quantity_keyboard():
    keyboard = [
        ["➕10", "➕50", "➕100"],
        ["➕200", "➕500", "➕1000"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def price_keyboard():
    keyboard = [
        ["₹50", "₹100", "₹200"],
        ["₹500", "₹1000", "Custom"],
        ["🔙 Admin Panel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# ==================== MESSAGE HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username, user.full_name)
    
    welcome_text = """
🎮 Welcome to Premium Account Store!

🌟 Available Services:

🛒 Telegram Accounts (12 Countries)
• India, USA, UK, Brazil, Russia, etc.
• Fresh & Premium numbers
• Instant delivery

📱 Game Registration Numbers
• Any game - Any platform
• Phone number + OTP delivery
• One click purchase

💸 Easy Payments:
• UPI (Instant)
• Crypto (Bitcoin/USDT)

📞 24/7 Support
🔒 100% Safe & Secure

Select an option below:
    """
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(user.id)
    )
    return MAIN_MENU

# ==================== USER PANEL HANDLERS ====================
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "👤 My Profile":
        user = get_user(user_id)
        if user:
            profile_text = f"""
👤 Your Profile

User ID: {user['user_id']}
Username: @{user['username'] if user['username'] else 'N/A'}
Name: {user['full_name']}

💰 Balance: ₹{user['balance']:.2f}
📦 Total Orders: {user['total_orders']}
💸 Total Spent: ₹{user['total_spent']:.2f}
📅 Member Since: {user['join_date'][:10]}
            """
            await update.message.reply_text(
                profile_text,
                reply_markup=main_menu_keyboard(user_id)
            )
        return MAIN_MENU
    
    elif text == "💰 Add Balance":
        await update.message.reply_text(
            "💸 Select Payment Method:\n\n"
            "1. UPI - Instant deposit (Recommended)\n"
            "2. Crypto - Bitcoin/USDT\n\n"
            "Choose an option:",
            reply_markup=payment_methods_keyboard()
            )
# ==================== MAIN RUNNER ====================
def main():
    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # BASIC HANDLERS
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
    )

    print("✅ Bot started successfully...")
    application.run_polling()

if __name__ == "__main__":
    main()
