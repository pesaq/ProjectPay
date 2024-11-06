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

    # Проверяем права доступа пользователя
    if not db_helper.has_permission(user_class, ADMIN):
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
                await callback_query.message.edit_text("Пользователь не найден.")
                await state.clear()
                return
            role = role_result[0]

            if role == OWNER:
                await callback_query.message.edit_text("Невозможно удалить владельца.")
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
        await callback_query.message.edit_text("Удаление отменено.")
        await state.clear()
    except Exception as e:
        print(f"Необработанное исключение при отмене удаления: {e}")