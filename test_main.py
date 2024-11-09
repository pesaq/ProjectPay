import random
import secrets
import time
import datetime
import aiosqlite

from aiogram import executor
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

BOT_TOKEN = "6999739354:AAGCugWsLPrvrAH4brf778-xVmABDN7mcxQ"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Определение классов пользователей
USER = 'user'
ADMIN = 'admin'
OWNER = 'owner'

# Определение списка предметов
subjects = [
    'Русский язык', 'Английский язык', 'Французский язык', 'Химия', 'Биология', 'Физика',
    'История', 'Обществознание', 'Литература', 'Алгебра', 'Геометрия', 'Теория вероятностей',
    'Музыка', 'Информатика', 'География', 'Проект'
]

# Асинхронная функция для инициализации базы данных и создания таблиц
async def initialize_database():
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
async def add_user(user_id, name, role, username, user_type, additional_info):
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''
            INSERT OR REPLACE INTO users (user_id, name, role, username, type, additional_info)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name, role, username, user_type, additional_info))
        await db.commit()

# Асинхронная функция для получения роли пользователя
async def get_user_role(user_id):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

# Асинхронная функция для получения полного имени пользователя
async def get_user_full_name(user_id):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
 

# Функция для определения класса пользователя
async def get_user_class(user_id):
    if user_id == OWNER_CHAT_ID:
        return OWNER
    role = await get_user_role(user_id)
    return role if role else USER

# Проверка доступа к командам
def has_permission(user_class, required_class):
    if user_class == OWNER:
        return True
    if user_class == ADMIN and required_class in [USER, ADMIN]:
        return True
    if user_class == USER and required_class == USER:
        return True
    return False


# Пример функции для добавления пользователя
# (Убедись, что все параметры передаются правильно)
# async def add_user(user_id, name, role, username, user_type, additional_info):
#     ...

# Пример использования функций в обработчиках
# Не забудь, что обработчики должны быть асинхронными и использовать `await` для вызовов функций

# Например:
# @dp.message_handler(commands=['start'])
# async def send_welcome(message: types.Message):
#     user_id = message.from_user.id
#     await add_user(user_id, "Имя Фамилия", USER, message.from_user.username, "student", None)
#     await message.reply("Добро пожаловать!")

# Остальная часть твоего кода...

# Определение функции set_bot_commands
async def set_bot_commands(dp):
    commands = [
        types.BotCommand("start", "Начать работу с ботом"),
        types.BotCommand("help", "Получить помощь"),
        # Добавьте другие команды, если нужно
    ]
    await dp.bot.set_my_commands(commands)

################################
# Уникальный ID для владельца
OWNER_CHAT_ID = 5233054529
OWNER = 'owner'

# Состояния для добавления пользователя
class AddUserState(StatesGroup):
    waiting_for_fio = State()

# Функция для добавления нового пользователя в базу
async def add_user(user_id, name, role, username, user_type="student", additional_info=None):
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute('''
            INSERT INTO users (user_id, name, role, username, type, additional_info)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name, role, username, user_type, additional_info))
        await db.commit()

# Обработка команды /start и регистрация владельца при первом запуске
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with aiosqlite.connect('bot_data.db') as db:
        # Проверка для владельца
        if user_id == OWNER_CHAT_ID:
            # Проверяем, зарегистрирован ли владелец в базе данных
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                role = await cursor.fetchone()

            # Если владелец еще не зарегистрирован, добавляем его
            if not role:
                await add_user(
                    user_id=user_id,
                    name=None,  # Имя будет запрошено отдельно
                    role=OWNER,  # Назначаем роль владельца
                    username=message.from_user.username or None
                )
                await message.reply("Добро пожаловать, владелец! Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество), чтобы завершить регистрацию.")
                await AddUserState.waiting_for_fio.set()
            elif role[0] != OWNER:
                # Если роль владельца указана некорректно, обновляем ее
                await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (OWNER, user_id))
                await db.commit()
                await message.reply("Ваша роль была обновлена до владельца. Добро пожаловать!")
                await show_main_menu(message)
            else:
                await message.reply("Добро пожаловать обратно, владелец!")
                await show_main_menu(message)
        else:
            # Проверка для других пользователей
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                role = await cursor.fetchone()

            # Если пользователь еще не зарегистрирован
            if role is None:
                await add_user(
                    user_id=user_id,
                    name=None,
                    role="unregistered",
                    username=message.from_user.username or None
                )
                await message.reply(
                    "Здравствуйте! Для доступа к боту, пожалуйста, введите токен. "
                    "Если у вас его нет, обратитесь к владельцу или администратору."
                )
            else:
                await message.reply(f"Добро пожаловать, {message.from_user.full_name}.")
                await show_main_menu(message)


# Проверка уникальности ФИО
async def is_unique_name(name):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT user_id FROM users WHERE name = ?", (name,)) as cursor:
            result = await cursor.fetchone()
            return result is None

# Обработка токена для регистрации или назначения роли
@dp.message_handler(lambda message: message.text.startswith("/token "), state='*')
async def process_token(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    token = message.text.split(" ")[1]  # Получаем токен из команды

    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT token_type, expires_at, used FROM tokens WHERE token = ?", (token,)) as cursor:
            token_data = await cursor.fetchone()

        if not token_data:
            await message.reply("Неверный или несуществующий токен.")
            return

        token_type, expires_at, used = token_data

        if used:
            await message.reply("Этот токен уже был использован.")
            return

        if time.time() > expires_at:
            await message.reply("Срок действия токена истек.")
            return

        # Назначаем роль на основе типа токена
        role = "admin" if token_type == "admin" else "user"

        # Сохраняем токен и роль в состоянии
        async with state.proxy() as data:
            data['token'] = token
            data['role'] = role
        await message.reply(f"Введите ваше ФИО (Фамилия Имя Отчество), чтобы завершить регистрацию как {role}.")
        await AddUserState.waiting_for_fio.set()

        # Помечаем токен как использованный
        await db.execute("UPDATE tokens SET used = 1 WHERE token = ?", (token,))
        await db.commit()

# Завершение регистрации после ввода ФИО
@dp.message_handler(AddUserState.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    fio = message.text

    # Проверка уникальности имени
    if not await is_unique_name(fio):
        await message.reply("Пользователь с таким ФИО уже существует. Пожалуйста, введите уникальное ФИО.")
        return

    async with aiosqlite.connect('bot_data.db') as db:
        async with state.proxy() as data:
            role = data.get('role', 'user')

        # Завершаем регистрацию для владельца или других пользователей
        await db.execute("UPDATE users SET name = ?, role = ?, type = ? WHERE user_id = ?", (fio, role, "student", user_id))
        await db.commit()

    await message.reply("Регистрация завершена. Добро пожаловать!")
    await state.finish()

####################################

# Главное меню с кнопками школьного функционала
async def show_main_menu(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Дневник", "Среднее арифметическое", "Информация", "Домашние работы")
    await message.answer("Главное меню:", reply_markup=markup)

# Состояния для работы с домашними заданиями
class HomeworkState(StatesGroup):
    waiting_for_subject_selection = State()
    waiting_for_homework_action = State()
    waiting_for_homework_entry = State()

  
# Обработка кнопки "Дневник"
@dp.message_handler(lambda message: message.text == "Дневник")
async def handle_diary(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Получаем список предметов из базы данных
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT subject_name FROM subjects") as cursor:
            rows = await cursor.fetchall()
    subjects = [row[0] for row in rows]
    markup.add(*subjects, "Назад")
    await message.answer("Выберите предмет:", reply_markup=markup)
    await HomeworkState.waiting_for_subject_selection.set()



@dp.message_handler(state=HomeworkState.waiting_for_subject_selection)
async def process_subject_selection(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    subject = message.text

    if subject == "Назад":
        await state.finish()
        await show_main_menu(message)
        return

    # Проверяем, существует ли предмет в базе данных
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT subject_name FROM subjects WHERE subject_name = ?", (subject,)) as cursor:
            result = await cursor.fetchone()
    if not result:
        await message.answer("Некорректный предмет. Пожалуйста, выберите предмет из списка.")
        return

    async with state.proxy() as data:
        data['subject'] = subject

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Записать д/з", "Узнать д/з", "Назад")
    await message.answer(f"Вы выбрали {subject}. Что вы хотите сделать?", reply_markup=markup)
    await HomeworkState.waiting_for_homework_action.set()


@dp.message_handler(state=HomeworkState.waiting_for_homework_action)
async def process_homework_action(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    action = message.text

    if action == "Назад":
        await state.finish()
        await handle_diary(message)
        return

    async with state.proxy() as data:
        if 'subject' not in data:
            await message.answer("Произошла ошибка. Пожалуйста, начните с выбора предмета снова.")
            await state.finish()
            await handle_diary(message)
            return
        subject = data['subject']

    if action == "Записать д/з":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Отмена")
        await message.answer(f"Введите домашнее задание по предмету {subject}.", reply_markup=markup)
        await HomeworkState.waiting_for_homework_entry.set()
    elif action == "Узнать д/з":
        # Получаем домашнее задание из базы данных
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT text, sender, username, timestamp FROM homework WHERE user_id = ? AND subject = ?", (user_id, subject)) as cursor:
                homework = await cursor.fetchone()
        if homework:
            text, sender, username, timestamp = homework
            await message.answer(
                f"Домашнее задание по предмету {subject}: {text}\n"
                f"Отправлено: {sender} (Username: {username})\n"
                f"Дата: {datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y')}, Время: {datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M')}"
            )
        else:
            await message.answer(f"Домашнее задание по предмету {subject}: отсутствует.")


@dp.message_handler(state=HomeworkState.waiting_for_homework_entry)
async def process_homework_entry(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    homework_text = message.text

    if homework_text.lower() == "отмена":
        await state.finish()
        await show_main_menu(message)
        return

    async with state.proxy() as data:
        if 'subject' not in data:
            await message.answer("Произошла ошибка. Пожалуйста, начните с выбора предмета снова.")
            await state.finish()
            await handle_diary(message)
            return
        subject = data['subject']

    # Сохраняем домашнее задание в базе данных
    timestamp = time.time()
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute(
            "INSERT OR REPLACE INTO homework (user_id, subject, text, sender, username, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, subject, homework_text, await get_user_full_name(user_id), f"@{message.from_user.username}", timestamp)
        )
        await db.commit()

    await message.answer(f"Домашнее задание по предмету {subject} успешно записано.")
    await state.finish()
    await show_main_menu(message)

# Состояния для работы с арифметическими задачами
class ArithmeticState(StatesGroup):
    waiting_for_arithmetic_entry = State()
    
# Обработка кнопки "Среднее арифметическое"
@dp.message_handler(lambda message: message.text == "Среднее арифметическое")
async def handle_arithmetic(message: types.Message):
    user_class = get_user_class(message.from_user.id)
    if user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    buttons = [
        types.KeyboardButton(text="Отмена")
    ]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons)
    await message.answer("Введите длинное число из цифр без пробелов для расчета среднего арифметического:", reply_markup=keyboard)
    await ArithmeticState.waiting_for_arithmetic_entry.set()

@dp.message_handler(lambda message: message.text == "Отмена", state=ArithmeticState.waiting_for_arithmetic_entry)
async def cancel_arithmetic(message: types.Message, state: FSMContext):
    await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(state=ArithmeticState.waiting_for_arithmetic_entry)
async def process_arithmetic(message: types.Message, state: FSMContext):
    try:
        digits = [int(d) for d in message.text if d.isdigit()]
        if not digits:
            raise ValueError("Ваш запрос должен содержать только цифры.")
        average = sum(digits) / len(digits)
        await message.answer(f"Среднее арифметическое цифр равно: {average}", reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        await message.answer("Пожалуйста, введите только слитное число. Это число автоматически разделится на цифры, из которых будет получено среднее арифметическое.")
    await state.finish()
    await show_main_menu(message)

class InfoState(StatesGroup):
    waiting_for_info_entry = State()
    
# Обработка кнопки "Информация"
@dp.message_handler(lambda message: message.text == "Информация")
async def handle_info(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    if user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_class in [ADMIN, OWNER]:
        markup.add("Добавить информацию", "Посмотреть информацию", "Назад")
    else:
        markup.add("Посмотреть информацию", "Назад")
    await message.answer("Выберите действие с информацией:", reply_markup=markup)

@dp.message_handler(lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(lambda message: message.text == "Добавить информацию")
async def add_info(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления информации.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Отмена")
    await message.answer("Введите информацию для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await InfoState.waiting_for_info_entry.set()

@dp.message_handler(state=InfoState.waiting_for_info_entry)
async def process_info_entry(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Информация'
        user_class = await get_user_class(message.from_user.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        if user_class in [ADMIN, OWNER]:
            markup.add("Добавить информацию", "Посмотреть информацию", "Назад")
        else:
            markup.add("Посмотреть информацию", "Назад")
        await message.answer("Возвращены в подменю 'Информация'.", reply_markup=markup)
        await state.finish()
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute(
            "INSERT INTO information (info, sender, timestamp) VALUES (?, ?, ?)",
            (message.text, await get_user_full_name(user_id), time.time())
        )
        await db.commit()
    await message.answer("Информация успешно добавлена.")
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(lambda message: message.text == "Посмотреть информацию")
async def view_info(message: types.Message):
    now = time.time()
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT info, sender, timestamp FROM information WHERE timestamp >= ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60,)) as cursor:
            recent_info = await cursor.fetchall()

    if not recent_info:
        await message.answer("Нет доступной информации.")
    else:
        for info, sender, timestamp in recent_info:
            timestamp_dt = datetime.datetime.fromtimestamp(timestamp)
            await message.answer(
                f"{info}\n\nОтправлено: {sender}\nДата: {timestamp_dt.strftime('%d-%m-%Y')}, Время: {timestamp_dt.strftime('%H:%M')}"
            )
    await message.answer("Возвращаюсь в главное меню.")
    await show_main_menu(message)

# Функция для удаления информации старше 8 дней
async def delete_old_information():
    threshold = time.time() - 8 * 24 * 60 * 60
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute("DELETE FROM information WHERE timestamp < ?", (threshold,))
        await db.commit()

class WorkState(StatesGroup):
    waiting_for_work_entry = State()
    
# Обработка кнопки "Домашние работы"
@dp.message_handler(lambda message: message.text == "Домашние работы")
async def handle_works(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    if user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_class in [ADMIN, OWNER]:
        markup.add("Добавить работу", "Посмотреть все работы", "Назад")
    else:
        markup.add("Посмотреть все работы", "Назад")
    await message.answer("Выберите действие с работами:", reply_markup=markup)

@dp.message_handler(lambda message: message.text == "Добавить работу")
async def add_work(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления работы.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Отмена")
    await message.answer("Введите работу для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await WorkState.waiting_for_work_entry.set()

@dp.message_handler(state=WorkState.waiting_for_work_entry)
async def process_work_entry(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Домашние работы'
        user_class = await get_user_class(message.from_user.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        if user_class in [ADMIN, OWNER]:
            markup.add("Добавить работу", "Посмотреть все работы", "Назад")
        else:
            markup.add("Посмотреть все работы", "Назад")
        await message.answer("Возвращены в подменю 'Домашние работы'.", reply_markup=markup)
        await state.finish()
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        try:
            await db.execute(
                "INSERT INTO works (work, sender, timestamp) VALUES (?, ?, ?)",
                (message.text, await get_user_full_name(user_id), time.time())
            )
            await db.commit()
            await message.answer("Работа успешно добавлена.")
        except aiosqlite.Error as e:
            await message.answer("Произошла ошибка при добавлении работы. Пожалуйста, попробуйте снова.")
            print(f"Ошибка базы данных: {e}")
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(lambda message: message.text == "Посмотреть все работы")
async def view_works(message: types.Message):
    now = time.time()
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT work, sender, timestamp FROM works WHERE timestamp >= ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60,)) as cursor:
            recent_works = await cursor.fetchall()

    if not recent_works:
        await message.answer("Нет доступных работ.")
    else:
        for work, sender, timestamp in recent_works:
            try:
                timestamp_dt = datetime.datetime.fromtimestamp(float(timestamp))
                await message.answer(
                    f"{work}\n\nОтправлено: {sender}\nДата: {timestamp_dt.strftime('%d-%m-%Y')}, Время: {timestamp_dt.strftime('%H:%M')}"
                )
            except Exception as e:
                await message.answer("Ошибка при обработке времени. Пожалуйста, попробуйте позже.")
                print(f"Ошибка: {e}")
    await message.answer("Возвращаюсь в главное меню.")
    await show_main_menu(message)

# Функция для удаления работы старше 8 дней
async def delete_old_works():
    threshold = time.time() - 8 * 24 * 60 * 60
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute("DELETE FROM works WHERE timestamp < ?", (threshold,))
        await db.commit()
##################################################################

# Генерация токена
def generate_token(token_type):
    return f"{token_type}_{int(time.time())}_{random.randint(1000, 9999)}"

# Проверка доступа к командам
def has_permission(user_class, required_class):
    if user_class == OWNER:
        return True
    if user_class == ADMIN and required_class in [USER, ADMIN]:
        return True
    if user_class == USER and required_class == USER:
        return True
    return False

# Асинхронная функция получения класса пользователя
async def get_user_class(user_id):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return result[0]
            return 'unregistered'

# Асинхронная функция получения полного имени пользователя
async def get_user_full_name(user_id):
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else "Unknown"

# Обработка команды добавления нового пользователя
@dp.message_handler(commands=['addNewUser'])
async def add_new_user(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    # Используем существующую проверку прав доступа
    if not has_permission(user_class, ADMIN) or not has_permission(user_class, OWNER):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Генерация токена для нового пользователя
    token = generate_token('user')
    try:
        async with aiosqlite.connect('bot_data.db') as db:
            await db.execute(
                "INSERT INTO tokens (token, token_type, expires_at, used) VALUES (?, ?, ?, ?)",
                (token, 'user', time.time() + 3600, False)  # Токен действителен 1 час
            )
            await db.commit()
        await message.answer(
            f"Сгенерирован токен для нового пользователя: `<code>{token}</code>`. Он действителен 1 час.",
            parse_mode='HTML'
        )
    except aiosqlite.Error as e:
        await message.answer("Произошла ошибка при генерации токена. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при добавлении токена: {e}")

# Генерация токена для повышения до администратора
@dp.message_handler(commands=['makeAdmin'])
async def make_admin(message: types.Message):
    user_class = await get_user_class(message.from_user.id)
    if not has_permission(user_class, OWNER):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Генерация токена для повышения до администратора
    token = generate_token('admin')
    try:
        async with aiosqlite.connect('bot_data.db') as db:
            await db.execute(
                "INSERT INTO tokens (token, token_type, expires_at, used) VALUES (?, ?, ?, ?)",
                (token, 'admin', time.time() + 3600, False)  # Токен действителен 1 час
            )
            await db.commit()
        await message.answer(
            f"Сгенерирован токен для повышения до администратора: `<code>{token}</code>`. Он действителен 1 час.",
            parse_mode='HTML'
        )
    except aiosqlite.Error as e:
        await message.answer("Произошла ошибка при генерации токена. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при добавлении токена: {e}")
################################################################################################

# Состояния для удаления пользователей и администраторов
class DeleteUserState(StatesGroup):
    choosing_user = State()
    confirm_delete = State()

# Функция проверки доступа к командам
def has_permission(user_class, required_class):
    if user_class == OWNER:
        return True
    if user_class == ADMIN and required_class in [USER, ADMIN]:
        return True
    if user_class == USER and required_class == USER:
        return True
    return False

# Асинхронная функция получения класса пользователя
async def get_user_class(user_id):
    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return result[0]
                return 'unregistered'
    except aiosqlite.Error as e:
        print(f"Ошибка базы данных при получении класса пользователя: {e}")
        return 'unregistered'

# Асинхронная функция получения полного имени пользователя
async def get_user_full_name(user_id):
    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else "Unknown"
    except aiosqlite.Error as e:
        print(f"Ошибка базы данных при получении полного имени пользователя: {e}")
        return "Unknown"

# Обработка команды удаления пользователя
@dp.message_handler(commands=['deleteUser'], state='*')
async def delete_user_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not has_permission(user_class, ADMIN):
        await message.reply("У вас нет прав для удаления пользователей.")
        return

    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND role != ?",
                (USER, OWNER)
            ) as cursor:
                available_users = await cursor.fetchall()

        if not available_users:
            await message.reply("Нет доступных пользователей для удаления.")
            return

        buttons = [
            types.InlineKeyboardButton(text=user[1], callback_data=f"delete_user_{user[0]}")
            for user in available_users
        ]
        cancel_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")
        buttons.append(cancel_button)
        keyboard = types.InlineKeyboardMarkup(row_width=1).add(*buttons)

        await DeleteUserState.choosing_user.set()
        await message.reply("Выберите пользователя для удаления:", reply_markup=keyboard)

    except aiosqlite.Error as e:
        await message.reply("Произошла ошибка при получении списка пользователей. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при получении пользователей для удаления: {e}")

# Обработка команды удаления администратора
@dp.message_handler(commands=['deleteAdmin'], state='*')
async def delete_admin_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not has_permission(user_class, OWNER):
        await message.reply("У вас нет прав для удаления администраторов.")
        return

    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND user_id != ? AND role != ?",
                (ADMIN, OWNER_CHAT_ID, OWNER)
            ) as cursor:
                available_admins = await cursor.fetchall()

        if not available_admins:
            await message.reply("Нет доступных администраторов для удаления.")
            return

        buttons = [
            types.InlineKeyboardButton(text=admin[1], callback_data=f"delete_admin_{admin[0]}")
            for admin in available_admins
        ]
        cancel_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")
        buttons.append(cancel_button)
        keyboard = types.InlineKeyboardMarkup(row_width=1).add(*buttons)

        await DeleteUserState.choosing_user.set()
        await message.reply("Выберите администратора для удаления:", reply_markup=keyboard)

    except aiosqlite.Error as e:
        await message.reply("Произошла ошибка при получении списка администраторов. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при получении администраторов для удаления: {e}")

# Обработка выбора пользователя или администратора для удаления
@dp.callback_query_handler(
    lambda c: c.data and (c.data.startswith('delete_user_') or c.data.startswith('delete_admin_')),
    DeleteUserState.choosing_user
)
async def process_delete_user(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id_to_delete = int(callback_query.data.split('_')[2])
        is_admin = callback_query.data.startswith('delete_admin_')

        await state.update_data(user_id_to_delete=user_id_to_delete, is_admin=is_admin)

        # Запрашиваем подтверждение на удаление
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(text="Подтвердить удаление", callback_data="confirm_delete"),
            types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")
        )

        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                (user_id_to_delete,)
            ) as cursor:
                user_data = await cursor.fetchone()

        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        await DeleteUserState.confirm_delete.set()
        await callback_query.message.edit_text(
            f"Вы уверены, что хотите удалить пользователя {user_name} (Username: @{username})?",
            reply_markup=keyboard
        )
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при обработке выбора пользователя для удаления: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при обработке выбора пользователя для удаления: {e}")

# Подтверждение удаления пользователя или администратора
@dp.callback_query_handler(lambda c: c.data == 'confirm_delete', state=DeleteUserState.confirm_delete)
async def confirm_delete_user(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        user_id_to_delete = data['user_id_to_delete']
        is_admin = data.get('is_admin', False)

        async with aiosqlite.connect('bot_data.db') as db:
            # Получаем роль пользователя перед удалением
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id_to_delete,)) as cursor:
                role_result = await cursor.fetchone()
            if not role_result:
                await callback_query.message.edit_text("Пользователь не найден.")
                await state.finish()
                return
            role = role_result[0]

            if role == OWNER:
                await callback_query.message.edit_text("Невозможно удалить владельца.")
                await state.finish()
                return

            if is_admin:
                # Понижаем администратора до пользователя
                await db.execute(
                    "UPDATE users SET role = ? WHERE user_id = ?",
                    (USER, user_id_to_delete)
                )
                await db.commit()

                # Получаем имя и username для уведомления
                async with db.execute(
                    "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                    (user_id_to_delete,)
                ) as cursor:
                    user_data = await cursor.fetchone()

                user_name, username = user_data if user_data else ("Unknown", "Unknown")
                await callback_query.message.edit_text(
                    f"Администратор {user_name} (Username: @{username}) был понижен до пользователя."
                )
            else:
                # Понижаем пользователя до незарегистрированного
                await db.execute(
                    "UPDATE users SET role = ? WHERE user_id = ?",
                    ('unregistered', user_id_to_delete)
                )
                await db.commit()

                # Получаем имя и username для уведомления
                async with db.execute(
                    "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                    (user_id_to_delete,)
                ) as cursor:
                    user_data = await cursor.fetchone()

                user_name, username = user_data if user_data else ("Unknown", "Unknown")
                await callback_query.message.edit_text(
                    f"Пользователь {user_name} (Username: @{username}) был удален."
                )

        await state.finish()
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при удалении пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при подтверждении удаления пользователя: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при подтверждении удаления пользователя: {e}")

# Обработка отмены удаления
@dp.callback_query_handler(lambda c: c.data == 'cancel_delete', state='*')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Удаление отменено.")
        await state.finish()
    except Exception as e:
        print(f"Необработанное исключение при отмене удаления: {e}")
#############################################################################################

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    user_class = await get_user_class(message.from_user.id)

    if user_class == 'owner':  # Проверка для владельца
        await message.answer("Доступные команды для владельца:\n"
                             "/addNewUser - добавить пользователя\n"
                             "/makeAdmin - повысить пользователя до администратора\n"
                             "/deleteUser - удалить пользователя\n"
                             "/deleteAdmin - удалить администратора\n"
                             "/help - справка")
    elif user_class == 'admin':  # Проверка для администратора
        await message.answer("Доступные команды для администратора:\n"
                             "/addNewUser - добавить пользователя\n"
                             "/deleteUser - удалить пользователя\n"
                             "/help - справка")
    else:
        await message.answer("Команда /help позволяет получить справочную информацию о доступных функциях.\n"
                             "/token 'ваш токен здесь' - для использования токена повышения прав.")

# Функция для очистки всех таблиц
async def clear_all_tables():
    async with aiosqlite.connect('bot_data.db') as db:
        tables = ["users", "tokens", "information", "subjects", "homework", "works"]
        
        for table in tables:
            await db.execute(f"DELETE FROM {table}")
        await db.commit()
    
    print("Все таблицы очищены.")

# Обработчик команды /clear_all для владельца
@dp.message_handler(commands=['clear_all'])
async def handle_clear_all(message: types.Message):
    user_id = message.from_user.id

    # Проверка прав: только владелец может выполнять команду
    if user_id != 5233054529:
        await message.reply("У вас нет прав для выполнения этой команды.")
        return
    
    # Очистка таблиц
    await clear_all_tables()
    await message.reply("Все таблицы успешно очищены.")


if __name__ == "__main__":
    async def on_startup(router):
        await initialize_database()  # если у вас есть эта функция
        await set_bot_commands(dp)   # если у вас есть функция для установки команд

    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)