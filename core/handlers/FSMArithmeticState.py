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

class ArithmeticState(StatesGroup):
    waiting_for_arithmetic_entry = State()

# Обработка кнопки "Среднее арифметическое"
@router.message(lambda message: message.text == "Среднее арифметическое")
async def handle_arithmetic(message: types.Message, state: FSMContext):
    user_class = await db_helper.get_user_class(message.from_user.id)
    if user_class is None or user_class == 'unregistered':
        await message.answer("У вас нет прав для выполнения этой команды. Пожалуйста, зарегистрируйтесь снова с помощью токена.")
        return
    keyboard = types.ReplyKeyboardMarkup(keyboard=[
        [
            types.KeyboardButton(
                text='Отмена'
            )
        ]
    ], resize_keyboard=True)
    await message.answer("Введите длинное число из цифр без пробелов для расчета среднего арифметического:", reply_markup=keyboard)
    await state.set_state(ArithmeticState.waiting_for_arithmetic_entry)

@router.message(lambda message: message.text == "Отмена", ArithmeticState.waiting_for_arithmetic_entry)
async def cancel_arithmetic(message: types.Message, state: FSMContext):
    await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()
    await db_helper.show_choose_class_menu(message)

@router.message(ArithmeticState.waiting_for_arithmetic_entry)
async def process_arithmetic(message: types.Message, state: FSMContext):
    try:
        digits = [int(d) for d in message.text if d.isdigit()]
        if not digits:
            raise ValueError("Ваш запрос должен содержать только цифры.")
        average = sum(digits) / len(digits)
        await message.answer(f"Среднее арифметическое цифр равно: {round(average, 2)}", reply_markup=types.ReplyKeyboardRemove())
    except ValueError:
        await message.answer("Пожалуйста, введите только слитное число. Это число автоматически разделится на цифры, из которых будет получено среднее арифметическое.")
    await state.clear()
    await db_helper.show_choose_class_menu(message)

class InfoState(StatesGroup):
    waiting_for_info_entry = State()