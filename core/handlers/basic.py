from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import aiosqlite

from database.db_helper import db_helper, Class9AState, Class9BState

router = Router()

class ChooseClassState(StatesGroup):
    action = State()

@router.message(Command(commands=['start']))
async def get_start(message: Message):
    user_id = message.from_user.id
    role = await db_helper.get_user_role(user_id=user_id)

    if role is None or role == "unregistered":
        await message.answer('Здравствуйте! Для доступа к некоторым возможностям бота, пожалуйста, введите токен.\nДля ввода токена используйте команду /token "здесь без скобок ваш токен"\nЕсли у вас его нет, обратитесь к владельцу или администратору для его получения.\nВладелец бота: @Kibershkolnik')
    else:
        await db_helper.show_choose_class_menu(message)

@router.message(Class9AState.action, F.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_choose_class_menu(message)

@router.message(Class9BState.action, F.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_choose_class_menu(message)

@router.message(Command(commands=['help']))
async def send_help(message: types.Message):
    user_class = await db_helper.get_user_class(message.from_user.id)

    if user_class == 'owner':  # Проверка для владельца
        await message.answer("Доступные команды для владельца:\n"
                             "/addNewUser - добавить пользователя\n"
                             "/makeAdmin - повысить пользователя до администратора\n"
                             "/deleteUser - удалить пользователя\n"
                             "/deleteAdmin - удалить администратора\n"
                             "/addtype - изменить тип администратора на \"teacher\"\n"
                             "/deltype - изменить тип администратора на \"student\"\n"
                             "(/)clear_data - очистить базу данных (ручной ввод)\n"
                             "/help - справка")
    elif user_class == 'admin':  # Проверка для администратора
        await message.answer("Доступные команды для администратора:\n"
                             "/addNewUser - добавить пользователя\n"
                             "/deleteUser - удалить пользователя\n"
                             "/help - справка")
    else:
        await message.answer("Команда /help позволяет получить справочную информацию о доступных функциях.\n"
                             "/token 'ваш токен здесь' - для использования токена повышения прав.")