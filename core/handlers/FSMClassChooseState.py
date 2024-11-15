from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from core.settings import get_settings

from database.db_helper import db_helper
from user_classes import *

import aiosqlite
import time

router = Router()

@router.message(F.text == '9А')
async def show_9A_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    user_class_name = await db_helper.get_user_class_name(user_id)

    if user_class_name == '9a' or user_class_name == 'general':
        await db_helper.show_9a_main_menu(message, state)
    else:
        await message.answer('Вы не состоите в 9А классе')

@router.message(F.text == '9Б')
async def show_9A_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    user_class_name = await db_helper.get_user_class_name(user_id)

    if user_class_name == '9b' or user_class_name == 'general':
        await db_helper.show_9b_main_menu(message, state)
    else:
        await message.answer('Вы не состоите в 9Б классе')