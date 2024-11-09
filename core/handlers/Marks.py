import re
from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from aiogram.enums import ParseMode

from database.db_helper import db_helper

from user_classes import *

import aiosqlite

router = Router()

# Функция для расчета среднего арифметического, исключая нечисловые значения
async def calculate_mean(scores):
    numeric_scores = [score for score in scores if isinstance(score, (int, float))]
    return sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0

@router.message(lambda message: message.text == "Оценки")
async def student_grades_handler(message: types.Message):
    user_class = await db_helper.get_user_class(user_id=message.from_user.id)
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT type FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            user_type = await cursor.fetchone()
            if user_type:
                user_type = user_type[0]
            
            if user_type == "teacher":
                markup = types.ReplyKeyboardMarkup(keyboard=[
                    [
                        types.KeyboardButton(
                            text='Редактировать оценки'
                        ),
                        types.KeyboardButton(
                            text='Назад'
                        )
                    ]
                ])
            elif user_type == "student":
                markup = types.ReplyKeyboardMarkup(keyboard=[
                    [
                        types.KeyboardButton(
                            text='Посмотреть оценки'
                        ),
                        types.KeyboardButton(
                            text='Назад'
                        )
                    ]
                ])
        
        await message.answer('Выберите действие:', reply_markup=markup)



@router.message(lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_main_menu(message)

# Функция для форматирования оценок, введенных подряд
def format_grades(grades_text):
  formatted_grades = ', '.join(re.findall(r'\d+|[^\d\s]', grades_text))
  return formatted_grades

class EditMarksState(StatesGroup):
    choosing_user = State()
    choosing_subject = State()
    choosing_mark = State()

# Обработка команды изменения оценок
@router.message(lambda message: message.text == "Редактировать оценки")
async def edit_user_mark_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect('bot_data.db') as db:
        async with db.execute("SELECT type FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            user_type = await cursor.fetchone()
    
            if user_type:
                user_type = user_type[0]
            # Проверяем права доступа пользователя
            if user_type == "teacher":
                try:
                    async with aiosqlite.connect('bot_data.db') as db:
                        async with db.execute(
                            "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE type = ?",
                            ("student",)
                        ) as cursor:
                            available_users = await cursor.fetchall()

                    if not available_users:
                        await message.reply("Нет доступных пользователей.")
                        return

                    buttons = [
                        [
                            types.InlineKeyboardButton(
                                text=user[1],
                                callback_data=f"marks_user_{user[0]}"
                            ) for user in available_users
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="Отмена",
                                callback_data="cancel_edit"
                            )
                        ]
                    ]

                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
                    await state.set_state(EditMarksState.choosing_user)
                    await message.answer("Выберите пользователя для изменения оценки:", reply_markup=keyboard)

                except aiosqlite.Error as e:
                    await message.reply("Произошла ошибка при получении списка пользователей. Пожалуйста, попробуйте позже.")
                    print(f"Ошибка базы данных при получении пользователей для удаления: {e}")

# Обработка выбора пользователя или администратора для удаления
@router.callback_query(
    lambda c: c.data and (c.data.startswith('marks_user_')),
    EditMarksState.choosing_user
)
async def process_edit_mark_user(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id_to_edit = int(callback_query.data.split('_')[2])
        is_admin = callback_query.data.startswith('marks_user_')

        await state.update_data(user_id_to_edit=user_id_to_edit, is_admin=is_admin)
        keyboard_buttons = [[types.KeyboardButton(text=subject) for subject in subjects[i:i + 2]] for i in range(0, len(subjects), 2)]
        markup = types.ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

        async with aiosqlite.connect('bot_data.db') as db:
            async with db.execute(
                "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                (user_id_to_edit,)
            ) as cursor:
                user_data = await cursor.fetchone()

        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        await callback_query.message.answer(
            f"По какому предмету вы хотите поставить оценку пользователю {user_name} (Username: @{username})?",
            reply_markup=markup
        )
        await state.set_state(EditMarksState.choosing_subject)
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при обработке выбора пользователя для удаления: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при обработке выбора пользователя для удаления: {e}")

@router.message(EditMarksState.choosing_subject)
async def confirm_delete_user(message: types.Message, state: FSMContext):
    await state.update_data(subject_to_edit=message.text)
    data = await state.get_data()
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text='н',
                callback_data='num_H'
            ),
            types.InlineKeyboardButton(
                text='2',
                callback_data='num_2'
            ),
            types.InlineKeyboardButton(
                text='3',
                callback_data='num_3'
            ),
            types.InlineKeyboardButton(
                text='4',
                callback_data='num_4'
            ),
            types.InlineKeyboardButton(
                text='5',
                callback_data='num_5'
            )
        ]
    ])

    await message.answer('Выберите оценку, которую вы хотите поставить:', reply_markup=keyboard)
    await state.set_state(EditMarksState.choosing_mark)

@router.callback_query(lambda c: c.data.startswith('num_'), EditMarksState.choosing_mark)
async def set_mark(callback_query: types.CallbackQuery, state: FSMContext):
    selected_mark = callback_query.data.split('_')[1]
    data = await state.get_data()
    user_id = data['user_id_to_edit']
    subject_name = data['subject_to_edit']
    async with aiosqlite.connect('bot_data.db') as db:
        cursor = await db.execute("SELECT grades FROM marks WHERE subject_name = ? AND user_id = ?", (subject_name, user_id))
        current_grades = await cursor.fetchone()
        
        if current_grades:
            grades_str = current_grades[0]
        
            new_grades = grades_str + ',' + selected_mark if grades_str else selected_mark
            await db.execute("UPDATE marks SET grades = ? WHERE subject_name = ? AND user_id = ?", (new_grades, subject_name, user_id))
        else:
            await db.execute("INSERT INTO marks (subject_name, user_id, grades) VALUES (?, ?, ?)", (subject_name, user_id, selected_mark))

        await callback_query.message.answer(f'Оценка успешно выставлена: {selected_mark}')
    
        await db.commit()


@router.callback_query(lambda c: c.data == 'cancel_edit')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Изменение отменено.", reply_markup=None)
        await state.clear()
    except Exception as e:
        print(f"Необработанное исключение при отмене: {e}")


@router.message(lambda message: message.text == "Посмотреть оценки")
async def student_grades_handler(message: types.Message):
    async with aiosqlite.connect('bot_data.db') as db:
        cursor = await db.cursor()
 
        # Получаем список предметов и оценок для данного пользователя
        await cursor.execute("""
            SELECT subject_name, grades 
            FROM marks
            WHERE user_id = ?
        """, (message.from_user.id,))
        subjects = await cursor.fetchall()
 
        if not subjects:
            await message.answer("Нет данных об оценках.")
            return
 
        # Формируем текст для каждого предмета и его оценки в виде кода
        response_text = "Ваши оценки по предметам:\n\n"
        for subject, grades_text in subjects:
            # Извлекаем все числовые оценки из строки для расчета среднего
            grades = [int(num) for num in re.findall(r'\d+', grades_text)]
            subject_mean = await calculate_mean(grades)
 
            # Форматируем вывод для каждого предмета: оценки + среднее арифметическое
            response_text += f"`{subject}: {grades_text}`  <b>Средний балл: {subject_mean:.2f}</b>\n"
 
        # Отправляем сообщение с оценками
        await message.answer(response_text, parse_mode=ParseMode.HTML)
 
        # Сообщение о возвращении в главное меню
        await message.answer("Возвращение в главное меню...")
        await db_helper.show_main_menu(message)