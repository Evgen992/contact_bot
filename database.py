import os
import asyncpg
import re

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не задан в переменных окружения")

async def get_connection():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    # Таблица уже создана вручную в Supabase, можно пропустить
    pass

def validate_phone(phone):
    return re.match(r'^[78]\d{10}$', phone) is not None

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def validate_vk(vk_url):
    return vk_url and ('vk.com' in vk_url or 'm.vk.com' in vk_url)
async def add_or_update_contact(chat_id, username, phone=None, email=None, vk=None):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT phone, email, vk FROM contacts WHERE chat_id = $1", chat_id)
    if row:
        new_phone = phone if phone else row['phone']
        new_email = email if email else row['email']
        new_vk = vk if vk else row['vk']
        await conn.execute('''
            UPDATE contacts SET phone=$1, email=$2, vk=$3, username=$4, updated_at=NOW()
            WHERE chat_id=$5
        ''', new_phone, new_email, new_vk, username, chat_id)
    else:
        await conn.execute('''
            INSERT INTO contacts (chat_id, username, phone, email, vk)
            VALUES ($1, $2, $3, $4, $5)
        ''', chat_id, username, phone, email, vk)
    await conn.close()

async def get_contact_by_chat_id(chat_id):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT phone, email, vk FROM contacts WHERE chat_id = $1", chat_id)
    await conn.close()
    return row

async def get_contact_by_username(username):
    conn = await get_connection()
    row = await conn.fetchrow("SELECT phone, email, vk FROM contacts WHERE username = $1", username)
    await conn.close()
    return row

async def get_all_contacts():
    conn = await get_connection()
    rows = await conn.fetch("SELECT username, phone, email, vk FROM contacts")
    await conn.close()
    return rows