from __future__ import annotations

import asyncio

import nextcord as discord # nextcord tbh
from nextcord.ext import commands # type:ignore
from databases import Database

from pathlib import Path
import json

from .utils import Context
import config
import statements
from typing import TYPE_CHECKING, List, Optional, TypeVar

import logging


log = logging.getLogger(__file__)
CTX = TypeVar("CTX")


class PrefixManager:
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.cursor = Database(f"sqlite:///{Path(__file__).parent}/data/prefixes.db")
        self.loop.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.cursor.connect()
        await self.cursor.execute(statements.CREATE_PREFIX_TABLE)

    async def get_prefixes(self, guild_id: int) -> List[str]:
        data = await self.cursor.fetch_val(statements.SELECT_PREFIXES, {"guild_id": guild_id})
        if not data:
            return []
        return json.loads(data)

    async def update_prefixes(self, guild_id: int, prefixes: List[str]) -> None:
        new = json.dumps(prefixes)
        await self.cursor.execute(
            statements.INSERT_OR_UPDATE_PREFIXES, {"prefixes": new, "guild_id": guild_id}
        )


class Bot(commands.Bot): # I doubt this bot will require sharding as this will be at most a semi-public bot tbh
    """A subclass of discord.ext.commands.Bot"""

    __author__ = "Jojo#7791"
    __version__ = "1.0.0.dev0"

    def __init__(self):
        self.prefix_manager = PrefixManager(self.loop)
        async def _prefix(bot: Bot, msg: discord.Message) -> List[str]:
            base = config.prefixes
            if msg.guild:
                prefixes = await self.prefix_manager()
                base = prefixes or base
            return commands.when_mentioned_or(base) # Always gonna have the bot mention as a prefix :D

        super().__init__(_prefix, help_command=None)

    async def get_context(self, message: discord.Message, cls=Context) -> CTX:
        return await super().get_context(message, cls=cls)

    async def show_help(self, ctx: Context, command: commands.Command) -> None:
        ...

    async def on_command_error(self, ctx: Context, exception: BaseException) -> None:
        if isinstance(exception, commands.CommandNotFound):
            pass # This is dumb af tbh imo fr
        elif isinstance(exception, commands.CheckFailure):
            pass # Don't need to tell them
        elif isinstance(exception, commands.BadArgument):
            if exception.args:
                await ctx.send(exception.args[0])
            else:
                await ctx.show_help() # TODO this function
        elif isinstance(exception, commands.NSFWChannelRequired):
            await ctx.send("Please run this command in an nsfw channel") # Idk if I'm gonna have nsfw stuff yet
        else:
            await ctx.send("I'm sorry! That command errored.")
            log.exception(f"Error in command '{ctx.command.name}'", exc_info=exception)
