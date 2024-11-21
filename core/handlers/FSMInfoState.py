from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import uuid

from core.settings import get_settings

from database.db_helper import db_helper
from user_classes import *

import time
import datetime
import aiosqlite

router = Router()

class Info9AState(StatesGroup):
    waiting_for_info_action = State()
    waiting_for_info_entry = State()
    
# Обработка кнопки "Информация 9A"
@router.message(lambda message: message.text == "Информация (9А)")
async def handle_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    await db_helper.delete_old_information()
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    if user_class in [ADMIN, OWNER]:
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Добавить информацию (9А)'
                ),
                types.KeyboardButton(
                    text='Посмотреть информацию (9А)'
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
                    text='Посмотреть информацию (9А)'
                ),
                types.KeyboardButton(
                    text='Назад'
                )
            ]
        ], resize_keyboard=True)
    
    await message.answer("Выберите действие с информацией:", reply_markup=markup)
    await state.set_state(Info9AState.waiting_for_info_action)

@router.message(Info9AState.waiting_for_info_action, lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_9a_main_menu(message, state)

@router.message(lambda message: message.text == "Добавить информацию (9А)")
async def add_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    user_class = await db_helper.get_user_class(message.from_user.id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
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
    await state.set_state(Info9AState.waiting_for_info_entry)

@router.message(Info9AState.waiting_for_info_entry)
async def process_info_entry(message: types.Message, state: FSMContext):
    random_filename = f'photo_{uuid.uuid4()}.jpg'
    info_text = ""

    if message.photo:
        await message.bot.download(file=message.photo[-1].file_id, destination=f'images_data/{random_filename}')
        if message.caption:
            info_text = message.caption
        else:
            info_text = "(без описания)"

    elif message.text:
        info_text = message.text

    if message.text and message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Информация'
        user_class = await db_helper.get_user_class(message.from_user.id)
        if user_class in [ADMIN, OWNER]:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(
                        text='Добавить информацию (9А)'
                    ),
                    types.KeyboardButton(
                        text='Посмотреть информацию (9А)'
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
                        text='Посмотреть информацию (9А)'
                    ),
                    types.KeyboardButton(
                        text='Назад'
                    )
                ]
            ], resize_keyboard=True)
        await message.answer("Возвращены в подменю 'Информация (9А)'.", reply_markup=markup)
        await state.set_state(Info9AState.waiting_for_info_action)
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        try:
            images_entry = random_filename if message.photo else ""
            await db.execute(
                "INSERT INTO information (info, sender, timestamp, class_name, images) VALUES (?, ?, ?, ?, ?)",
                (info_text, await db_helper.get_user_full_name(user_id), time.time(), '9a', images_entry)
            )
            await db.commit()
            await message.answer("Информация в 9А успешно добавлена.")
        except aiosqlite.Error as e:
            await message.answer("Произошла ошибка при добавлении работы. Пожалуйста, попробуйте снова.")
            print(f"Ошибка базы данных: {e}")
    
    await state.clear()
    await db_helper.show_9a_main_menu(message, state)

@router.message(lambda message: message.text == "Посмотреть информацию (9А)")
async def view_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    now = time.time()
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute("SELECT info, sender, timestamp, images FROM information WHERE timestamp >= ? AND class_name = ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60, '9a')) as cursor:
            recent_info = await cursor.fetchall()
    
    recent_info = sorted(recent_info, key=lambda i: i[2])
    if not recent_info:
        await message.answer("Нет доступной информации в 9А.")
    else:
        for work, sender, timestamp, images in recent_info:
            try:
                timestamp_dt = datetime.datetime.fromtimestamp(float(timestamp))
                response_text = f"{work}\n\nОтправлено: {sender}\nДата: {timestamp_dt.strftime('%d-%m-%Y')}, Время: {timestamp_dt.strftime('%H:%M')}"
                
                # Создание inline-кнопки, если поле images не пустое
                if images and images.strip():  # Проверяем, что поле не пустое
                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text='Посмотреть изображение',
                                callback_data=f'image_{images.strip()}'
                            )
                        ]
                    ])
                    await message.answer(response_text, reply_markup=keyboard)
                else:
                    await message.answer(response_text)
                    
            except Exception as e:
                await message.answer("Ошибка при обработке времени. Пожалуйста, попробуйте позже.")
                print(f"Ошибка: {e}")
    
    await message.answer("Возвращаюсь в главное меню.")
    await db_helper.show_9a_main_menu(message, state)

@router.message(Info9AState.waiting_for_info_action, F.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_9a_main_menu(message, state)







class Info9BState(StatesGroup):
    waiting_for_info_action = State()
    waiting_for_info_entry = State()
    
# Обработка кнопки "Информация 9A"
@router.message(lambda message: message.text == "Информация (9Б)")
async def handle_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    await db_helper.delete_old_information()
    if user_class_name != '9b' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9Б классе')
        return
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    if user_class in [ADMIN, OWNER]:
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Добавить информацию (9Б)'
                ),
                types.KeyboardButton(
                    text='Посмотреть информацию (9Б)'
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
                    text='Посмотреть информацию (9Б)'
                ),
                types.KeyboardButton(
                    text='Назад'
                )
            ]
        ], resize_keyboard=True)
    
    await message.answer("Выберите действие с информацией:", reply_markup=markup)
    await state.set_state(Info9BState.waiting_for_info_action)

@router.message(Info9BState.waiting_for_info_action, lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_9b_main_menu(message, state)

@router.message(lambda message: message.text == "Добавить информацию (9Б)")
async def add_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    user_class = await db_helper.get_user_class(message.from_user.id)
    if user_class_name != '9b' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9Б классе')
        return
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
    await state.set_state(Info9BState.waiting_for_info_entry)

@router.message(Info9BState.waiting_for_info_entry)
async def process_info_entry(message: types.Message, state: FSMContext):
    random_filename = f'photo_{uuid.uuid4()}.jpg'
    info_text = ""

    if message.photo:
        await message.bot.download(file=message.photo[-1].file_id, destination=f'images_data/{random_filename}')
        if message.caption:
            info_text = message.caption
        else:
            info_text = "(без описания)"

    elif message.text:
        info_text = message.text

    if message.text and message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Информация'
        user_class = await db_helper.get_user_class(message.from_user.id)
        if user_class in [ADMIN, OWNER]:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(
                        text='Добавить информацию (9Б)'
                    ),
                    types.KeyboardButton(
                        text='Посмотреть информацию (9Б)'
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
                        text='Посмотреть информацию (9Б)'
                    ),
                    types.KeyboardButton(
                        text='Назад'
                    )
                ]
            ], resize_keyboard=True)
        await message.answer("Возвращены в подменю 'Информация (9Б)'.", reply_markup=markup)
        await state.set_state(Info9BState.waiting_for_info_action)
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        try:
            images_entry = random_filename if message.photo else ""
            await db.execute(
                "INSERT INTO information (info, sender, timestamp, class_name, images) VALUES (?, ?, ?, ?, ?)",
                (info_text, await db_helper.get_user_full_name(user_id), time.time(), '9b', images_entry)
            )
            await db.commit()
            await message.answer("Информация в 9Б успешно добавлена.")
        except aiosqlite.Error as e:
            await message.answer("Произошла ошибка при добавлении работы. Пожалуйста, попробуйте снова.")
            print(f"Ошибка базы данных: {e}")
    
    await state.clear()
    await db_helper.show_9b_main_menu(message, state)

@router.message(lambda message: message.text == "Посмотреть информацию (9Б)")
async def view_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9b' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9Б классе')
        return
    now = time.time()
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute("SELECT info, sender, timestamp, images FROM information WHERE timestamp >= ? AND class_name = ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60, '9b')) as cursor:
            recent_info = await cursor.fetchall()
    
    recent_info = sorted(recent_info, key=lambda i: i[2])
    if not recent_info:
        await message.answer("Нет доступной информации в 9Б.")
    else:
        for work, sender, timestamp, images in recent_info:
            try:
                timestamp_dt = datetime.datetime.fromtimestamp(float(timestamp))
                response_text = f"{work}\n\nОтправлено: {sender}\nДата: {timestamp_dt.strftime('%d-%m-%Y')}, Время: {timestamp_dt.strftime('%H:%M')}"
                
                # Создание inline-кнопки, если поле images не пустое
                if images and images.strip():  # Проверяем, что поле не пустое
                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text='Посмотреть изображение',
                                callback_data=f'image_{images.strip()}'
                            )
                        ]
                    ])
                    await message.answer(response_text, reply_markup=keyboard)
                else:
                    await message.answer(response_text)
                    
            except Exception as e:
                await message.answer("Ошибка при обработке времени. Пожалуйста, попробуйте позже.")
                print(f"Ошибка: {e}")

    await message.answer("Возвращаюсь в главное меню.")
    await db_helper.show_9b_main_menu(message, state)