from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database.db_helper import db_helper

router = Router()

@router.message(Command(commands=['help']))
async def send_help(message: types.Message):
    user_class = await db_helper.get_user_class(message.from_user.id)

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