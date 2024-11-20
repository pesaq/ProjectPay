import aiosqlite
import time
import random


from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from user_classes import *
from core.settings import get_settings

settings = get_settings('.env')

class Class9AState(StatesGroup):
    action = State()

class Class9BState(StatesGroup):
    action = State()

class DataBaseHelper:

    # Асинхронная функция для инициализации базы данных и создания таблиц
    async def initialize_database(self):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:

            # Создание таблицы для хранения информации
            await db.execute('''
                CREATE TABLE IF NOT EXISTS information (
                    info TEXT,
                    sender TEXT,
                    timestamp REAL,
                    class_name TEXT
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
                    class_name TEXT,
                    additional_info TEXT
                )
            ''')

            # Создание таблицы для хранения токенов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    token_type TEXT,
                    token_class TEXT,
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
                    class_name TEXT,
                    timestamp REAL NOT NULL
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS marks (
                    user_id INTEGER,
                    subject_name TEXT NOT NULL,
                    grades TEXT NOT NULL
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
    async def add_user(self, user_id, name, role, username, user_type, class_name):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, name, role, username, type, class_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, role, username, user_type, class_name))
            await db.commit()

    # Асинхронная функция для получения роли пользователя
    async def get_user_role(self, user_id):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None

    # Асинхронная функция для получения полного имени пользователя
    async def get_user_full_name(self, user_id):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            async with db.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None
    
    # Функция для определения класса пользователя
    async def get_user_class(self, user_id):
        if user_id == settings.bots.owner_chat_id:
            return OWNER
        role = await self.get_user_role(user_id)
        return role if role else None
    
    async def get_user_class_name(self, user_id):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            async with db.execute("SELECT class_name FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None

    # Функция для добавления нового пользователя в базу
    async def add_user(self, user_id, name, role, username, user_type="student", class_name=None):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            await db.execute('''
                INSERT INTO users (user_id, name, role, username, type, class_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, role, username, user_type, class_name))
            await db.commit()

    async def show_choose_class_menu(self, message: types.Message):
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(text='9А'),
                types.KeyboardButton(text='9Б'),
                types.KeyboardButton(text='Дневник'),
                types.KeyboardButton(text='Среднее арифметическое')
            ]
        ], resize_keyboard=True)
        await message.answer("Выберите класс для взаимодействия:", reply_markup=markup)

    async def show_9a_main_menu(self, message: types.Message, state: FSMContext):
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(text='Информация (9А)'),
                types.KeyboardButton(text='Домашние работы (9А)'),
                types.KeyboardButton(text='Оценки (9А)')
            ],
            [
                types.KeyboardButton(text='Назад')
            ]
        ], resize_keyboard=True)
        await message.answer("Главное меню:", reply_markup=markup)
        await state.set_state(Class9AState.action)
    
    async def show_9b_main_menu(self, message: types.Message, state: FSMContext):
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(text='Информация (9Б)'),
                types.KeyboardButton(text='Домашние работы (9Б)'),
                types.KeyboardButton(text='Оценки (9Б)')
            ],
            [
                types.KeyboardButton(text='Назад')
            ]
        ], resize_keyboard=True)
        await message.answer("Главное меню:", reply_markup=markup)
        await state.set_state(Class9BState.action)

    async def is_unique_name(self, name, user_id=None):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            query = "SELECT user_id FROM users WHERE name = ?"
            
            if user_id is not None:
                query += " AND user_id != ?"
                async with db.execute(query, (name, user_id)) as cursor:
                    result = await cursor.fetchone()
            else:
                async with db.execute(query, (name,)) as cursor:
                    result = await cursor.fetchone()
            
            return result is None

    async def generate_token(self, token_type, token_class):
        return f"{token_type}_{token_class}_{int(time.time())}_{random.randint(1000, 9999)}"

    def has_permission(self, user_class, required_class):
        if user_class == OWNER:
            return True
        if user_class == ADMIN and required_class in [USER, ADMIN]:
            return True
        if user_class == USER and required_class == USER:
            return True
        return False

    # Функция для удаления работы старше 8 дней
    async def delete_old_works(self):
        threshold = time.time() - 8 * 24 * 60 * 60
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            await db.execute("DELETE FROM works WHERE timestamp < ?", (threshold,))
            await db.commit()
    
    # Функция для удаления информации старше 8 дней
    async def delete_old_information(self):
        threshold = time.time() - 8 * 24 * 60 * 60
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            await db.execute("DELETE FROM information WHERE timestamp < ?", (threshold,))
            await db.commit()
    
    async def create_subjects_for_student(self, user_id):
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            # Проверка наличия записей по user_id
            async with db.execute('SELECT COUNT(*) FROM marks WHERE user_id = ?', (user_id,)) as cursor:
                count = await cursor.fetchone()

            # Если записи уже существуют, выходим
            if count[0] > 0:
                return

            # Если записей нет, выполняем вставку
            await db.execute('''INSERT INTO marks (subject_name, grades, user_id) VALUES 
            (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?),
            (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?), (?, ?, ?)''',
            (
                'Русский язык', '', user_id,
                'Английский язык', '', user_id,
                'Французский язык', '', user_id,
                'Химия', '', user_id,
                'Биология', '', user_id,
                'Физика', '', user_id,
                'История', '', user_id,
                'Обществознание', '', user_id,
                'Литература', '', user_id,
                'Алгебра', '', user_id,
                'Геометрия', '', user_id,
                'Теория вероятностей', '', user_id,
                'Музыка', '', user_id,
                'Информатика', '', user_id,
                'География', '', user_id,
                'Проект', '', user_id,
                'ОБЗР', '', user_id,
                'Физическая культура', '', user_id
            ))
            await db.commit()

db_helper = DataBaseHelper()