import os
import json
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
URL = "https://evgeniylish.pythonanywhere.com"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.route('/')
def index():
    return "Bot is running", 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            if text == '/start':
                send_message(chat_id, "Привет! Я бот на PythonAnywhere 🚀")
            else:
                send_message(chat_id, f"Ты написал: {text}")
        return "OK", 200
    except Exception as e:
        print(f"Error: {e}")
        return "Error", 500