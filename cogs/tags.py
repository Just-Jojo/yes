# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

import asyncio

from databases import Database

from pathlib import Path

import discord
from discord.ext import commands # type:ignore
from dataclasses import dataclass 

from typing import TYPE_CHECKING, Optional
import logging

from utils import Context

if TYPE_CHECKING:
    from bot import Bot


CREATE_TABLE: str = """CREATE TABLE IF NOT EXISTS
    tags (
        name TEXT PRIMARY KEY,
        author_id INT NOT NULL,
        guild_id INT NOT NULL,
        response TEXT NOT NULL
    )
""".strip()
SELECT_TAG: str = "SELECT author_id, response FROM tags WHERE name=:name AND guild_id=:guild_id"
INSERT_TAG: str = """INSERT INTO
tags
    (name, author_id, response, guild_id)
VALUES
    (:name, :author_id, :response, :guild_id)
"""

log = logging.getLogger("tags")


class TagManager:
    """Manager class for tags"""

    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.cursor = Database(f"sqlite:///{Path(__file__).parent.parent}/data/tags.db")
        self._cache: dict = {}
        self.loop.create_task(self.initialize())

    async def initialize(self) -> None:
        await self.cursor.connect()
        await self.cursor.execute(CREATE_TABLE)
        try:
            data = await self.cursor.fetch_all("SELECT name, guild_id, author_id, response FROM tags;")
        except Exception as e:
            log.exception("Could not get data", exc_info=e)
            return
        if not data:
            return
        keys = ("author_id", "response")
        for payload in data:
            payload = list(payload)
            name = payload.pop(0)
            guild_id = payload.pop(0)
            self._cache[(name, guild_id)] = {k: v for k, v in zip(keys, payload)}

    async def get_tag(self, name: str, guild_id: int) -> Optional[dict]:
        if not self._cache.get((name, guild_id)):
            data = await self.cursor.fetch_one(SELECT_TAG, {"name": name, "guild_id": guild_id})
            if not data:
                return None
            self._cache[(name, guild_id)] = {k: v for k, v in zip(("author_id", "response"), data)}
            log.debug(f"{self._cache = }")
        return self._cache[(name, guild_id)]

    async def save_tag(self, name: str, author_id: int, response: str, guild_id: int) -> None:
        async with self.cursor.transaction():
            await self.cursor.execute(
                INSERT_TAG, {"name": name, "author_id": author_id, "response": response, "guild_id": guild_id}
            )
        self._cache[(name, guild_id)] = {"author_id": author_id, "response": response}

    async def delete_tag(self, name: str, guild_id: int) -> None:
        async with self.cursor.transaction():
            await self.cursor.execute(
                "DELETE FROM tags WHERE name=:name AND guild_id=:guild_id",
                {"name": name, "guild_id": guild_id},
            )
        self._cache.pop((name, guild_id), None)


class Tags(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tag_manager = TagManager(self.bot.loop)
        self._blacklist_names = ["create"]

    @commands.group(name="tag", invoke_without_command=True)
    @commands.guild_only()
    async def tag(self, ctx: Context, tag_name: str):
        data = await self.tag_manager.get_tag(tag_name, ctx.guild.id)
        if not data:
            # Assume that they misspelled a subcommand
            return await ctx.show_help()
        await ctx.send(data["response"])

    @tag.command(name="create")
    @commands.guild_only()
    async def tag_create(self, ctx: Context, name: str, *, response: str):
        if name in self._blacklist_names:
            # Some names are gonna be subcommands so like, don't allow them :kappa:
            return await ctx.send("That tag name is reserved (probably for subcommands)")
        if await self.tag_manager.get_tag(name, ctx.guild.id):
            return await ctx.send("That tag already exists.")
        await self.tag_manager.save_tag(name, ctx.author.id, response, ctx.guild.id)
        await ctx.tick()

    @tag.command(name="delete")
    @commands.guild_only()
    async def tag_delete(self, ctx: Context, name: str):
        tag = await self.tag_manager.get_tag(name, ctx.guild.id)
        if not tag:
            return await ctx.send("I could not find that tag.")
        if tag["author_id"] != ctx.author.id and not await self.bot.is_owner(ctx.author):
            return await ctx.send("You are not the author of that tag")
        await self.tag_manager.delete_tag(name, ctx.guild.id)
        await ctx.tick()


def setup(bot: Bot) -> None:
    bot.add_cog(Tags(bot))
