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

class HomeworkState(StatesGroup):
    waiting_for_subject_selection = State()
    waiting_for_homework_action = State()
    waiting_for_homework_entry = State()

# Обработка кнопки "Дневник"
@router.message(lambda message: message.text == "Дневник")
async def handle_diary(message: types.Message, state: FSMContext):
    user_class = await db_helper.get_user_class(message.from_user.id)
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    user_id = message.from_user.id
    keyboard_buttons = [[types.KeyboardButton(text=subject) for subject in subjects[i:i + 2]] for i in range(0, len(subjects), 2)]
    markup = types.ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
    await message.answer("Выберите предмет:", reply_markup=markup)
    await state.set_state(HomeworkState.waiting_for_subject_selection)


@router.message(HomeworkState.waiting_for_subject_selection)
async def process_subject_selection(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    subject = message.text

    if subject == "Назад":
        await state.clear()
        await db_helper.show_choose_class_menu(message)
        return

    if subject in subjects:
        pass
    else:
        await message.answer("Некорректный предмет. Пожалуйста, выберите предмет из списка.")
        return

    await state.update_data({'subject': subject})

    markup = types.ReplyKeyboardMarkup(keyboard=[
        [
            types.KeyboardButton(
                text='Записать д/з'
            ),
            types.KeyboardButton(
                text='Узнать д/з'
            ),
            types.KeyboardButton(
                text='Назад'
            )
        ]
    ],resize_keyboard=True)
    await message.answer(f"Вы выбрали {subject}. Что вы хотите сделать?", reply_markup=markup)
    await state.set_state(HomeworkState.waiting_for_homework_action)


@router.message(HomeworkState.waiting_for_homework_action)
async def process_homework_action(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    action = message.text
    subject = await state.get_data()

    if action == "Назад":
        await state.clear()
        await handle_diary(message, state)
        return

    if action == "Записать д/з":
        markup = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text='Отмена')]], resize_keyboard=True)
        await message.answer(f"Введите домашнее задание по предмету {subject['subject']}", reply_markup=markup)
        await state.set_state(HomeworkState.waiting_for_homework_entry)
    elif action == "Узнать д/з":
        # Получаем домашнее задание из базы данных
        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute("SELECT text, sender, username, timestamp FROM homework WHERE user_id = ? AND subject = ?", (user_id, subject['subject'])) as cursor:
                homework = await cursor.fetchone()
        if homework:
            text, sender, username, timestamp = homework
            await message.answer(
                f"Домашнее задание по предмету {subject['subject']}: {text}\n"
                f"Отправлено: {sender} (Username: {username})\n"
                f"Дата: {datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y')}, Время: {datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M')}"
            )
        else:
            await message.answer(f"Домашнее задание по предмету {subject['subject']} отсутствует.")


@router.message(HomeworkState.waiting_for_homework_entry)
async def process_homework_entry(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    homework_text = message.text
    subject = await state.get_data()

    if homework_text.lower() == "отмена":
        await state.clear()
        await db_helper.show_choose_class_menu(message)
        return

    # Сохраняем домашнее задание в базе данных
    timestamp = time.time()
    async with aiosqlite.connect('bot_data.db') as db:
        await db.execute(
            "INSERT OR REPLACE INTO homework (user_id, subject, text, sender, username, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, subject['subject'], homework_text, await db_helper.get_user_full_name(user_id), f"@{message.from_user.username}", timestamp)
        )
        await db.commit()

    await message.answer(f"Домашнее задание по предмету {subject['subject']} успешно записано.")
    await state.clear()
    await db_helper.show_choose_class_menu(message)