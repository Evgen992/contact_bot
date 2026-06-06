import os
import json
from flask import Flask, request
import requests
import database as db

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = os.environ.get("RENDER_URL", "https://contact-bot.onrender.com")

# Хранилище временных данных пользователей
user_data = {}

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def save_contact(chat_id, username, phone, email, vk):
    try:
        db.add_or_update_contact(chat_id, username, phone, email, vk)
        return True
    except Exception as e:
        print(f"Error saving contact: {e}")
        return False

def get_user_contacts(chat_id):
    try:
        row = db.get_contact_by_chat_id(chat_id)
        if row:
            return {"phone": row[0], "email": row[1], "vk": row[2]}
        return None
    except Exception as e:
        print(f"Error getting user contacts: {e}")
        return None

def get_all_contacts():
    try:
        rows = db.get_all_contacts()
        result = []
        for row in rows:
            result.append({"username": row[0], "phone": row[1], "email": row[2], "vk": row[3]})
        return result
    except Exception as e:
        print(f"Error getting all contacts: {e}")
        return []

@app.route('/')
def index():
    return "Bot is running", 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            username = message['chat'].get('username', 'no_username')
            text = message.get('text', '')
            
            # Проверяем, находится ли пользователь в процессе добавления контактов
            if chat_id in user_data:
                state = user_data[chat_id]['state']
                
                if state == 'awaiting_phone':
                    phone = text.strip()
                    if db.validate_phone(phone):
                        user_data[chat_id]['phone'] = phone
                        user_data[chat_id]['state'] = 'awaiting_email'
                        send_message(chat_id, "Введите email (или '-' чтобы пропустить):")
                    else:
                        send_message(chat_id, "❌ Неверный формат телефона. Введите 11 цифр, начиная с 7 или 8:")
                    return "OK", 200
                
                elif state == 'awaiting_email':
                    email = text.strip()
                    if email == '-':
                        user_data[chat_id]['email'] = None
                    elif db.validate_email(email):
                        user_data[chat_id]['email'] = email
                    else:
                        send_message(chat_id, "❌ Неверный формат email. Попробуйте ещё раз (или '-' чтобы пропустить):")
                        return "OK", 200
                    
                    user_data[chat_id]['state'] = 'awaiting_vk'
                    send_message(chat_id, "Введите ссылку ВК (или '-' чтобы пропустить):")
                    return "OK", 200
                
                elif state == 'awaiting_vk':
                    vk = text.strip()
                    if vk == '-':
                        user_data[chat_id]['vk'] = None
                    elif db.validate_vk(vk):
                        user_data[chat_id]['vk'] = vk
                    else:
                        send_message(chat_id, "❌ Неверная ссылка ВК. Попробуйте ещё раз (или '-' чтобы пропустить):")
                        return "OK", 200
                    
                    # Сохраняем все данные
                    data = user_data[chat_id]
                    success = save_contact(chat_id, username, data['phone'], data['email'], data['vk'])
                    if success:
                        send_message(chat_id, "✅ Контакты успешно сохранены!")
                    else:
                        send_message(chat_id, "❌ Ошибка при сохранении контактов. Попробуйте позже.")
                    
                    # Удаляем временные данные
                    del user_data[chat_id]
                    return "OK", 200
            
            # Обработка команд
            if text == '/start':
                send_message(chat_id, "👋 Привет! Я бот для сбора контактов.\n\n"
                                     "📋 Команды:\n"
                                     "/add — добавить контакты\n"
                                     "/view — посмотреть свои данные\n"
                                     "/list — список всех (только админ)\n"
                                     "/help — помощь")
            
            elif text == '/help':
                send_message(chat_id, "Доступные команды:\n"
                                     "/add — добавить или обновить контакты\n"
                                     "/view — посмотреть свои контакты\n"
                                     "/list — список всех пользователей\n"
                                     "/start — приветствие")
            
            elif text == '/list':
                if chat_id == 7354713280:  # твой ID
                    contacts = get_all_contacts()
                    if contacts:
                        msg = "📋 Список контактов:\n\n"
                        for c in contacts:
                            msg += f"👤 @{c['username'] or 'no_username'}\n"
                            msg += f"📞 {c['phone'] or '—'}\n"
                            msg += f"✉️ {c['email'] or '—'}\n"
                            msg += f"🌐 {c['vk'] or '—'}\n\n"
                        send_message(chat_id, msg[:4000])
                    else:
                        send_message(chat_id, "База пуста.")
                else:
                    send_message(chat_id, "❌ Только администратор может использовать эту команду.")
            
            elif text == '/view':
                contacts = get_user_contacts(chat_id)
                if contacts:
                    send_message(chat_id, f"📞 Телефон: {contacts['phone'] or 'не указан'}\n"
                                          f"✉️ Email: {contacts['email'] or 'не указан'}\n"
                                          f"🌐 ВК: {contacts['vk'] or 'не указан'}")
                else:
                    send_message(chat_id, "Нет данных. Используйте /add")
            
            elif text == '/add':
                # Начинаем процесс добавления контактов
                user_data[chat_id] = {'state': 'awaiting_phone', 'phone': None, 'email': None, 'vk': None}
                send_message(chat_id, "Введите номер телефона (11 цифр, начиная с 7 или 8):")
            
            else:
                send_message(chat_id, f"❌ Неизвестная команда: {text}\n\nИспользуйте /help для списка команд.")
        
        return "OK", 200
    except Exception as e:
        print(f"Error in webhook: {e}")
        return "Error", 500