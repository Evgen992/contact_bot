import os
import sqlite3
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")

RENDER_URL = "https://contact-bot-c3hw.onrender.com"
WEBHOOK_URL = f"{RENDER_URL}/webhook"

logging.basicConfig(level=logging.INFO)

flask_app = Flask(__name__)

# Создаём и инициализируем Application сразу
application = Application.builder().token(TOKEN).build()
application.initialize()

ADMIN_ID = 7354713280
PHONE, EMAIL, VK, PHONE_ONLY, EMAIL_ONLY, VK_ONLY = range(6)

# === Обработчики команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для сбора контактов.\n\n"
        "📋 Основные команды:\n"
        "/add — добавить все контакты сразу\n"
        "/view — посмотреть свои данные\n"
        "/view @username — данные другого пользователя\n\n"
        "✏️ Обновить отдельно:\n"
        "/add_phone — телефон\n"
        "/add_email — email\n"
        "/add_vk — ВК\n\n"
        "🔐 Админ-команда:\n"
        "/list — список всех"
    )

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("❌ Только администратор может использовать эту команду.")
        return

    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, phone, email, vk FROM contacts")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("База пуста.")
        return

    message = "📋 Список контактов:\n\n"
    for username, phone, email, vk in rows:
        message += f"👤 @{username or 'no_username'}\n"
        message += f"📞 {phone or '—'}\n"
        message += f"✉️ {email or '—'}\n"
        message += f"🌐 {vk or '—'}\n\n"

    if len(message) > 4000:
        for x in range(0, len(message), 4000):
            await update.message.reply_text(message[x:x+4000])
    else:
        await update.message.reply_text(message)

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите номер телефона (11 цифр, 7 или 8 в начале):")
    return PHONE

async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    if db.validate_phone(phone):
        context.user_data['phone'] = phone
        await update.message.reply_text("Введите email (или '-' чтобы пропустить):")
        return EMAIL
    else:
        await update.message.reply_text("Неверный формат. Попробуйте ещё раз.")
        return PHONE

async def add_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    if email == '-':
        context.user_data['email'] = None
    elif db.validate_email(email):
        context.user_data['email'] = email
    else:
        await update.message.reply_text("Неверный email. Попробуйте ещё раз (или '-'):")
        return EMAIL
    await update.message.reply_text("Введите ссылку ВК (или '-'):")
    return VK

async def add_vk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vk = update.message.text
    if vk == '-':
        context.user_data['vk'] = None
    elif db.validate_vk(vk):
        context.user_data['vk'] = vk
    else:
        await update.message.reply_text("Неверная ссылка. Попробуйте ещё раз (или '-'):")
        return VK

    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    db.add_or_update_contact(
        chat_id=chat_id,
        username=username,
        phone=context.user_data.get('phone'),
        email=context.user_data.get('email'),
        vk=context.user_data.get('vk')
    )
    await update.message.reply_text("✅ Контакты сохранены.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        username = context.args[0].lstrip('@')
        conn = sqlite3.connect(db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, email, vk FROM contacts WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            phone, email, vk = row
            await update.message.reply_text(
                f"📞 Телефон: {phone or 'не указан'}\n"
                f"✉️ Email: {email or 'не указан'}\n"
                f"🌐 ВК: {vk or 'не указан'}"
            )
        else:
            await update.message.reply_text("Пользователь не найден.")
    else:
        chat_id = update.effective_chat.id
        conn = sqlite3.connect(db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, email, vk FROM contacts WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            phone, email, vk = row
            await update.message.reply_text(
                f"📞 Телефон: {phone or 'не указан'}\n"
                f"✉️ Email: {email or 'не указан'}\n"
                f"🌐 ВК: {vk or 'не указан'}"
            )
        else:
            await update.message.reply_text("Нет данных. Используйте /add")

# === Отдельные обновления ===
async def add_phone_only_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите номер телефона (11 цифр, 7 или 8 в начале):")
    return PHONE_ONLY

async def add_phone_only_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    if db.validate_phone(phone):
        chat_id = update.effective_chat.id
        username = update.effective_chat.username or "no_username"
        conn = sqlite3.connect(db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT email, vk FROM contacts WHERE chat_id = ?", (chat_id,))
        existing = cursor.fetchone()
        if existing:
            email, vk = existing
            cursor.execute('UPDATE contacts SET phone=?, username=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?',
                           (phone, username, chat_id))
        else:
            cursor.execute('INSERT INTO contacts (chat_id, username, phone, email, vk) VALUES (?, ?, ?, ?, ?)',
                           (chat_id, username, phone, None, None))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Телефон сохранён!")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Неверный формат. Попробуйте ещё раз.")
        return PHONE_ONLY

async def add_email_only_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите email (или '-' чтобы пропустить):")
    return EMAIL_ONLY

async def add_email_only_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    if email == '-':
        email = None
    elif not db.validate_email(email):
        await update.message.reply_text("❌ Неверный email. Попробуйте ещё раз (или '-'):")
        return EMAIL_ONLY

    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT phone, vk FROM contacts WHERE chat_id = ?", (chat_id,))
    existing = cursor.fetchone()
    if existing:
        phone, vk = existing
        cursor.execute('UPDATE contacts SET email=?, username=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?',
                       (email, username, chat_id))
    else:
        cursor.execute('INSERT INTO contacts (chat_id, username, phone, email, vk) VALUES (?, ?, ?, ?, ?)',
                       (chat_id, username, None, email, None))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Email сохранён!")
    return ConversationHandler.END

async def add_vk_only_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ссылку ВК (или '-'):")
    return VK_ONLY

async def add_vk_only_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vk = update.message.text
    if vk == '-':
        vk = None
    elif not db.validate_vk(vk):
        await update.message.reply_text("❌ Неверная ссылка. Попробуйте ещё раз (или '-'):")
        return VK_ONLY

    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT phone, email FROM contacts WHERE chat_id = ?", (chat_id,))
    existing = cursor.fetchone()
    if existing:
        phone, email = existing
        cursor.execute('UPDATE contacts SET vk=?, username=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?',
                       (vk, username, chat_id))
    else:
        cursor.execute('INSERT INTO contacts (chat_id, username, phone, email, vk) VALUES (?, ?, ?, ?, ?)',
                       (chat_id, username, None, None, vk))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ ВК сохранён!")
    return ConversationHandler.END

# === Регистрация ===
conv_add = ConversationHandler(
    entry_points=[CommandHandler("add", add_start)],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_email)],
        VK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_vk)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

conv_phone = ConversationHandler(
    entry_points=[CommandHandler("add_phone", add_phone_only_start)],
    states={PHONE_ONLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone_only_handler)]},
    fallbacks=[CommandHandler("cancel", cancel)],
)

conv_email = ConversationHandler(
    entry_points=[CommandHandler("add_email", add_email_only_start)],
    states={EMAIL_ONLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_email_only_handler)]},
    fallbacks=[CommandHandler("cancel", cancel)],
)

conv_vk = ConversationHandler(
    entry_points=[CommandHandler("add_vk", add_vk_only_start)],
    states={VK_ONLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_vk_only_handler)]},
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_add)
application.add_handler(conv_phone)
application.add_handler(conv_email)
application.add_handler(conv_vk)
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("view", view))
application.add_handler(CommandHandler("list", list_users))

# === Вебхук ===
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "Error", 500

@flask_app.route('/')
def index():
    return "Contact Bot is running", 200

@flask_app.route('/health')
def health():
    return "OK", 200

# === Точка входа ===
if __name__ == "__main__":
    db.init_db()
    
    # Установка вебхука (один раз при запуске)
    async def set_webhook():
        await application.bot.set_webhook(url=WEBHOOK_URL)
    asyncio.run(set_webhook())
    
    # Запуск Flask
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)