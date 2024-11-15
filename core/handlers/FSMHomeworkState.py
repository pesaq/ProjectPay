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
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Домашние работы'
        user_class = await db_helper.get_user_class(message.from_user.id)
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

        await message.answer("Возвращены в подменю 'Домашние работы'.", reply_markup=markup)
        await state.set_state(Work9AState.waiting_for_work_action)
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        try:
            await db.execute(
                "INSERT INTO works (work, sender, class_name, timestamp) VALUES (?, ?, ?, ?)",
                (message.text, await db_helper.get_user_full_name(user_id), '9a', time.time())
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
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT work, sender, timestamp FROM works WHERE timestamp >= ? AND class_name = ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60, '9a')) as cursor:
            recent_works = await cursor.fetchall()

    recent_works = sorted(recent_works, key=lambda i: i[2])
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
    if message.text.lower() == "отмена":
        # Возвращаем пользователя в подменю 'Домашние работы'
        user_class = await db_helper.get_user_class(message.from_user.id)
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

        await message.answer("Возвращены в подменю 'Домашние работы'.", reply_markup=markup)
        await state.set_state(Work9BState.waiting_for_info_action)
        return

    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        try:
            await db.execute(
                "INSERT INTO works (work, sender, class_name, timestamp) VALUES (?, ?, ?, ?)",
                (message.text, await db_helper.get_user_full_name(user_id), '9b', time.time())
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
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT work, sender, timestamp FROM works WHERE timestamp >= ? AND class_name = ? ORDER BY timestamp DESC", (now - 8 * 24 * 60 * 60, '9b')) as cursor:
            recent_works = await cursor.fetchall()

    recent_works = sorted(recent_works, key=lambda i: i[2])
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
    await db_helper.show_9b_main_menu(message, state)