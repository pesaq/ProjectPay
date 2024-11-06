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

class InfoState(StatesGroup):
    waiting_for_info_entry = State()
    
# Обработка кнопки "Информация"
@router.message(lambda message: message.text == "Информация")
async def handle_info(message: types.Message):
    user_class = await db_helper.get_user_class(message.from_user.id)
    if user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    if user_class in [ADMIN, OWNER]:
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Добавить информацию'
                ),
                types.KeyboardButton(
                    text='Посмотреть информацию'
                ),
                types.KeyboardButton(
                    text='Назад'
                )
            ]
        ], resize_keyboard=True)
    else:
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Посмотреть информацию'
                ),
                types.KeyboardButton(
                    text='Назад'
                )
            ]
        ], resize_keyboard=True)
    
    await message.answer("Выберите действие с информацией:", reply_markup=markup)

@router.message(lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_main_menu(message)

@router.message(lambda message: message.text == "Добавить информацию")
async def add_info(message: types.Message, state: FSMContext):
    user_class = await db_helper.get_user_class(message.from_user.id)
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления информации.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(keyboard=[
        [
            types.KeyboardButton(
                text='Отмена'
            )
        ]
    ], resize_keyboard=True)
    await message.answer("Введите информацию для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await state.set_state(InfoState.waiting_for_info_entry)

@router.message(InfoState.waiting_for_info_entry)
async def process_info_entry(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Информация'
        user_class = await db_helper.get_user_class(message.from_user.id)
        if user_class in [ADMIN, OWNER]:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(
                        text='Добавить информацию'
                    ),
                    types.KeyboardButton(
                        text='Посмотреть информацию'
                    ),
                    types.KeyboardButton(
                        text='Назад'
                    )
                ]
            ], resize_keyboard=True)
        else:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(
                        text='Посмотреть информацию'
                    ),
                    types.KeyboardButton(
                        text='Назад'
                    )
                ]
            ], resize_keyboard=True)
        await message.answer("Возвращены в подменю 'Информация'.", reply_markup=markup)
        await state.clear()
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute(
            "INSERT INTO information (info, sender, timestamp) VALUES (?, ?, ?)",
            (message.text, await db_helper.get_user_full_name(user_id), time.time())
        )
        await db.commit()
    await message.answer("Информация успешно добавлена.")
    await state.clear()
    await db_helper.show_main_menu(message)

@router.message(lambda message: message.text == "Посмотреть информацию")
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
    await db_helper.show_main_menu(message)