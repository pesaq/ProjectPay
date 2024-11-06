import aiosqlite
import time
import random


from aiogram import types, filters

from user_classes import *
from core.settings import get_settings

settings = get_settings('.env')

class DataBaseHelper:

    # Асинхронная функция для инициализации базы данных и создания таблиц
    async def initialize_database(self):
        async with aiosqlite.connect('bot_data.db') as db:

            # Создание таблицы для хранения информации
            await db.execute('''
                CREATE TABLE IF NOT EXISTS information (
                    info TEXT,
                    sender TEXT,
                    timestamp REAL
                )
            ''')

            # Создание таблицы для хранения пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    role TEXT,
                    username TEXT,
                    type TEXT DEFAULT 'student',
                    additional_info TEXT
                )
            ''')

            # Создание таблицы для хранения токенов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    token_type TEXT,
                    expires_at REAL,
                    used BOOLEAN
                )
            ''')

            # Создание таблицы для хранения предметов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS subjects (
                    subject_name TEXT PRIMARY KEY
                )
            ''')

            # Создание таблицы для хранения домашнего задания
            await db.execute('''
                CREATE TABLE IF NOT EXISTS homework (
                    user_id INTEGER,
                    subject TEXT,
                    text TEXT,
                    sender TEXT,
                    username TEXT,
                    timestamp REAL,
                    PRIMARY KEY (user_id, subject)
                )
            ''')

            # Создание таблицы для хранения работ
            await db.execute('''
                CREATE TABLE IF NOT EXISTS works (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            ''')

            # Добавление предустановленных предметов, если таблица subjects пуста
            async with db.execute("SELECT COUNT(*) FROM subjects") as cursor:
                subject_count = await cursor.fetchone()
                if subject_count[0] == 0:
                    await db.executemany("INSERT INTO subjects (subject_name) VALUES (?)", [(subject,) for subject in subjects])

            await db.commit()
        print("База данных инициализирована, таблицы созданы и предустановленные предметы добавлены.")

    # Асинхронная функция для добавления пользователя в базу данных
    async def add_user(self, user_id, name, role, username, user_type, additional_info):
        async with aiosqlite.connect('bot_data.db') as db:
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, name, role, username, type, additional_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, role, username, user_type, additional_info))
            await db.commit()

    # Асинхронная функция для получения роли пользователя
    async def get_user_role(self, user_id):
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None

    # Асинхронная функция для получения полного имени пользователя
    async def get_user_full_name(self, user_id):
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None
    
    # Функция для определения класса пользователя
    async def get_user_class(self, user_id):
        if user_id == settings.bots.owner_chat_id:
            return OWNER
        role = await self.get_user_role(user_id)
        return role if role else USER

    # Функция для добавления нового пользователя в базу
    async def add_user(self, user_id, name, role, username, user_type="student", additional_info=None):
        async with aiosqlite.connect('bot_data.db') as db:
            await db.execute('''
                INSERT INTO users (user_id, name, role, username, type, additional_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, role, username, user_type, additional_info))
            await db.commit()

    # Главное меню с кнопками школьного функционала
    async def show_main_menu(self, message: types.Message):
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Дневник'
                ),
                types.KeyboardButton(
                    text='Среднее арифметическое'
                ),
                types.KeyboardButton(
                    text='Информация'
                ),
                types.KeyboardButton(
                    text='Домашние работы'
                )
            ]
        ], resize_keyboard=True)
        await message.answer("Главное меню:", reply_markup=markup)

    async def is_unique_name(self, name):
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT user_id FROM users WHERE name = ?", (name,)) as cursor:
                result = await cursor.fetchone()
                return result is None

    async def generate_token(self, token_type):
        return f"{token_type}_{int(time.time())}_{random.randint(1000, 9999)}"

    def has_permission(self, user_class, required_class):
        if user_class == OWNER:
            return True
        if user_class == ADMIN and required_class in [USER, ADMIN]:
            return True
        if user_class == USER and required_class == USER:
            return True
        return False



db_helper = DataBaseHelper()