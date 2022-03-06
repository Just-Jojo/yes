from __future__ import annotations

import asyncio
import json
import logging.handlers
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Type, TypeVar, Union

import discord as discord  # discord tbh
from databases import Database
from discord.ext import commands  # type:ignore

import config
import statements
from utils import Context

log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)
CTX = TypeVar("CTX")
extensions: List[str] = [f"cogs.{ext}" for ext in ("general", "blacklist")]


@contextmanager
def init_logging():
    try:
        logging.getLogger("discord").setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.WARNING)
        logging.getLogger("discord.gateway").setLevel(logging.WARNING)
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            filename="yesbot.log", maxBytes=1_000_000, encoding="utf-8", mode="w"
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        fmt = logging.Formatter("[{asctime}] [{levelname}] {name}: {message}", dt_fmt, style="{")
        handler.setFormatter(fmt)
        log.addHandler(handler)
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(fmt)
        log.addHandler(stdout)
        yield
    finally:
        handlers = log.handlers[:]
        for hndl in handlers:
            hndl.close()
            log.removeHandler(hndl)


class PrefixManager:
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.cursor = Database(f"sqlite:///{Path(__file__).parent}/data/prefixes.db")
        self._cache: Dict[int, List[str]] = {}
        self.loop.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.cursor.connect()
        await self.cursor.execute(statements.CREATE_PREFIX_TABLE)

    async def get_prefixes(self, guild_id: int) -> List[str]:
        if not self._cache.get(guild_id):
            data = await self.cursor.fetch_val(statements.SELECT_PREFIXES, {"guild_id": guild_id})
            if not data:
                return []
            self._cache[guild_id] = json.loads(data)
        return self._cache[guild_id]

    async def update_prefixes(self, guild_id: int, prefixes: List[str] = None) -> None:
        new = json.dumps(prefixes or [])
        async with self.cursor.transaction() as tr:
            await self.cursor.execute(
                statements.UPSERT_PREFIXES, {"prefixes": new, "guild_id": guild_id}
            )
            if prefixes:
                self._cache[guild_id] = prefixes
            else:
                self._cache.pop(guild_id, None)

    async def teardown(self):
        await self.cursor.disconnect()


class BlacklistManager:
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.cursor = Database(f"sqlite:///{Path(__file__).parent}/data/blacklist.db")
        self._cache: Dict[int, str] = {}
        self.loop.create_task(self.initialize())

    async def initialize(self):
        await self.cursor.connect()
        await self.cursor.execute(statements.CREATE_BLACKLIST_TABLE)
        await self.get_blacklist()

    async def get_blacklist(self, user_id: int = None) -> Dict[int, str]:
        if not user_id:
            if not self._cache: # starting up
                data = await self.cursor.fetch_all("SELECT user_id, reason FROM blacklist;")
                if not data:
                    return {}
                ret = {k: v for k, v in data}
                self._cache = ret
            return self._cache
        elif ret := self._cache.get(user_id):
            return {user_id: ret}
        data = await self.cursor.fetch_val(statements.SELECT_BLACKLIST, {"user_id": user_id})
        ret = {user_id: data}
        self._cache[user_id] = data
        return ret

    async def add_to_blacklist(self, users: Iterable[int], reason: str) -> None:
        async with self.cursor.transaction():
            for user in users:
                await self.cursor.execute(
                    statements.UPSERT_REASON, {"user_id": user, "reason": reason}
                )
                self._cache[user] = reason

    async def remove_from_blacklist(self, users: Iterable[int]) -> None:
        async with self.cursor.transaction():
            if not users:
                await self.cursor.execute("DROP TABLE blacklist")
                await self.cursor.execute(statements.CREATE_BLACKLIST_TABLE)
                self._cache = {}
                return
            for user in users:
                await self.cursor.execute(
                    "DELETE FROM blacklist WHERE user_id=:user_id", {"user_id": user}
                )
                self._cache.pop(user_id, None)


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
            ret =commands.when_mentioned_or(*base)(
                bot, msg
            )  # Always gonna have the bot mention as a prefix :D
            log.info(ret)
            return ret

        super().__init__(_prefix, help_command=None)
        for ext in extensions:
            try:
                self.load_extension(ext)
            except commands.ExtensionFailed as e:
                log.exception("Failed to load extension %s", ext, exc_info=e)
        self.blacklist_manager = BlacklistManager(self.loop)

    async def shutdown(self):
        await self.prefix_manager.teardown()
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

    async def change_prefixes(self, ctx: Context, prefixes: List[str] = None):
        await self.prefix_manager.update_prefixes(ctx.guild.id, prefixes)

    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        elif msg.author.id in await self.blacklist_manager.get_blacklist():
            return
        log.info("Processing commands")
        await self.process_commands(msg)

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
            log.exception("Error in command '%s'", ctx.command.name, exc_info=exception)

    async def start(self, *args, **kwargs) -> None:
        await super().start(config.token, reconnect=True)


if __name__ == "__main__":
    with init_logging():
        bot = Bot()
        bot.run()
