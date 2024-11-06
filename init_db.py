import aiosqlite

import asyncio

from database.db_helper import db_helper

async def init():
    await db_helper.initialize_database()

asyncio.run(init())