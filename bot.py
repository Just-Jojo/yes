from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Type, TypeVar

import nextcord as discord  # nextcord tbh
from databases import Database
from nextcord.ext import commands  # type:ignore

import config
import statements
from utils import Context

log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)
CTX = TypeVar("CTX")
extensions: List[str] = [f"cogs.{ext}" for ext in ("general",)]


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

    async def teardown(self):
        await self.cursor.disconnect()


class Bot(
    commands.Bot
):  # I doubt this bot will require sharding as this will be at most a semi-public bot tbh
    """A subclass of discord.ext.commands.Bot"""

    __author__ = "Jojo#7791"
    __version__ = "1.0.0.dev0"

    def __init__(self):
        self.prefix_manager = PrefixManager()

        async def _prefix(bot: Bot, msg: discord.Message) -> List[str]:
            base = config.prefixes
            if msg.guild:
                prefixes = await self.prefix_manager.get_prefixes(msg.guild.id)
                base = prefixes or base
            return commands.when_mentioned_or(
                *base
            )(bot, msg)  # Always gonna have the bot mention as a prefix :D

        super().__init__(_prefix, help_command=None)
        for ext in extensions:
            try:
                self.load_extension(ext)
            except commands.ExtensionFailed as e:
                log.exception("Failed to load extension %s", ext, exc_info=e)

    async def shutdown(self):
        await self.close()
        sys.exit(0)

    async def get_context(self, message: discord.Message, *, cls: Type[CTX] = Context) -> CTX:
        return await super().get_context(message, cls=cls)

    async def show_help(self, ctx: Context, command: commands.Command) -> None:
        await ctx.send("This is coming soon tbh imo fr")

    async def get_prefixes(self, ctx: Context) -> List[str]:
        base = config.prefixes
        if ctx.guild:
            base = await self.prefix_manager.get_prefixes(ctx.guild.id) or base
        return base

    async def on_command_error(self, ctx: Context, exception: BaseException) -> None:
        if isinstance(exception, commands.CommandNotFound):
            pass  # This is dumb af tbh imo fr
        elif isinstance(exception, commands.CheckFailure):
            pass  # Don't need to tell them
        elif isinstance(exception, commands.BadArgument):
            if exception.args:
                await ctx.send(exception.args[0])
            else:
                await ctx.show_help()  # TODO this function
        elif isinstance(exception, commands.NSFWChannelRequired):
            await ctx.send(
                "Please run this command in an nsfw channel"
            )  # Idk if I'm gonna have nsfw stuff yet
        else:
            await ctx.send("I'm sorry! That command errored.")
            log.exception(f"Error in command '{ctx.command.name}'", exc_info=exception)

    async def start(self, *args, **kwargs) -> None:
        await super().start(config.token, reconnect=True)


if __name__ == "__main__":
    bot = Bot()
    bot.run()
