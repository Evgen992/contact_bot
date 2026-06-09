import os
import psycopg2
import re

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def validate_phone(phone):
    return re.match(r'^[78]\d{10}$', phone) is not None

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def validate_vk(vk_url):
    return vk_url and len(vk_url) > 0
def add_or_update_contact(chat_id, username, phone=None, email=None, vk=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT phone, email, vk FROM contacts WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone()
    if row:
        new_phone = phone if phone else row[0]
        new_email = email if email else row[1]
        new_vk = vk if vk else row[2]
        cur.execute('''
            UPDATE contacts SET phone=%s, email=%s, vk=%s, username=%s, updated_at=NOW()
            WHERE chat_id=%s
        ''', (new_phone, new_email, new_vk, username, chat_id))
    else:
        cur.execute('''
            INSERT INTO contacts (chat_id, username, phone, email, vk)
            VALUES (%s, %s, %s, %s, %s)
        ''', (chat_id, username, phone, email, vk))
    conn.commit()
    cur.close()
    conn.close()

def get_contact_by_chat_id(chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT phone, email, vk FROM contacts WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_contact_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT phone, email, vk FROM contacts WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_all_contacts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, phone, email, vk FROM contacts")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows