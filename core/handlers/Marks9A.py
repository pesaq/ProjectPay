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

subjects = subjects[:-1]

# Функция для расчета среднего арифметического, исключая нечисловые значения
async def calculate_mean(scores):
    numeric_scores = [score for score in scores if isinstance(score, (int, float))]
    return sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0

class Marks9AState(StatesGroup):
    marks_action = State()

@router.message(lambda message: message.text == "Оценки (9А)")
async def student_grades_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    user_class = await db_helper.get_user_class(user_id=message.from_user.id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute("SELECT type FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            user_type = await cursor.fetchone()
            if user_type:
                user_type = user_type[0]
            
            if user_type == "teacher":
                markup = types.ReplyKeyboardMarkup(keyboard=[
                    [
                        types.KeyboardButton(
                            text='Редактировать оценки (9А)'
                        ),
                        types.KeyboardButton(
                            text='Назад'
                        )
                    ]
                ], resize_keyboard=True)
            elif user_type == "student":
                markup = types.ReplyKeyboardMarkup(keyboard=[
                    [
                        types.KeyboardButton(
                            text='Посмотреть оценки (9А)'
                        ),
                        types.KeyboardButton(
                            text='Назад'
                        )
                    ]
                ], resize_keyboard=True)
        
        await message.answer('Выберите действие:', reply_markup=markup)
        await state.set_state(Marks9AState.marks_action)


@router.message(Marks9AState.marks_action, lambda message: message.text == "Назад")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await db_helper.show_9a_main_menu(message, state)

# Функция для форматирования оценок, введенных подряд
def format_grades(grades_text):
  formatted_grades = ', '.join(re.findall(r'\d+|[^\d\s]', grades_text))
  return formatted_grades

class EditMarks9AState(StatesGroup):
    choosing_user = State()
    choosing_subject = State()
    choosing_action = State()
    choosing_mark = State()

# Обработка команды изменения оценок
@router.message(lambda message: message.text == "Редактировать оценки (9А)")
async def edit_user_mark_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return    
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute("SELECT type FROM users WHERE user_id=?", (message.from_user.id,)) as cursor:
            user_type = await cursor.fetchone()
    
            if user_type:
                user_type = user_type[0]
            # Проверяем права доступа пользователя
            if user_type == "teacher":
                try:
                    async with aiosqlite.connect('bot_data/bot_data.db') as db:
                        async with db.execute(
                            "SELECT user_id, name, COALESCE(username, 'отсутствует') as username FROM users WHERE type = ? AND role IN (?, ?, ?) AND class_name = ?",
                            ("student", USER, ADMIN, OWNER, '9a')
                        ) as cursor:
                            available_users = await cursor.fetchall()

                    if not available_users:
                        await message.reply("Нет доступных пользователей.")
                        return

                    buttons = []
                    row = []

                    for user in available_users:
                        row.append(types.InlineKeyboardButton(
                            text=user[1],
                            callback_data=f"marks_user_{user[0]}"
                        ))

                        if len(row) == 1:  # Когда в ряду 3 кнопки
                            buttons.append(row)
                            row = []  # Сбросить ряд

                    if row:  # Добавить оставшиеся кнопки, если они есть
                        buttons.append(row)

                    buttons.append([
                        types.InlineKeyboardButton(
                            text="Отмена",
                            callback_data="cancel_edit"
                        )
                    ])

                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
                    await state.set_state(EditMarks9AState.choosing_user)
                    await message.answer("Выберите ученика 9А для изменения оценки:", reply_markup=keyboard)

                except aiosqlite.Error as e:
                    await message.reply("Произошла ошибка при получении списка пользователей. Пожалуйста, попробуйте позже.")
                    print(f"Ошибка базы данных при получении пользователей для удаления: {e}")

# Обработка выбора пользователя или администратора для удаления
@router.callback_query(
    lambda c: c.data and (c.data.startswith('marks_user_')),
    EditMarks9AState.choosing_user
)
async def process_edit_mark_user(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id_to_edit = int(callback_query.data.split('_')[2])
        is_admin = callback_query.data.startswith('marks_user_')

        await state.update_data(user_id_to_edit=user_id_to_edit, is_admin=is_admin)
        
        keyboard_buttons = [[types.KeyboardButton(text=subject) for subject in subjects[i:i + 2]] for i in range(0, len(subjects), 2)]
        markup = types.ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            async with db.execute(
                "SELECT name, COALESCE(username, 'отсутствует') FROM users WHERE user_id = ?",
                (user_id_to_edit,)
            ) as cursor:
                user_data = await cursor.fetchone()

        user_name, username = user_data if user_data else ("Unknown", "Unknown")
        await callback_query.message.answer(
            f"По какому предмету вы хотите изменить оценку пользователю {user_name} (Username: @{username})?",
            reply_markup=markup
        )
        await state.set_state(EditMarks9AState.choosing_subject)
    except aiosqlite.Error as e:
        await callback_query.message.edit_text("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте позже.")
        print(f"Ошибка базы данных при обработке выбора пользователя для удаления: {e}")
    except Exception as e:
        await callback_query.message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Необработанное исключение при обработке выбора пользователя для удаления: {e}")

@router.message(EditMarks9AState.choosing_subject, lambda message: message.text != "Назад")
async def get_choosing_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject_to_edit=message.text)

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text='Добавить оценку',
                callback_data='action_add'
            ),
            types.InlineKeyboardButton(
                text='Удалить оценку',
                callback_data='action_del'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Другой предмет',
                callback_data='cancel_action'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Назад',
                callback_data='back_to_menu_9a'
            )
        ]
    ])

    await message.answer('Выберите действие с оценками:', reply_markup=keyboard)
    await state.set_state(EditMarks9AState.choosing_action)

@router.callback_query(lambda c: c.data.startswith('action_'), EditMarks9AState.choosing_action)
async def confirm_delete_user(callback_query: types.CallbackQuery, state: FSMContext):
    selected_action = callback_query.data.split('_')[1]
    data = await state.get_data()
    user_id_to_edit = data['user_id_to_edit']
    subject_to_edit = data['subject_to_edit']
    if selected_action == 'add':
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
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text='Назад',
                    callback_data='cancel_mark'
                )
            ]
        ])
        await callback_query.message.answer('Выберите оценку, которую вы хотите поставить:', reply_markup=keyboard)
        await state.set_state(EditMarks9AState.choosing_mark)
    elif selected_action == 'del':
        async with aiosqlite.connect('bot_data/bot_data.db') as db:
            async with db.execute("SELECT grades FROM marks WHERE subject_name = ? AND user_id = ?", (subject_to_edit, user_id_to_edit)) as cursor:
                marks_data = await cursor.fetchone()
                marks_data = marks_data[0]
                marks_data = list(mark for mark in marks_data.split(','))
            if marks_data != ['']:
                buttons = []
                for i in range(0, len(marks_data), 7):
                    row = [
                        types.InlineKeyboardButton(
                            text=mark,
                            callback_data=f"mark_del_{mark}"
                        ) for mark in marks_data[i:i + 7]
                    ]
                    buttons.append(row)
                
                buttons.append([
                    types.InlineKeyboardButton(
                        text="Назад",
                        callback_data="cancel_del_mark"
                    )
                ])
                
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
                
                await callback_query.message.edit_text('Выберите оценку, которую хотите удалить:', reply_markup=keyboard)
                await state.set_state(EditMarks9AState.choosing_mark)
            else:
                await callback_query.message.answer('У ученика нету оценок по этому предмету')

@router.callback_query(lambda c: c.data.startswith('num_'), EditMarks9AState.choosing_mark)
async def set_mark(callback_query: types.CallbackQuery, state: FSMContext):
    selected_mark = callback_query.data.split('_')[1]
    data = await state.get_data()
    user_id = data['user_id_to_edit']
    subject_name = data['subject_to_edit']
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
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

@router.callback_query(lambda c: c.data.startswith('mark_del_'), EditMarks9AState.choosing_mark)
async def set_mark(callback_query: types.CallbackQuery, state: FSMContext):
    mark_to_delete = callback_query.data.split('_')[2]
    data = await state.get_data()
    user_id_to_edit = data['user_id_to_edit']
    subject_to_edit = data['subject_to_edit']

    async with aiosqlite.connect('bot_data/bot_data.db') as db:
        async with db.execute("SELECT grades FROM marks WHERE user_id = ? AND subject_name = ?", (user_id_to_edit, subject_to_edit)) as cursor:
            row = await cursor.fetchone()

        if row:
            grades = row[0].split(',')
            count = 0
            new_grades = []

            for grade in grades:
                if grade == mark_to_delete and count == 0:
                    count += 1  # Удаляем только первую найденную оценку
                else:
                    new_grades.append(grade)

            # Обновляем строку с новыми оценками
            new_grades_str = ','.join(new_grades)
            await db.execute("UPDATE marks SET grades = ? WHERE user_id = ? AND subject_name = ?", (new_grades_str, user_id_to_edit, subject_to_edit))
            await db.commit()
            async with aiosqlite.connect('bot_data/bot_data.db') as db:
                async with db.execute("SELECT grades FROM marks WHERE subject_name = ? AND user_id = ?", (subject_to_edit, user_id_to_edit)) as cursor:
                    marks_data = await cursor.fetchone()
                    marks_data = marks_data[0]
                    marks_data = list(mark for mark in marks_data.split(','))
                if marks_data != ['']:
                    buttons = []
                    for i in range(0, len(marks_data), 7):
                        row = [
                            types.InlineKeyboardButton(
                                text=mark,
                                callback_data=f"mark_del_{mark}"
                            ) for mark in marks_data[i:i + 7]
                        ]
                        buttons.append(row)

                    buttons.append([
                        types.InlineKeyboardButton(
                            text="Отмена",
                            callback_data="cancel_del_mark"
                        )
                    ])

                    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.message.answer(f'Оценка {mark_to_delete} была удалена')
                else:
                    await callback_query.message.answer('У ученика нету оценок по этому предмету')

@router.message(lambda message: message.text == "Посмотреть оценки (9А)")
async def student_grades_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_class_name = await db_helper.get_user_class_name(user_id)
    if user_class_name != '9a' and user_class_name != 'general':
        await message.answer('Вы не состоите в 9А классе')
        return
    async with aiosqlite.connect('bot_data/bot_data.db') as db:
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
 
        # Формируем вывод для каждого предмета и его оценок
        output_messages = []
        for subject, grades_text in subjects:
            # Извлекаем все числовые оценки из строки для расчета среднего
            grades = [int(num) for num in re.findall(r'\d+', grades_text)]
            subject_mean = await calculate_mean(grades)

            # Формируем сообщение
            output_messages.append(f"<b>{subject}</b>: {grades_text}\nСредний балл: <b>{subject_mean:.2f}</b>\n")

        # Отправляем все сообщения в одном
        await message.answer("\n".join(output_messages), parse_mode=ParseMode.HTML)

@router.callback_query(EditMarks9AState.choosing_user, lambda c: c.data == 'cancel_edit')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Изменение отменено.", reply_markup=None)
        await state.clear()
        await db_helper.show_9a_main_menu(callback_query.message, state)
    except Exception as e:
        print(f"Необработанное исключение при отмене: {e}")

@router.callback_query(EditMarks9AState.choosing_action, lambda c: c.data == 'cancel_action')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    
    keyboard_buttons = [[types.KeyboardButton(text=subject) for subject in subjects[i:i + 2]] for i in range(0, len(subjects), 2)]
    markup = types.ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

    await callback_query.message.answer("Выберите предмет:", reply_markup=markup)
    await state.set_state(EditMarks9AState.choosing_subject)

@router.callback_query(EditMarks9AState.choosing_mark, lambda c: c.data == 'cancel_mark')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text='Добавить оценку',
                callback_data='action_add'
            ),
            types.InlineKeyboardButton(
                text='Удалить оценку',
                callback_data='action_del'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Другой предмет',
                callback_data='cancel_action'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Назад',
                callback_data='back_to_menu_9a'
            )
        ]
    ])

    await callback_query.message.answer('Выберите действие с оценками:', reply_markup=keyboard)
    await state.set_state(EditMarks9AState.choosing_action)

@router.callback_query(EditMarks9AState.choosing_mark, lambda c: c.data == 'cancel_del_mark')
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text='Добавить оценку',
                callback_data='action_add'
            ),
            types.InlineKeyboardButton(
                text='Удалить оценку',
                callback_data='action_del'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Другой предмет',
                callback_data='cancel_action'
            )
        ],
        [
            types.InlineKeyboardButton(
                text='Назад',
                callback_data='back_to_menu_9a'
            )
        ]
    ])

    await callback_query.message.answer('Выберите действие с оценками:', reply_markup=keyboard)
    await state.set_state(EditMarks9AState.choosing_action)

@router.callback_query(lambda c: c.data.startswith('back_to_menu_'))
async def cancel_to_9a_menu(callback_query: types.CallbackQuery, state: FSMContext):
    class_name_to_back = callback_query.data.split('_')[3]
    if class_name_to_back == '9a':
        await db_helper.show_9a_main_menu(callback_query.message, state)
    if class_name_to_back == '9b':
        await db_helper.show_9b_main_menu(callback_query.message, state)