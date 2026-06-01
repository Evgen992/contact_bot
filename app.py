import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv
import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")

logging.basicConfig(level=logging.INFO)

# ID администратора (только этот пользователь может использовать /list)
ADMIN_ID = 7354713280

# Состояния для разговора

PHONE, EMAIL, VK, PHONE_ONLY, EMAIL_ONLY, VK_ONLY = range(6)

# Flask-приложение, которое будет "держать" порт
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Contact Bot is running", 200

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

ADMIN_ID = 7354713280
PHONE, EMAIL, VK, PHONE_ONLY, EMAIL_ONLY, VK_ONLY = range(6)

# ... все ваши существующие функции (start, add_phone, add_email и т.д.) ...
# Они остаются без изменений, я их здесь не повторяю для краткости.
# Просто убедитесь, что весь ваш код обработчиков команд остался ниже.

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # ... все ваши обработчики (conv_handler, conv_phone и т.д.) ...
    # Они остаются без изменений.

    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask).start()

    logging.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    db.init_db()
    main()

async def list_users(update: Update, context):
    """Показывает список всех пользователей (только для администратора)"""
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

    # Разбиваем, если сообщение слишком длинное
    if len(message) > 4000:
        for x in range(0, len(message), 4000):
            await update.message.reply_text(message[x:x+4000])
    else:
        await update.message.reply_text(message)

async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Я бот для сбора контактов.\n\n"
        "📋 Основные команды:\n"
        "/add — добавить все контакты сразу (телефон, email, ВК)\n"
        "/view — посмотреть свои данные\n"
        "/view @username — посмотреть данные другого пользователя\n\n"
        "✏️ Обновить отдельные поля:\n"
        "/add_phone — добавить или обновить телефон\n"
        "/add_email — добавить или обновить email\n"
        "/add_vk — добавить или обновить ВК\n\n"
        "🔐 Админ-команда:\n"
        "/list — список всех пользователей (только для админа)"
    )

async def add_start(update: Update, context):
    await update.message.reply_text("Введите ваш номер телефона (11 цифр, начинается с 7 или 8):")
    return PHONE

async def add_phone(update: Update, context):
    phone = update.message.text
    if db.validate_phone(phone):
        context.user_data['phone'] = phone
        await update.message.reply_text("Теперь введите ваш email (или отправьте '-' чтобы пропустить):")
        return EMAIL
    else:
        await update.message.reply_text("Неверный формат. Попробуйте ещё раз (11 цифр, 7 или 8 в начале):")
        return PHONE

async def add_email(update: Update, context):
    email = update.message.text
    if email == '-':
        context.user_data['email'] = None
    elif db.validate_email(email):
        context.user_data['email'] = email
    else:
        await update.message.reply_text("Неверный email. Попробуйте ещё раз (или '-' чтобы пропустить):")
        return EMAIL

    await update.message.reply_text("Введите ссылку на профиль ВК (или '-' чтобы пропустить):")
    return VK

async def add_vk(update: Update, context):
    vk = update.message.text
    if vk == '-':
        context.user_data['vk'] = None
    elif db.validate_vk(vk):
        context.user_data['vk'] = vk
    else:
        await update.message.reply_text("Неверная ссылка ВК. Попробуйте ещё раз (или '-' чтобы пропустить):")
        return VK

    # Сохраняем все данные
    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    db.add_or_update_contact(
        chat_id=chat_id,
        username=username,
        phone=context.user_data.get('phone'),
        email=context.user_data.get('email'),
        vk=context.user_data.get('vk')
    )
    await update.message.reply_text("✅ Спасибо! Ваши контакты сохранены.")
    return ConversationHandler.END

async def cancel(update: Update, context):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

async def view(update: Update, context):
    """Показывает контакты пользователя (свои или по @username)"""
    # Если есть аргумент (например, @username), пытаемся найти пользователя
    if context.args:
        username = context.args[0].lstrip('@')  # убираем @ в начале
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
        # Без аргумента — показываем свои данные
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
            await update.message.reply_text("Вы ещё не добавляли контакты. Используйте /add")

async def add_phone_only(update: Update, context):
    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    
    # Запрашиваем телефон
    await update.message.reply_text("Введите ваш номер телефона (11 цифр, начинается с 7 или 8):")
    
    def phone_received(update: Update, context):
        phone = update.message.text
        if db.validate_phone(phone):
            # Обновляем только телефон, не трогая email и VK
            conn = sqlite3.connect(db.DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT email, vk FROM contacts WHERE chat_id = ?", (chat_id,))
            existing = cursor.fetchone()
            if existing:
                email, vk = existing
                cursor.execute('''
                    UPDATE contacts
                    SET phone = ?, username = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                ''', (phone, username, chat_id))
            else:
                cursor.execute('''
                    INSERT INTO contacts (chat_id, username, phone, email, vk)
                    VALUES (?, ?, ?, ?, ?)
                ''', (chat_id, username, phone, None, None))
            conn.commit()
            conn.close()
            update.message.reply_text("✅ Телефон сохранён!")
            return ConversationHandler.END
        else:
            update.message.reply_text("❌ Неверный формат. Попробуйте ещё раз.")
            return PHONE_ONLY
    
    return ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

async def add_email_only(update: Update, context):
    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    
    await update.message.reply_text("Введите ваш email (или '-' чтобы пропустить):")
    
    def email_received(update: Update, context):
        email = update.message.text
        if email == '-':
            email = None
        elif not db.validate_email(email):
            update.message.reply_text("❌ Неверный email. Попробуйте ещё раз (или '-' чтобы пропустить):")
            return EMAIL_ONLY
        
        conn = sqlite3.connect(db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, vk FROM contacts WHERE chat_id = ?", (chat_id,))
        existing = cursor.fetchone()
        if existing:
            phone, vk = existing
            cursor.execute('''
                UPDATE contacts
                SET email = ?, username = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            ''', (email, username, chat_id))
        else:
            cursor.execute('''
                INSERT INTO contacts (chat_id, username, phone, email, vk)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, username, None, email, None))
        conn.commit()
        conn.close()
        update.message.reply_text("✅ Email сохранён!")
        return ConversationHandler.END
    
    return ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, email_received)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

async def add_vk_only(update: Update, context):
    chat_id = update.effective_chat.id
    username = update.effective_chat.username or "no_username"
    
    await update.message.reply_text("Введите ссылку на профиль ВКонтакте (или '-' чтобы пропустить):")
    
    def vk_received(update: Update, context):
        vk = update.message.text
        if vk == '-':
            vk = None
        elif not db.validate_vk(vk):
            update.message.reply_text("❌ Неверная ссылка ВК. Попробуйте ещё раз (или '-' чтобы пропустить):")
            return VK_ONLY
        
        conn = sqlite3.connect(db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT phone, email FROM contacts WHERE chat_id = ?", (chat_id,))
        existing = cursor.fetchone()
        if existing:
            phone, email = existing
            cursor.execute('''
                UPDATE contacts
                SET vk = ?, username = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            ''', (vk, username, chat_id))
        else:
            cursor.execute('''
                INSERT INTO contacts (chat_id, username, phone, email, vk)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, username, None, None, vk))
        conn.commit()
        conn.close()
        update.message.reply_text("✅ ВК сохранён!")
        return ConversationHandler.END
    
    return ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, vk_received)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Основной диалог /add
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_email)],
            VK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_vk)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Отдельные диалоги для обновления полей
    conv_phone = ConversationHandler(
        entry_points=[CommandHandler("add_phone", add_phone_only)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    conv_email = ConversationHandler(
        entry_points=[CommandHandler("add_email", add_email_only)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    conv_vk = ConversationHandler(
        entry_points=[CommandHandler("add_vk", add_vk_only)],
        states={},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Регистрируем все обработчики
    app.add_handler(conv_handler)
    app.add_handler(conv_phone)
    app.add_handler(conv_email)
    app.add_handler(conv_vk)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("list", list_users))

    logging.info("Бот запущен...")
    app.run_polling()

    # Регистрируем все обработчики
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("list", list_users))  # только для админа

    logging.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    db.init_db()
    main()