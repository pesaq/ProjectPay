from aiogram import types, Bot

# Определение функции set_bot_commands
async def set_bot_commands(bot: Bot):
    commands = [
        types.BotCommand("start", "Начать работу с ботом"),
        types.BotCommand("help", "Получить помощь"),
        # Добавьте другие команды, если нужно
    ]
    await bot.set_my_commands(commands)