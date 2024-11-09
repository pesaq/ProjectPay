import random
import secrets
import time
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_polling
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand
import datetime
import sqlite3

# Создаем подключение к базе данных
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()

# Создаем таблицу для хранения информации
cursor.execute('''
    CREATE TABLE IF NOT EXISTS information (
        info TEXT,
        sender TEXT,
        timestamp REAL
    )
''')
conn.commit()

# Создаем таблицу для хранения пользователей
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        role TEXT,
        username TEXT,
        type TEXT,
        additional_info TEXT
    )
''')
conn.commit()



# Создаем таблицу для хранения токенов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tokens (
        token TEXT PRIMARY KEY,
        token_type TEXT,
        expires_at REAL,
        used BOOLEAN
    )
''')

# Создаем таблицу для хранения предметов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        subject_name TEXT PRIMARY KEY
    )
''')

# Создаем таблицу для хранения домашнего задания
cursor.execute('''
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

conn.commit()

# Создаем таблицу для хранения работ
cursor.execute('''
    CREATE TABLE IF NOT EXISTS works (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work TEXT NOT NULL,
        sender TEXT NOT NULL,
        timestamp REAL NOT NULL
    )
''')
conn.commit()


# Пример функции для добавления пользователя
def add_user(user_id, name, role):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, name, role) VALUES (?, ?, ?)", (user_id, name, role))
    conn.commit()

# Пример функции для получения роли пользователя
def get_user_role(user_id):
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Пример функции для получения имени пользователя
def get_user_full_name(user_id):
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Переменная для chat_id владельца (устанавливается при первом запуске)
OWNER_CHAT_ID = None

# Определение списка предметов и добавление в базу данных при старте
subjects = [
    'Русский язык', 'Английский язык', 'Французский язык', 'Химия', 'Биология', 'Физика',
    'История', 'Обществознание', 'Литература', 'Алгебра', 'Геометрия', 'Теория вероятностей',
    'Музыка', 'Информатика', 'География', 'Проект'
]

# Добавление предустановленных предметов в базу данных, если они отсутствуют
cursor.execute("SELECT COUNT(*) FROM subjects")
subject_count = cursor.fetchone()[0]
if subject_count == 0:
    for subject in subjects:
        cursor.execute("INSERT INTO subjects (subject_name) VALUES (?)", (subject,))
    conn.commit()


bot = Bot(token='6999739354:AAGCugWsLPrvrAH4brf778-xVmABDN7mcxQ')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Определение классов пользователей
USER = 'user'
ADMIN = 'admin'
OWNER = 'owner'

class AddUserState(StatesGroup):
    waiting_for_fio = State()
    waiting_for_subject_selection = State()
    waiting_for_homework_action = State()
    waiting_for_homework_entry = State()
    waiting_for_token_generation = State()
    waiting_for_user_deletion = State()
    waiting_for_info_entry = State()
    waiting_for_arithmetic_entry = State()
    waiting_for_work_entry = State()
# Функция для определения класса пользователя
def get_user_class(user_id):
    if user_id == OWNER_CHAT_ID:
        return OWNER
    return get_user_role(user_id) or USER

# Проверка доступа к командам
def has_permission(user_class, required_class):
    if user_class == OWNER:
        return True
    if user_class == ADMIN and required_class in [USER, ADMIN]:
        return True
    if user_class == USER and required_class == USER:
        return True
    return False

################################
class AddUserState(StatesGroup):
    waiting_for_fio = State()
    waiting_for_subject_selection = State()

# Функция проверки уникальности ФИО
def is_unique_name(name):
    cursor.execute("SELECT user_id FROM users WHERE name = ?", (name,))
    return cursor.fetchone() is None

# Функция добавления пользователя в базу данных
def add_user(user_id, name, role, username, user_type, additional_info):
    cursor.execute('''
        INSERT INTO users (user_id, name, role, username, type, additional_info)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, name, role, username, user_type, additional_info))
    conn.commit()

# Обработка отправки токена для доступа или повышения до администратора
@dp.message_handler(lambda message: message.text.startswith("/token "), state='*')
async def process_token(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Если команда начинается с /token, берем токен из сообщения
    token = message.text.split(" ")[1]

    try:
        # Проверяем наличие токена в базе данных токенов
        cursor.execute("SELECT token_type, expires_at, used FROM tokens WHERE token = ?", (token,))
        token_data = cursor.fetchone()

        if not token_data:
            await message.reply("Неверный или несуществующий токен.")
            return

        token_type, expires_at, used = token_data

        # Проверка на использование и истечение срока действия токена
        if used:
            await message.reply("Неверный или использованный токен.")
            return

        if time.time() > expires_at:
            await message.reply("Срок действия токена истек.")
            return

        # Новый пользователь отправил токен администратора, регистрируем его как администратора
        if token_type == 'admin':
            cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            user_role = cursor.fetchone()

            if not user_role:
                async with state.proxy() as data:
                    data['token'] = token
                    data['role'] = 'admin'
                await message.reply("Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество) для завершения регистрации как администратора.")
                await AddUserState.waiting_for_fio.set()
            else:
                cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", ('admin', user_id))
                conn.commit()
                await message.reply("Вы успешно повышены до администратора. Теперь у вас есть доступ к функциям администратора.")

        elif token_type == 'user':
            cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            user_role = cursor.fetchone()

            if not user_role:
                async with state.proxy() as data:
                    data['token'] = token
                    data['role'] = 'user'
                await message.reply("Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество).")
                await AddUserState.waiting_for_fio.set()
            else:
                await message.reply("Вы уже зарегистрированы и имеете доступ к боту.")

        # Помечаем токен как использованный
        cursor.execute("UPDATE tokens SET used = 1 WHERE token = ?", (token,))
        conn.commit()

    except Exception as e:
        await message.reply("Произошла ошибка при обработке токена. Пожалуйста, попробуйте снова.")
        print(f"Ошибка: {e}")

# Обработка состояния регистрации пользователя
@dp.message_handler(state=AddUserState.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with state.proxy() as data:
        role = data.get('role', 'user')
        token = data.get('token', None)

    # Проверка на уникальность ФИО
    if not is_unique_name(message.text):
        await message.reply("Пользователь с таким ФИО уже существует. Пожалуйста, введите уникальное ФИО.")
        return

    # Сохраняем данные пользователя
    add_user(user_id, message.text, role, message.from_user.username, 'student', None)

    if role == 'admin':
        await message.reply("Вы успешно зарегистрированы и повышены до администратора. Теперь у вас есть доступ к функциям администратора.")
    else:
        await message.reply("Вы успешно зарегистрированы как пользователь. Теперь у вас есть доступ к функциям пользователя.")

    await state.finish()

# Приветствие новых пользователей и установка владельца
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    global OWNER_CHAT_ID
    user_id = message.from_user.id

    # Устанавливаем владельца, если его еще нет в базе данных
    if OWNER_CHAT_ID is None:
        OWNER_CHAT_ID = 5233054529  # Ваш ID
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, name, role, username, type, additional_info)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (OWNER_CHAT_ID, message.from_user.full_name, 'owner', message.from_user.username, 'student', None))
        conn.commit()
        await message.answer(f"Добро пожаловать, {message.from_user.first_name}! Вы теперь владелец этого бота. Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество).")
        await AddUserState.waiting_for_fio.set()
    elif user_id == OWNER_CHAT_ID:
        await message.answer(f"Добро пожаловать обратно, владелец!")
    else:
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        user_role = cursor.fetchone()

        if not user_role:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, name, role, username, type, additional_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, message.from_user.full_name, 'unregistered', message.from_user.username, 'student', None))
            conn.commit()
            await message.answer(
                "Здравствуйте, похоже вы ещё не добавлены в базу данных этого бота. "
                "Попросите владельца или администратора добавить вас в бот.\n"
                "Если у вас есть токен доступа, отправьте его боту.")
        else:
            await message.answer(f"Добро пожаловать в SchoolBot, {message.from_user.full_name}.")
            await show_main_menu(message)

####################################


# Главное меню с кнопками школьного функционала
async def show_main_menu(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Дневник", "Среднее арифметическое", "Информация", "Домашние работы")
    await message.answer("Главное меню:", reply_markup=markup)


# Обработка кнопки "Дневник"
@dp.message_handler(lambda message: message.text == "Дневник")
async def handle_diary(message: types.Message):
    user_class = get_user_class(message.from_user.id)
    if user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Получаем список предметов из базы данных
    cursor.execute("SELECT subject_name FROM subjects")
    subjects = [row[0] for row in cursor.fetchall()]
    markup.add(*subjects, "Назад")
    await message.answer("Выберите предмет:", reply_markup=markup)
    await AddUserState.waiting_for_subject_selection.set()



@dp.message_handler(state=AddUserState.waiting_for_subject_selection)
async def process_subject_selection(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    subject = message.text

    if subject == "Назад":
        await state.finish()
        await show_main_menu(message)
        return

    # Проверяем, существует ли предмет в базе данных
    cursor.execute("SELECT subject_name FROM subjects WHERE subject_name = ?", (subject,))
    if not cursor.fetchone():
        await message.answer("Некорректный предмет. Пожалуйста, выберите предмет из списка.")
        return

    async with state.proxy() as data:
        data['subject'] = subject

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Записать д/з", "Узнать д/з", "Назад")
    await message.answer(f"Вы выбрали {subject}. Что вы хотите сделать?", reply_markup=markup)
    await AddUserState.waiting_for_homework_action.set()


@dp.message_handler(state=AddUserState.waiting_for_homework_action)
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
        await AddUserState.waiting_for_homework_entry.set()
    elif action == "Узнать д/з":
        # Получаем домашнее задание из базы данных
        cursor.execute("SELECT text, sender, username, timestamp FROM homework WHERE user_id = ? AND subject = ?", (user_id, subject))
        homework = cursor.fetchone()
        if homework:
            text, sender, username, timestamp = homework
            await message.answer(
                f"Домашнее задание по предмету {subject}: {text}\n"
                f"Отправлено: {sender} (Username: {username})\n"
                f"Дата: {datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y')}, Время: {datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M')}"
            )
        else:
            await message.answer(f"Домашнее задание по предмету {subject}: отсутствует.")


@dp.message_handler(state=AddUserState.waiting_for_homework_entry)
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
    cursor.execute(
        "INSERT OR REPLACE INTO homework (user_id, subject, text, sender, username, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, subject, homework_text, get_user_full_name(user_id), f"@{message.from_user.username}", timestamp)
    )
    conn.commit()

    await message.answer(f"Домашнее задание по предмету {subject} успешно записано.")
    await state.finish()
    await show_main_menu(message)




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
    await AddUserState.waiting_for_arithmetic_entry.set()

@dp.message_handler(lambda message: message.text == "Отмена", state=AddUserState.waiting_for_arithmetic_entry)
async def cancel_arithmetic(message: types.Message, state: FSMContext):
    await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(state=AddUserState.waiting_for_arithmetic_entry)
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

# Обработка кнопки "Информация"
@dp.message_handler(lambda message: message.text == "Информация")
async def handle_info(message: types.Message):
    user_class = get_user_class(message.from_user.id)
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
    user_class = get_user_class(message.from_user.id)
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления информации.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Отмена")
    await message.answer("Введите информацию для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await AddUserState.waiting_for_info_entry.set()

@dp.message_handler(state=AddUserState.waiting_for_info_entry)
async def process_info_entry(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Информация'
        user_class = get_user_class(message.from_user.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        if user_class in [ADMIN, OWNER]:
            markup.add("Добавить информацию", "Посмотреть информацию", "Назад")
        else:
            markup.add("Посмотреть информацию", "Назад")
        await message.answer("Возвращены в подменю 'Информация'.", reply_markup=markup)
        await state.finish()
        return

    user_id = message.from_user.id
    cursor.execute(
        "INSERT INTO information (info, sender, timestamp) VALUES (?, ?, ?)",
        (message.text, get_user_full_name(user_id), time.time())
    )
    conn.commit()
    await message.answer("Информация успешно добавлена.")
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(lambda message: message.text == "Посмотреть информацию")
async def view_info(message: types.Message):
    now = time.time()
    cursor.execute("SELECT info, sender, timestamp FROM information WHERE timestamp >= ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60,))
    recent_info = cursor.fetchall()

    if not recent_info:
        await message.answer("Нет доступной информации.")
    else:
        for info, sender, timestamp in recent_info:
            timestamp_dt = datetime.datetime.fromtimestamp(timestamp)
            await message.answer(f"{info}\n\nОтправлено: {sender}\nДата: {timestamp_dt.strftime('%d-%m-%Y')}, Время: {timestamp_dt.strftime('%H:%M')}")
    await message.answer("Возвращаюсь в главное меню.")
    await show_main_menu(message)

# Функция для удаления информации старше 8 дней
def delete_old_information():
    threshold = time.time() - 8 * 24 * 60 * 60
    cursor.execute("DELETE FROM information WHERE timestamp < ?", (threshold,))
    conn.commit()

# Обработка кнопки "Домашние работы"
@dp.message_handler(lambda message: message.text == "Домашние работы")
async def handle_works(message: types.Message):
    user_class = get_user_class(message.from_user.id)
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
    user_class = get_user_class(message.from_user.id)
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления работы.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Отмена")
    await message.answer("Введите работу для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await AddUserState.waiting_for_work_entry.set()

@dp.message_handler(state=AddUserState.waiting_for_work_entry)
async def process_work_entry(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Домашние работы'
        user_class = get_user_class(message.from_user.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        if user_class in [ADMIN, OWNER]:
            markup.add("Добавить работу", "Посмотреть все работы", "Назад")
        else:
            markup.add("Посмотреть все работы", "Назад")
        await message.answer("Возвращены в подменю 'Домашние работы'.", reply_markup=markup)
        await state.finish()
        return

    user_id = message.from_user.id
    try:
        cursor.execute(
            "INSERT INTO works (work, sender, timestamp) VALUES (?, ?, ?)",
            (message.text, get_user_full_name(user_id), time.time())
        )
        conn.commit()
        await message.answer("Работа успешно добавлена.")
    except Exception as e:
        await message.answer("Произошла ошибка при добавлении работы. Пожалуйста, попробуйте снова.")
        print(f"Ошибка: {e}")
    await state.finish()
    await show_main_menu(message)

@dp.message_handler(lambda message: message.text == "Посмотреть все работы")
async def view_works(message: types.Message):
    now = time.time()
    cursor.execute("SELECT work, sender, timestamp FROM works WHERE timestamp >= ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60,))
    recent_works = cursor.fetchall()

    if not recent_works:
        await message.answer("Нет доступных работ.")
    else:
        for work, sender, timestamp in recent_works:
            try:
                timestamp_dt = datetime.datetime.fromtimestamp(float(timestamp))
                await message.answer(f"{work}\n\nОтправлено: {sender}\nДата: {timestamp_dt.strftime('%d-%m-%Y')}, Время: {timestamp_dt.strftime('%H:%M')}")
            except Exception as e:
                await message.answer("Ошибка при обработке времени. Пожалуйста, попробуйте позже.")
                print(f"Ошибка: {e}")
    await message.answer("Возвращаюсь в главное меню.")
    await show_main_menu(message)

# Функция для удаления работы старше 8 дней
def delete_old_works():
    threshold = time.time() - 8 * 24 * 60 * 60
    cursor.execute("DELETE FROM works WHERE timestamp < ?", (threshold,))
    conn.commit()


##################################################################

# Обработка команды добавления нового пользователя
@dp.message_handler(commands=['addNewUser'])
async def add_new_user(message: types.Message):
    user_class = get_user_class(message.from_user.id)
    # Используем существующую проверку прав доступа
    if not has_permission(user_class, ADMIN):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Генерация токена для нового пользователя
    token = generate_token('user')
    cursor.execute("INSERT INTO tokens (token, token_type, expires_at, used) VALUES (?, ?, ?, ?)",
                   (token, 'user', time.time() + 3600, False))  # Сохраняем токен с временем действия 1 час
    conn.commit()
    await message.answer(f"Сгенерирован токен для нового пользователя: `<code>{token}</code>`. Он действителен 1 час.", parse_mode='HTML')

# Проверка доступа к командам
# Используем существующую проверку прав

def has_permission(user_class, required_class):
    if user_class == OWNER:
        return True
    if user_class == ADMIN and required_class == USER:
        return True
    if user_class == USER and required_class == USER:
        return True
    return False

# Генерация токена для повышения до администратора
@dp.message_handler(commands=['makeAdmin'])
async def make_admin(message: types.Message):
    user_class = get_user_class(message.from_user.id)
    if not has_permission(user_class, OWNER):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Генерация токена для повышения до администратора
    token = generate_token('admin')
    cursor.execute("INSERT INTO tokens (token, token_type, expires_at, used) VALUES (?, ?, ?, ?)",
                   (token, 'admin', time.time() + 3600, False))  # Сохраняем токен с временем действия 1 час
    conn.commit()
    await message.answer(f"Сгенерирован токен для повышения до администратора: `<code>{token}</code>`. Он действителен 1 час.", parse_mode='HTML')

# Генерация токена
# Обеспечивает разделение токенов для пользователей и администраторов, чтобы исключить конфликт

def generate_token(token_type):
    return f"{token_type}_{int(time.time())}_{random.randint(1000, 9999)}"




################################################################################################
# Состояния для удаления пользователей и администраторов
class DeleteUserState(StatesGroup):
    choosing_user = State()
    confirm_delete = State()

@dp.message_handler(commands=['deleteUser'], state='*')
async def delete_user_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not has_permission(user_class, ADMIN):
        await message.reply("У вас нет прав для удаления пользователей.")
        return

    # Администраторы могут удалять только пользователей, а не владельца или других администраторов.
    cursor.execute("SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND role != ?", (USER, OWNER))
    available_users = cursor.fetchall()

    if not available_users:
        await message.reply("Нет доступных пользователей для удаления.")
        return

    buttons = [types.InlineKeyboardButton(text=user[1], callback_data=f"delete_user_{user[0]}") for user in available_users]
    cancel_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")
    buttons.append(cancel_button)
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(*buttons)

    await DeleteUserState.choosing_user.set()
    await message.reply("Выберите пользователя для удаления:", reply_markup=keyboard)

@dp.message_handler(commands=['deleteAdmin'], state='*')
async def delete_admin_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not has_permission(user_class, OWNER):
        await message.reply("У вас нет прав для удаления администраторов.")
        return

    # Владелец может удалить всех администраторов, кроме себя.
    cursor.execute("SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND user_id != ? AND role != ?", (ADMIN, OWNER_CHAT_ID, OWNER))
    available_admins = cursor.fetchall()

    if not available_admins:
        await message.reply("Нет доступных администраторов для удаления.")
        return

    buttons = [types.InlineKeyboardButton(text=admin[1], callback_data=f"delete_admin_{admin[0]}") for admin in available_admins]
    cancel_button = types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")
    buttons.append(cancel_button)
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(*buttons)

    await DeleteUserState.choosing_user.set()
    await message.reply("Выберите администратора для удаления:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('delete_user_') or c.data.startswith('delete_admin_')), state=DeleteUserState.choosing_user)
async def process_delete_user(callback_query: types.CallbackQuery, state: FSMContext):
    user_id_to_delete = int(callback_query.data.split('_')[2])
    is_admin = callback_query.data.startswith('delete_admin_')

    await state.update_data(user_id_to_delete=user_id_to_delete, is_admin=is_admin)

    # Запрашиваем подтверждение на удаление
    keyboard = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(text="Подтвердить удаление", callback_data="confirm_delete"),
        types.InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")
    )
    cursor.execute("SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?", (user_id_to_delete,))
    user_data = cursor.fetchone()
    user_name, username = user_data if user_data else ("Unknown", "Unknown")
    await DeleteUserState.confirm_delete.set()
    await callback_query.message.edit_text(f"Вы уверены, что хотите удалить пользователя {user_name} (Username: @{username})?", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'confirm_delete', state=DeleteUserState.confirm_delete)
async def confirm_delete_user(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id_to_delete = data['user_id_to_delete']
    is_admin = data.get('is_admin', False)

    # Удаляем пользователя или администратора
    if is_admin:
        # Проверяем, что удаляемый пользователь не является владельцем
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id_to_delete,))
        if cursor.fetchone()[0] == OWNER:
            await callback_query.message.edit_text("Невозможно удалить владельца.")
            await state.finish()
            return

        # Если удаляем администратора, понижаем его до пользователя, но не удаляем полностью
        cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (USER, user_id_to_delete))
        conn.commit()
        cursor.execute("SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?", (user_id_to_delete,))
        user_data = cursor.fetchone()
        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        await callback_query.message.edit_text(f"Администратор {user_name} (Username: @{username}) был понижен до пользователя.")
    else:
        # Проверяем, что удаляемый пользователь не является владельцем
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id_to_delete,))
        if cursor.fetchone()[0] == OWNER:
            await callback_query.message.edit_text("Невозможно удалить владельца.")
            await state.finish()
            return

        # Понижение пользователя до незарегистрированного
        cursor.execute("SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?", (user_id_to_delete,))
        user_data = cursor.fetchone()
        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", ('unregistered', user_id_to_delete))
        conn.commit()
        await callback_query.message.edit_text(f"Пользователь {user_name} (Username: @{username}) был удален.")

    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'cancel_delete', state='*')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Удаление отменено.")
    await state.finish()

# Исправление функции проверки прав
# Проверка доступа к командам
def has_permission(user_class, required_class):
    if user_class == OWNER:
        return True
    if user_class == ADMIN and required_class in [USER, ADMIN]:
        return True
    if user_class == USER and required_class == USER:
        return True
    return False

#############################################################################################

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    user_class = get_user_class(message.from_user.id)

    if user_class == OWNER:
        await message.answer("Доступные команды для владельца:\n"
                             "/addNewUser - добавить пользователя\n"
                             "/makeAdmin - повысить пользователя до администратора\n"
                             "/deleteUser - удалить пользователя\n"
                             "/deleteAdmin - удалить администратора\n"
                             "/help - справка")
    elif user_class == ADMIN:
        await message.answer("Доступные команды для администратора:\n"
                             "/addNewUser - добавить пользователя\n"
                             "/deleteUser - удалить пользователя\n"
                             "/help - справка")
    else:
        await message.answer("Команда /help позволяет получить справочную информацию о доступных функциях.\n"
                             "/token 'ваш токен здесь' - для использования токена повышения прав.")

if __name__ == "__main__":
    from aiogram import executor
    from schoolbot import dp # предполагаем, что dp уже настроен

    executor.start_polling(dp, skip_updates=True, on_startup=set_bot_commands)