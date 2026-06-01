import sqlite3
import re

DB_NAME = "contacts.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            email TEXT,
            vk TEXT,
            username TEXT,
            chat_id INTEGER UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def validate_phone(phone):
    # Простая проверка: 11 цифр, начинается с 7 или 8
    return re.match(r'^[78]\d{10}$', phone) is not None

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def validate_vk(vk_url):
    return re.match(r'^https?://(vk\.com|m\.vk\.com)/[\w\.]+$', vk_url) is not None

def add_or_update_contact(chat_id, username, phone=None, email=None, vk=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверяем, есть ли уже такой chat_id
    cursor.execute("SELECT phone, email, vk FROM contacts WHERE chat_id = ?", (chat_id,))
    existing = cursor.fetchone()

    if existing:
        # Обновляем только переданные непустые поля
        new_phone = phone if phone else existing[0]
        new_email = email if email else existing[1]
        new_vk = vk if vk else existing[2]
        cursor.execute('''
            UPDATE contacts
            SET phone = ?, email = ?, vk = ?, username = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        ''', (new_phone, new_email, new_vk, username, chat_id))
    else:
        # Вставляем новую запись
        cursor.execute('''
            INSERT INTO contacts (chat_id, username, phone, email, vk)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, username, phone, email, vk))

    conn.commit()
    conn.close()