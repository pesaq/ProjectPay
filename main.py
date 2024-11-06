from aiogram import Bot, Dispatcher
import asyncio
from core.settings import get_settings

from core.handlers.FSMAddUserState import router as AddUserStateRouter
from core.handlers.basic import router as BasicRouter
from core.handlers.FSMDiaryState import router as DiaryRouter
from core.handlers.FSMArithmeticState import router as ArithmeticRouter
from core.handlers.FSMInfoState import router as InfoRouter
from core.handlers.FSMHomeworkState import router as HomeworkRouter
from core.handlers.FSMDeleteUserState import router as DeleteUserRouter

async def start():
    
    settings = get_settings('.env')

    bot = Bot(token=settings.bots.bot_token)
    dp = Dispatcher()

    dp.include_router(AddUserStateRouter)
    dp.include_router(BasicRouter)
    dp.include_router(DiaryRouter)
    dp.include_router(ArithmeticRouter)
    dp.include_router(InfoRouter)
    dp.include_router(HomeworkRouter)
    dp.include_router(DeleteUserRouter)

    try:
        await dp.start_polling(bot)
    finally:
        bot.session.close()

if __name__ == '__main__':
    asyncio.run(start())