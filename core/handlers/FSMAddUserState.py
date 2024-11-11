from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from core.settings import get_settings

from database.db_helper import db_helper
from user_classes import *

import aiosqlite
import time

router = Router()
settings = get_settings('.env')

# Обработка команды добавления нового пользователя
@router.message(Command(commands=['addNewUser']))
async def add_new_user(message: types.Message):
    user_class = await db_helper.get_user_class(message.from_user.id)
    # Используем существующую проверку прав доступа
    if not db_helper.has_permission(user_class, ADMIN) and not db_helper.has_permission(user_class, OWNER):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Генерация токена для нового пользователя
    token = await db_helper.generate_token('user')
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
@router.message(Command(commands=['makeAdmin']))
async def make_admin(message: types.Message):
    user_class = await db_helper.get_user_class(message.from_user.id)
    if not db_helper.has_permission(user_class, OWNER):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # Генерация токена для повышения до администратора
    token = await db_helper.generate_token('admin')
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

class AddUserState(StatesGroup):
    waiting_for_fio = State()



# Обработка команды /reg и регистрация владельца при первом запуске
@router.message(Command(commands=['registration']))
async def send_welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with aiosqlite.connect('bot_data.db') as db:
        # Проверка для владельца
        if user_id == settings.bots.owner_chat_id:
            # Проверяем, зарегистрирован ли владелец в базе данных
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                role = await cursor.fetchone()

            # Если владелец еще не зарегистрирован, добавляем его
            if not role:
                await db_helper.add_user(
                    user_id=user_id,
                    name=None,  # Имя будет запрошено отдельно
                    role=OWNER,  # Назначаем роль владельца
                    username=message.from_user.username or None
                )
                await db_helper.create_subjects_for_student(user_id=user_id)
                await message.reply("Добро пожаловать, владелец! Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество), чтобы завершить регистрацию.")
                await state.set_state(AddUserState.waiting_for_fio)
            elif role[0] != OWNER:
                # Если роль владельца указана некорректно, обновляем ее
                await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (OWNER, user_id))
                await db.commit()
                await message.reply("Ваша роль была обновлена до владельца. Добро пожаловать!")
                await db_helper.create_subjects_for_student(user_id=user_id)
                await db_helper.show_main_menu(message)
            else:
                await message.reply("Добро пожаловать обратно, владелец!")
                await db_helper.show_main_menu(message)
        else:
            # Проверка для других пользователей
            async with db.execute("SELECT role, user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
                role = await cursor.fetchone()

            try:
                await db_helper.add_user(
                        user_id=user_id,
                        name=None,  # Имя будет запрошено отдельно
                        role=role[0] if role is not None else UNREGISTERED,
                        username=message.from_user.username or None
                )
            except:
                await message.reply(
                    "Здравствуйте! Для доступа к некоторым возможностям бота, пожалуйста, введите токен.\n"
                    "Для ввода токена используйте команду /token \"токен\"\n"
                    "Если у вас его нет, обратитесь к владельцу или администратору."
                )
                return
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
                role = await cursor.fetchone()
            
            # Если пользователь еще не зарегистрирован
            if role[0] == UNREGISTERED:
                await message.reply(
                    "Здравствуйте! Для доступа к некоторым возможностям бота, пожалуйста, введите токен.\n"
                    "Для ввода токена используйте команду /token \"токен\"\n"
                    "Если у вас его нет, обратитесь к владельцу или администратору."
                )

# Завершение регистрации после ввода ФИО
@router.message(AddUserState.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    fio = message.text

    # Проверка уникальности имени
    if not await db_helper.is_unique_name(fio):
        await message.reply("Пользователь с таким ФИО уже существует. Пожалуйста, введите уникальное ФИО.")
        return

    async with aiosqlite.connect('bot_data.db') as db:
        role = await db_helper.get_user_role(user_id=user_id)

        # Завершаем регистрацию для владельца или других пользователей
        await db.execute("UPDATE users SET name = ?, role = ?, type = ? WHERE user_id = ?", (fio, role, "student", user_id))
        await db.commit()

        await db_helper.create_subjects_for_student(user_id=user_id)

    await message.reply("Регистрация завершена. Добро пожаловать!")
    await db_helper.show_main_menu(message)
    await state.clear()

# Обработка токена для регистрации или назначения роли
@router.message(lambda message: message.text.startswith("/token "))
async def process_token(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    token = message.text.split(" ")[1]

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


        await message.reply(f"Введите ваше ФИО (Фамилия Имя Отчество), чтобы завершить регистрацию как {role}.")
        await state.set_state(AddUserState.waiting_for_fio)

        await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))

        # Помечаем токен как использованный
        await db.execute("UPDATE tokens SET used = 1 WHERE token = ?", (token,))
        await db.commit()

class AddTypeState(StatesGroup):
    choosing_user = State()
    confirm_change = State()

@router.message(Command(commands=['addtype']))
async def addtype_user(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not db_helper.has_permission(user_class, OWNER):
        await message.reply("У вас нет прав для изменения типа пользователя.")
        return

    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE type = ? AND role = ? AND user_id != ? AND role != ?",
                ("student", ADMIN, settings.bots.owner_chat_id, OWNER)
            ) as cursor:
                available_admins = await cursor.fetchall()
        
        if not available_admins:
            await message.reply("Нет доступных администраторов.")
            return

        buttons = [
            [
                types.InlineKeyboardButton(
                    text=admin[1],
                    callback_data=f"change_type_{admin[0]}"
                ) for admin in available_admins
            ],
            [
                types.InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_delete"
                )
            ]
        ]

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.set_state(AddTypeState.choosing_user)
        await message.reply("Выберите администратора для изменения типа на teacher:", reply_markup=keyboard)

    except aiosqlite.Error as e:
        await message.reply("Произошла ошибка при получении списка администраторов. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при получении администраторов для изменения: {e}")

# Обработка выбора пользователя или администратора для удаления
@router.callback_query(
    lambda c: c.data and (c.data.startswith('change_type_')),
    AddTypeState.choosing_user
)
async def process_change_type(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id_to_delete = int(callback_query.data.split('_')[2])
        is_admin = callback_query.data.startswith('change_type_')

        await state.update_data(user_id_to_delete=user_id_to_delete, is_admin=is_admin)

        # Запрашиваем подтверждение на удаление
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Подтвердить",
                    callback_data="confirm_delete"
                ),
                types.InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_delete"
                )
            ]
        ]
    )

        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                (user_id_to_delete,)
            ) as cursor:
                user_data = await cursor.fetchone()

        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        await state.set_state(AddTypeState.confirm_change)
        await callback_query.message.edit_text(
            f"Вы уверены, что хотите изменить роль администратора {user_name} (Username: @{username})?",
            reply_markup=keyboard
        )
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при обработке выбора пользователя для изменения типа: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при обработке выбора пользователя для изменения типа: {e}")

# Подтверждение удаления пользователя или администратора
@router.callback_query(lambda c: c.data == 'confirm_delete', AddTypeState.confirm_change)
async def confirm_change_type(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        user_id_to_change = data['user_id_to_delete']
        is_admin = data.get('is_admin', False)

        async with aiosqlite.connect('bot_data.db') as db:
            # Получаем роль пользователя перед изменением
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id_to_change,)) as cursor:
                role_result = await cursor.fetchone()
            if not role_result:
                await callback_query.message.edit_text("Администратор не найден.", reply_markup=None)
                await state.clear()
                return
            role = role_result[0]

            if role == OWNER:
                await callback_query.message.edit_text("Невозможно изменить владельца.", reply_markup=None)
                await state.clear()
                return

            if is_admin:
                await db.execute(
                    "UPDATE users SET type = ? WHERE user_id = ?",
                    ("teacher", user_id_to_change)
                )
                await db.commit()

                # Получаем имя и username для уведомления
                async with db.execute(
                    "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                    (user_id_to_change,)
                ) as cursor:
                    user_data = await cursor.fetchone()

                user_name, username = user_data if user_data else ("Unknown", "Unknown")
                await callback_query.message.edit_text(
                    f"Тип администратора {user_name} (Username: @{username}) был иземнен до teacher.",
                    reply_markup=None
                )

        await state.clear()
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при изменении типа пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при подтверждении изменения типа пользователя: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при подтверждении изменения типа пользователя: {e}")


class DelTypeState(StatesGroup):
    choosing_user = State()
    confirm_delete = State()


@router.message(Command(commands=['deltype']))
async def deltype_user(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not db_helper.has_permission(user_class, OWNER):
        await message.reply("У вас нет прав для изменения типа пользователя.")
        return

    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE type = ? AND role = ? AND user_id != ? AND role != ?",
                ("teacher", ADMIN, settings.bots.owner_chat_id, OWNER)
            ) as cursor:
                available_admins = await cursor.fetchall()
        
        if not available_admins:
            await message.reply("Нет доступных администраторов.")
            return

        buttons = [
            [
                types.InlineKeyboardButton(
                    text=admin[1],
                    callback_data=f"change_type_{admin[0]}"
                ) for admin in available_admins
            ],
            [
                types.InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_delete"
                )
            ]
        ]

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.set_state(DelTypeState.choosing_user)
        await message.reply("Выберите администратора для изменения типа на student:", reply_markup=keyboard)

    except aiosqlite.Error as e:
        await message.reply("Произошла ошибка при получении списка администраторов. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при получении администраторов для изменения: {e}")

# Обработка выбора пользователя или администратора для удаления
@router.callback_query(
    lambda c: c.data and (c.data.startswith('change_type_')),
    DelTypeState.choosing_user
)
async def process_change_type(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id_to_delete = int(callback_query.data.split('_')[2])
        is_admin = callback_query.data.startswith('change_type_')

        await state.update_data(user_id_to_delete=user_id_to_delete, is_admin=is_admin)

        # Запрашиваем подтверждение на удаление
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Подтвердить",
                    callback_data="confirm_delete"
                ),
                types.InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_delete"
                )
            ]
        ]
    )

        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                (user_id_to_delete,)
            ) as cursor:
                user_data = await cursor.fetchone()

        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        await state.set_state(DelTypeState.confirm_delete)
        await callback_query.message.edit_text(
            f"Вы уверены, что хотите изменить роль администратора {user_name} (Username: @{username})?",
            reply_markup=keyboard
        )
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при обработке выбора пользователя для изменения типа: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при обработке выбора пользователя для изменения типа: {e}")

# Подтверждение удаления пользователя или администратора
@router.callback_query(lambda c: c.data == 'confirm_delete', DelTypeState.confirm_delete)
async def confirm_change_type(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        user_id_to_change = data['user_id_to_delete']
        is_admin = data.get('is_admin', False)

        async with aiosqlite.connect('bot_data.db') as db:
            # Получаем роль пользователя перед изменением
            async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id_to_change,)) as cursor:
                role_result = await cursor.fetchone()
            if not role_result:
                await callback_query.message.edit_text("Администратор не найден.", reply_markup=None)
                await state.clear()
                return
            role = role_result[0]

            if role == OWNER:
                await callback_query.message.edit_text("Невозможно изменить владельца.", reply_markup=None)
                await state.clear()
                return

            if is_admin:
                await db.execute(
                    "UPDATE users SET type = ? WHERE user_id = ?",
                    ("student", user_id_to_change)
                )
                await db.commit()

                # Получаем имя и username для уведомления
                async with db.execute(
                    "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                    (user_id_to_change,)
                ) as cursor:
                    user_data = await cursor.fetchone()

                user_name, username = user_data if user_data else ("Unknown", "Unknown")
                await callback_query.message.edit_text(
                    f"Тип администратора {user_name} (Username: @{username}) был иземнен до student.",
                    reply_markup=None
                )

        await state.clear()
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при изменении типа пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при подтверждении изменения типа пользователя: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при подтверждении изменения типа пользователя: {e}")