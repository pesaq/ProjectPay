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

class Work9AState(StatesGroup):
    waiting_for_work_action = State()
    waiting_for_work_entry = State()
    
# Обработка кнопки "Домашние работы"
@router.message(lambda message: message.text == "Домашние работы (9А)")
async def handle_works(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    await db_helper.delete_old_works()
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    if user_class in [ADMIN, OWNER]:
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Добавить работу (9А)'
                ),
                types.KeyboardButton(
                    text='Посмотреть все работы (9А)'
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
                    text='Посмотреть все работы (9А)'
                ),
                types.KeyboardButton(
                    text='Назад'
                )
            ]
        ], resize_keyboard=True)
    await message.answer("Выберите действие с работами:", reply_markup=markup)
    await state.set_state(Work9AState.waiting_for_work_action)

@router.message(Work9AState.waiting_for_work_action, lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_9a_main_menu(message, state)

@router.message(lambda message: message.text == "Добавить работу (9А)")
async def add_work(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления работы.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(keyboard=[
        [
            types.KeyboardButton(
                text='Отмена'
            )
        ]
    ], resize_keyboard=True)
    await message.answer("Введите работу для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await state.set_state(Work9AState.waiting_for_work_entry)

@router.message(Work9AState.waiting_for_work_entry)
async def process_work_entry(message: types.Message, state: FSMContext):
    random_filename = f'photo_{uuid.uuid4()}.jpg'
    work_text = ""
    
    if message.photo:
        await message.bot.download(file=message.photo[-1].file_id, destination=f'images_data/{random_filename}')
        if message.caption:
            work_text = message.caption
        else:
            work_text = "(без описания)"
    
    elif message.text:
        work_text = message.text
    
    if message.text and message.text.lower() == "отмена":
        user_class = await db_helper.get_user_class(message.from_user.id)
        if user_class in [ADMIN, OWNER]:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(text='Добавить работу (9А)'),
                    types.KeyboardButton(text='Посмотреть все работы (9А)'),
                    types.KeyboardButton(text='Назад')
                ]
            ], resize_keyboard=True)
        else:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(text='Посмотреть все работы (9А)'),
                    types.KeyboardButton(text='Назад')
                ]
            ], resize_keyboard=True)
        
        await message.answer("Возвращены в подменю 'Домашние работы'.", reply_markup=markup)
        await state.set_state(Work9AState.waiting_for_work_action)
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        try:
            images_entry = random_filename if message.photo else ""
            await db.execute(
                "INSERT INTO works (work, sender, class_name, timestamp, images) VALUES (?, ?, ?, ?, ?)",
                (work_text, await db_helper.get_user_full_name(user_id), '9a', time.time(), images_entry)
            )
            await db.commit()
            await message.answer("Работа в 9А успешно добавлена.")
        except aiosqlite.Error as e:
            await message.answer("Произошла ошибка при добавлении работы. Пожалуйста, попробуйте снова.")
            print(f"Ошибка базы данных: {e}")
    
    await state.clear()
    await db_helper.show_9a_main_menu(message, state)

@router.message(lambda message: message.text == "Посмотреть все работы (9А)")
async def view_works(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    now = time.time()
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute(
                "SELECT work, sender, timestamp, images FROM works WHERE timestamp >= ? AND class_name = ? ORDER BY timestamp DESC",
                (now - 8 * 24 * 60 * 60, '9a')) as cursor:
            recent_works = await cursor.fetchall()

    recent_works = sorted(recent_works, key=lambda i: i[2])
    if not recent_works:
        await message.answer("Нет доступных работ.")
    else:
        for work, sender, timestamp, images in recent_works:
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








class Work9BState(StatesGroup):
    waiting_for_work_action = State()
    waiting_for_work_entry = State()
    
# Обработка кнопки "Домашние работы"
@router.message(lambda message: message.text == "Домашние работы (9Б)")
async def handle_works(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9b' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9Б классе')
        return
    await db_helper.delete_old_works()
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    if user_class in [ADMIN, OWNER]:
        markup = types.ReplyKeyboardMarkup(keyboard=[
            [
                types.KeyboardButton(
                    text='Добавить работу (9Б)'
                ),
                types.KeyboardButton(
                    text='Посмотреть все работы (9Б)'
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
                    text='Посмотреть все работы (9Б)'
                ),
                types.KeyboardButton(
                    text='Назад'
                )
            ]
        ], resize_keyboard=True)
    await message.answer("Выберите действие с работами:", reply_markup=markup)
    await state.set_state(Work9BState.waiting_for_work_action)

@router.message(Work9BState.waiting_for_work_action, lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_9b_main_menu(message, state)

@router.message(lambda message: message.text == "Добавить работу (9Б)")
async def add_work(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class = await db_helper.get_user_class(message.from_user.id)
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9b' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9Б классе')
        return
    if user_class not in [ADMIN, OWNER]:
        await message.answer("У вас нет прав для добавления работы.")
        return
    # Создаем клавиатуру с кнопкой 'Отмена'
    markup = types.ReplyKeyboardMarkup(keyboard=[
        [
            types.KeyboardButton(
                text='Отмена'
            )
        ]
    ], resize_keyboard=True)
    await message.answer("Введите работу для добавления или нажмите 'Отмена'.", reply_markup=markup)
    await state.set_state(Work9BState.waiting_for_work_entry)

@router.message(Work9BState.waiting_for_work_entry)
async def process_work_entry(message: types.Message, state: FSMContext):
    random_filename = f'photo_{uuid.uuid4()}.jpg'
    work_text = ""
    
    if message.photo:
        await message.bot.download(file=message.photo[-1].file_id, destination=f'images_data/{random_filename}')
        if message.caption:
            work_text = message.caption
        else:
            work_text = "(без описания)"
    
    elif message.text:
        work_text = message.text
    
    if message.text and message.text.lower() == "отмена":
        user_class = await db_helper.get_user_class(message.from_user.id)
        if user_class in [ADMIN, OWNER]:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(text='Добавить работу (9Б)'),
                    types.KeyboardButton(text='Посмотреть все работы (9Б)'),
                    types.KeyboardButton(text='Назад')
                ]
            ], resize_keyboard=True)
        else:
            markup = types.ReplyKeyboardMarkup(keyboard=[
                [
                    types.KeyboardButton(text='Посмотреть все работы (9Б)'),
                    types.KeyboardButton(text='Назад')
                ]
            ], resize_keyboard=True)
        
        await message.answer("Возвращены в подменю 'Домашние работы'.", reply_markup=markup)
        await state.set_state(Work9BState.waiting_for_work_action)
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        try:
            images_entry = random_filename if message.photo else ""
            await db.execute(
                "INSERT INTO works (work, sender, class_name, timestamp, images) VALUES (?, ?, ?, ?, ?)",
                (work_text, await db_helper.get_user_full_name(user_id), '9b', time.time(), images_entry)
            )
            await db.commit()
            await message.answer("Работа в 9Б успешно добавлена.")
        except aiosqlite.Error as e:
            await message.answer("Произошла ошибка при добавлении работы. Пожалуйста, попробуйте снова.")
            print(f"Ошибка базы данных: {e}")
    
    await state.clear()
    await db_helper.show_9b_main_menu(message, state)

@router.message(lambda message: message.text == "Посмотреть все работы (9Б)")
async def view_works(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9b' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9Б классе')
        return
    now = time.time()
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute(
                "SELECT work, sender, timestamp, images FROM works WHERE timestamp >= ? AND class_name = ? ORDER BY timestamp DESC",
                (now - 8 * 24 * 60 * 60, '9b')) as cursor:
            recent_works = await cursor.fetchall()

    recent_works = sorted(recent_works, key=lambda i: i[2])
    if not recent_works:
        await message.answer("Нет доступных работ.")
    else:
        for work, sender, timestamp, images in recent_works:
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

@router.callback_query(lambda cb: cb.data.startswith('image_'))
async def send_image(callback_query: types.CallbackQuery):
    image_name = callback_query.data.split('_', 1)[1]
    image_path = f'images_data/{image_name}'

    try:
        # Создаем InputFile из пути к изображению
        photo = types.FSInputFile(image_path)
        await callback_query.message.answer_photo(photo=photo)
    except FileNotFoundError:
        await callback_query.answer("Изображение не найдено.")
    except Exception as e:
        await callback_query.answer("Произошла ошибка при отправке изображения.")
        print(f"Ошибка: {e}")