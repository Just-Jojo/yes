# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

import asyncio

from databases import Database

from pathlib import Path

import discord as discord # Yes
from discord.ext import commands # type:ignore

CREATE_TABLE: str = """CREATE TABLE IF NOT EXISTS
    tags (
        name TEXT PRIMARY KEY,
        author_id INT NOT NULL,
    )
""".strip()


class TagCache:
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.cursor = Database(f"sqlite:///{Path(__file__).parent}/data/tags.db")
        self._cache: dict = {}
        self.loop.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.cursor.connect()
        await self.cursor.execute(CREATE_TABLE)
