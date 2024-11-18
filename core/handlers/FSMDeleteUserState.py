from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from core.settings import get_settings

from database.db_helper import db_helper
from user_classes import *

import time
import datetime
import aiosqlite

router = Router()
settings = get_settings('.env')

# Состояния для удаления пользователей и администраторов
class DeleteUserState(StatesGroup):
    choosing_user = State()
    confirm_delete = State()

# Обработка команды удаления пользователя
@router.message(Command(commands=['deleteUser']))
async def delete_user_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(user_id)
    user_class_name = await db_helper.get_user_class_name(user_id)

    async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT type FROM users WHERE user_id=?", (user_id,)) as cursor:
                user_type = await cursor.fetchone()

                if user_type:
                    user_type = user_type[0]
    # Проверяем права доступа пользователя
    if not db_helper.has_permission(user_class, ADMIN):
        await message.reply("У вас нет прав для удаления пользователей.")
        return

    try:
        async with aiosqlite.connect('bot_data.db') as db:
            if user_type == 'student':
                if user_class_name == '9a':
                    async with db.execute(
                        "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE class_name = ? AND role = ? AND role != ?",
                        ('9a', USER, OWNER)
                    ) as cursor:
                        available_users = await cursor.fetchall()
                elif user_class_name == '9b':
                    async with db.execute(
                        "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE class_name = ? AND role = ? AND role != ?",
                        ('9b', USER, OWNER)
                    ) as cursor:
                        available_users = await cursor.fetchall()
                elif user_class_name == 'general':
                    async with db.execute(
                        "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND role != ?",
                        (USER, OWNER)
                    ) as cursor:
                        available_users = await cursor.fetchall()
                else:
                    await message.answer('Вы не состоите в классе')
                    return
            if user_class == OWNER or user_type == 'teacher':
                async with db.execute(
                    "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND role != ?",
                    (USER, OWNER)
                ) as cursor:
                    available_users = await cursor.fetchall()

            if not available_users:
                    await message.reply("Нет доступных пользователей для удаления.")
                    return

        buttons = [
            [
                types.InlineKeyboardButton(
                    text=user[1],
                    callback_data=f"delete_user_{user[0]}"
                ) for user in available_users
            ],
            [
                types.InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_delete"
                )
            ]
        ]

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        await state.set_state(DeleteUserState.choosing_user)
        await message.reply("Выберите пользователя для удаления:", reply_markup=keyboard)

    except aiosqlite.Error as e:
        await message.reply("Произошла ошибка при получении списка пользователей. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при получении пользователей для удаления: {e}")

# Обработка команды удаления администратора
@router.message(Command(commands=['deleteAdmin']))
async def delete_admin_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(user_id)

    # Проверяем права доступа пользователя
    if not db_helper.has_permission(user_class, OWNER):
        await message.reply("У вас нет прав для удаления администраторов.")
        return

    try:
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE role = ? AND user_id != ? AND role != ?",
                (ADMIN, settings.bots.owner_chat_id, OWNER)
            ) as cursor:
                available_admins = await cursor.fetchall()

        if not available_admins:
            await message.reply("Нет доступных администраторов для удаления.")
            return

        buttons = [
            [
                types.InlineKeyboardButton(
                    text=admin[1],
                    callback_data=f"delete_admin_{admin[0]}"
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

        await state.set_state(DeleteUserState.choosing_user)
        await message.reply("Выберите администратора для удаления:", reply_markup=keyboard)

    except aiosqlite.Error as e:
        await message.reply("Произошла ошибка при получении списка администраторов. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при получении администраторов для удаления: {e}")

# Обработка выбора пользователя или администратора для удаления
@router.callback_query(
    lambda c: c.data and (c.data.startswith('delete_user_') or c.data.startswith('delete_admin_')),
    DeleteUserState.choosing_user
)
async def process_delete_user(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id_to_delete = int(callback_query.data.split('_')[2])
        user_class_name_to_delete = await db_helper.get_user_class_name(user_id_to_delete)
        is_admin = callback_query.data.startswith('delete_admin_')

        await state.update_data(user_id_to_delete=user_id_to_delete, is_admin=is_admin)

        # Запрашиваем подтверждение на удаление
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Подтвердить удаление",
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
        await state.set_state(DeleteUserState.confirm_delete)
        await callback_query.message.edit_text(
            f"Вы уверены, что хотите удалить пользователя {user_name} ({user_class_name_to_delete}) (Username: @{username})?",
            reply_markup=keyboard
        )
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при обработке выбора пользователя для удаления: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при обработке выбора пользователя для удаления: {e}")

# Подтверждение удаления пользователя или администратора
@router.callback_query(lambda c: c.data == 'confirm_delete', DeleteUserState.confirm_delete)
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
                await callback_query.message.edit_text("Пользователь не найден.", reply_markup=None)
                await state.clear()
                return
            role = role_result[0]

            if role == OWNER:
                await callback_query.message.edit_text("Невозможно удалить владельца.", reply_markup=None)
                await state.clear()
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
                    f"Администратор {user_name} (Username: @{username}) был понижен до пользователя.",
                    reply_markup=None
                )
                await db_helper.show_choose_class_menu(callback_query.message)
            else:
                # Понижаем пользователя до незарегистрированного
                await db.execute(
                    "UPDATE users SET role = ?, class_name = ? WHERE user_id = ?",
                    ('unregistered', None, user_id_to_delete)
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
                    f"Пользователь {user_name} (Username: @{username}) был удален.", reply_markup=None
                )
                await db_helper.show_choose_class_menu(callback_query.message)

        await state.clear()
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при удалении пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при подтверждении удаления пользователя: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при подтверждении удаления пользователя: {e}")

# Обработка отмены удаления
@router.callback_query(lambda c: c.data == 'cancel_delete')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Удаление отменено.", reply_markup=None)
        await db_helper.show_choose_class_menu(callback_query.message)
        await state.clear()
    except Exception as e:
        print(f"Необработанное исключение при отмене удаления: {e}")

class ClearTables(StatesGroup):
    choosing_clear = State()
    confirm_clear = State()

# Обработчик команды /clear_all для владельца
@router.message(Command(commands=['clear_data']))
async def select_clear(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверка прав: только владелец может выполнять команду
    if user_id != settings.bots.owner_chat_id:
        await message.reply("У вас нет прав для выполнения этой команды.")
        return
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text='Оценки',
                callback_data='clear_marks'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Всех пользователей (user)',
                callback_data='clear_users'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Всех администраторов (admin)',
                callback_data='clear_admins'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Всю Информацию',
                callback_data='clear_info'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Все Домашние задания',
                callback_data='clear_homework'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Все заметки (Дневник)',
                callback_data='clear_diary'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Отмена',
                callback_data='cancel_clear'
            )
        ]
    ])
    
    await message.answer('Что вы хотите очистить?', reply_markup=markup)
    await state.set_state(ClearTables.choosing_clear)

@router.callback_query(ClearTables.choosing_clear, F.data.startswith('clear_'))
async def delete_data(callback_query: types.CallbackQuery, state: FSMContext):
    what_clear = callback_query.data.split('_')[1]
    await state.update_data(what_clear=what_clear)

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text='Подтвердить',
                callback_data='confirm_clear'
            ),
            types.InlineKeyboardButton(
                text='Отмена',
                callback_data='cancel_clear'
            )
        ]
    ])

    if what_clear == 'marks':
        confirmation_message = 'Вы уверены, что хотите очистить Оценки?\n\nПосле удаления их невозможно будет восстановить'
    if what_clear == 'users':
        confirmation_message = 'Вы уверены, что хотите очистить Всех пользователей?\n\nПосле удаления их невозможно будет восстановить'
    if what_clear == 'admins':
        confirmation_message = 'Вы уверены, что хотите очистить Всех администраторов?\n\nПосле удаления их невозможно будет восстановить'
    if what_clear == 'info':
        confirmation_message = 'Вы уверены, что хотите очистить Всю Информацию?\n\nПосле удаления ее невозможно будет восстановить'
    if what_clear == 'homework':
        confirmation_message = 'Вы уверены, что хотите очистить Все Домашние задания?\n\nПосле удаления их невозможно будет восстановить'
    if what_clear == 'diary':
        confirmation_message = 'Вы уверены, что хотите очистить Все заметки (Дневник)?\n\nПосле удаления их невозможно будет восстановить'

    await callback_query.message.edit_text(confirmation_message, reply_markup=markup)
    await state.set_state(ClearTables.confirm_clear)



@router.callback_query(ClearTables.confirm_clear, F.data == 'confirm_clear')
async def confirm_delete_data(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    what_clear = data['what_clear']

    async with aiosqlite.connect('bot_data.db') as db:
        if what_clear == 'marks':
            await db.execute("UPDATE marks SET grades = ''")
            await callback_query.message.edit_text('Все оценки были удалены', reply_markup=None)
        await db.commit()

        if what_clear == 'users':
            await db.execute("DELETE FROM users WHERE role = ? AND user_id != ?", (USER, settings.bots.owner_chat_id,))
            await callback_query.message.edit_text('Все Пользователи кроме владельца были удалены', reply_markup=None)
        await db.commit()

        if what_clear == 'admins':
            await db.execute("DELETE FROM users WHERE role = ? AND user_id != ?", (ADMIN, settings.bots.owner_chat_id,))
            await callback_query.message.edit_text('Все Администраторы были удалены', reply_markup=None)
        await db.commit()

        if what_clear == 'info':
            await db.execute("DELETE FROM information")
            await callback_query.message.edit_text('Вся Информация была удалена', reply_markup=None)
        await db.commit()

        if what_clear == 'homework':
            await db.execute("DELETE FROM works")
            await callback_query.message.edit_text('Все Домашние задания были удалены', reply_markup=None)
        await db.commit()

        if what_clear == 'diary':
            await db.execute("DELETE FROM homework")
            await callback_query.message.edit_text('Все Заметки (Дневник) были удалены', reply_markup=None)
        await db.commit()
    
    await db_helper.show_choose_class_menu(callback_query.message)
    
    await state.clear()

@router.callback_query(ClearTables.confirm_clear, F.data == 'cancel_clear')
async def cancel_delete_data(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text('Вы отменили действие')
    await db_helper.show_choose_class_menu(callback_query.message)
    await state.clear()

@router.callback_query(ClearTables.choosing_clear, F.data == 'cancel_clear')
async def cancel_delete_data(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text('Вы отменили действие')
    await db_helper.show_choose_class_menu(callback_query.message)
    await state.clear()