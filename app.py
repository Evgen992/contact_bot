import os
import json
from flask import Flask, request
import requests
import database as db

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")
if not RENDER_URL:
    RENDER_URL = "https://contact-bot-1-suuf.onrender.com"
WEBHOOK_URL = f"{RENDER_URL}/webhook"

user_data = {}

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"Send error: {e}")

def save_contact(chat_id, username, phone, email, vk):
    try:
        db.add_or_update_contact(chat_id, username, phone, email, vk)
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False

def get_user_contacts(chat_id):
    try:
        row = db.get_contact_by_chat_id(chat_id)
        return {"phone": row[0], "email": row[1], "vk": row[2]} if row else None
    except Exception as e:
        print(f"Get error: {e}")
        return None

def get_all_contacts():
    try:
        rows = db.get_all_contacts()
        return [{"username": row[0], "phone": row[1], "email": row[2], "vk": row[3]} for row in rows]
    except Exception as e:
        print(f"All contacts error: {e}")
        return []

@app.route('/')
def index():
    return "Bot is running", 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    return response.json()

@app.route(f'/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            username = message['chat'].get('username', 'no_username')
            text = message.get('text', '')

            if chat_id in user_data:
                state = user_data[chat_id]['state']
                if state == 'awaiting_phone':
                    if db.validate_phone(text):
                        user_data[chat_id]['phone'] = text
                        user_data[chat_id]['state'] = 'awaiting_email'
                        send_message(chat_id, "Введите email (или '-'):")
                    else:
                        send_message(chat_id, "❌ Неверный формат. Введите 11 цифр, 7 или 8.")
                    return "OK", 200
                elif state == 'awaiting_email':
                    email = None if text == '-' else text
                    if email and not db.validate_email(email):
                        send_message(chat_id, "❌ Неверный email. Попробуйте снова (или '-'):")
                        return "OK", 200
                    user_data[chat_id]['email'] = email
                    user_data[chat_id]['state'] = 'awaiting_vk'
                    send_message(chat_id, "Введите ссылку ВК (или '-'):")
                    return "OK", 200
                elif state == 'awaiting_vk':
                    vk = None if text == '-' else text
                    if vk and not db.validate_vk(vk):
                        send_message(chat_id, "❌ Неверная ссылка ВК. Попробуйте снова (или '-'):")
                        return "OK", 200
                    user_data[chat_id]['vk'] = vk
                    data = user_data.pop(chat_id)
                    if save_contact(chat_id, username, data['phone'], data['email'], data['vk']):
                        send_message(chat_id, "✅ Контакты сохранены!")
                    else:
                        send_message(chat_id, "❌ Ошибка базы данных.")
                    return "OK", 200

            if text == '/start':
                send_message(chat_id, "👋 Привет! Я бот для сбора контактов.\n\n/add — добавить контакты\n/view — мои данные\n/list — список (админ)\n/help — помощь")
            elif text == '/help':
                send_message(chat_id, "/add — начать добавление\n/view — посмотреть свои данные\n/list — список всех (только для админа)")
            elif text == '/view':
                contacts = get_user_contacts(chat_id)
                if contacts:
                    send_message(chat_id, f"📞 Телефон: {contacts['phone'] or '—'}\n✉️ Email: {contacts['email'] or '—'}\n🌐 ВК: {contacts['vk'] or '—'}")
                else:
                    send_message(chat_id, "Нет данных. Используйте /add")
            elif text == '/list' and chat_id == 7354713280:
                contacts = get_all_contacts()
                if contacts:
                    msg = "📋 Список:\n\n" + "\n".join([f"@{c['username']}: {c['phone'] or '—'} / {c['email'] or '—'} / {c['vk'] or '—'}" for c in contacts])
                    send_message(chat_id, msg[:4000])
                else:
                    send_message(chat_id, "База пуста.")
            elif text == '/add':
                user_data[chat_id] = {'state': 'awaiting_phone'}
                send_message(chat_id, "Введите номер телефона (11 цифр, 7 или 8 в начале):")
            elif chat_id != 7354713280:
                send_message(chat_id, f"Неизвестная команда: {text}. Используйте /help")
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "Error", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)