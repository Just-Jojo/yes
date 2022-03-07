# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

import asyncio

from databases import Database

from pathlib import Path

import discord
from discord.ext import commands # type:ignore
from dataclasses import dataclass 
import datetime

from typing import TYPE_CHECKING, Optional, Union, Dict, Tuple, Any
import logging

from utils import Context
from utils.chat_formatting import pagify, box

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

    def __init__(self, bot: Bot, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.bot = bot
        self.cursor = Database(f"sqlite:///{self.bot.datapath}/tags.db")
        self._cache: Dict[Tuple[str, int], Dict[str, Any]] = {}
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
        # I could do this in one line but uh, no
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

    async def get_tags(self, guild_id: int) -> Optional[dict]:
        data = await self.cursor.fetch_all(
            "SELECT name, author_id, response FROM tags WHERE guild_id=:guild_id",
            {"guild_id": guild_id},
        )
        if not data:
            return None
        ret = {}
        for payload in data:
            p = list(payload)
            name = p.pop(0)
            ret[name] = {k: v for k, v in zip(("author_id", "response"), p)}
        return ret


class TagSource:
    def __init__(self, data: list):
        self.data = data
        self.max_pages = len(self.data)

    async def format_page(self, menu: TagMenu, page: str) -> Union[discord.Embed, str]:
        ctx = menu.ctx
        footer = f"Page {menu.current_page + 1}/{self.max_pages}"
        if ctx.guild and not ctx.channel.permissions_for(ctx.me).embed_links:
            return f"**Tags**\n\n{page}\n{footer}"
        return discord.Embed(
            title="Tags",
            description=page,
            colour=0x00ffff,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        ).set_footer(text=footer)

    def get_page(self, index: int) -> str:
        return self.data[index]


class TagMenu(discord.ui.View):
    def __init__(self, ctx: Context, source: TagSource):
        super().__init__()
        self.ctx = ctx
        self.source = source
        self.current_page: int = 0
        self.message: discord.Message = None

    async def on_timeout(self) -> None:
        await self.message.edit(view=None)

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if inter.user.id != self.ctx.author.id:
            await inter.response.send_message("Only the author of the command can interact with this", ephemeral=True)
            return False
        return True

    async def _get_kwargs_from_page(self, page: str) -> dict:
        data = await self.source.format_page(self, page)
        if isinstance(data, discord.Embed):
            return {"embed": data, "view": self}
        return {"content": data, "view": self}

    async def start(self) -> None:
        await self.show_page(0)

    async def show_checked_page(self, index: int) -> None:
        try:
            if self.source.max_pages > index >= 0:
                await self.show_page(index)
            elif self.source.max_pages <= index:
                await self.show_page(0)
            elif 0 > index:
                await self.show_page(self.source.max_pages - 1)
        except IndexError:
            pass

    async def show_page(self, index: int) -> None:
        page = self.source.get_page(index)
        self.current_page = index
        kwargs = await self._get_kwargs_from_page(page)
        if not self.message:
            self.message = await self.ctx.send(**kwargs)
            return
        await self.message.edit(**kwargs)

    @discord.ui.button(emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", style=discord.ButtonStyle.grey)
    async def go_to_first_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_page(0)

    @discord.ui.button(emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.grey)
    async def go_to_previous_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_checked_page(self.current_page - 1)

    @discord.ui.button(emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.red)
    async def stop_pages(self, button: discord.ui.Button, inter: discord.Interaction):
        self.stop()
        await self.message.delete()

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.grey)
    async def go_to_next_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_checked_page(self.current_page + 1)

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", style=discord.ButtonStyle.grey)
    async def go_to_last_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_checked_page(-1)


if TYPE_CHECKING:
    clean_content = str
else:
    clean_content = commands.clean_content

if TYPE_CHECKING:
    # Use type checking and just alias it as a string
    ValidTag = str
else:
    # This will be a class at runtime
    class ValidTag(commands.Converter):
        async def convert(self, ctx: Context, argument: str) -> str:
            argument = argument.lower()
            arg, *_ = argument.partition(" ")
            if len(arg) > 100:
                raise commands.BadArgument("Tag name is a maximum of 100 characters")

            tag_cmd: commands.Group = ctx.bot.get_command("tag")
            if arg in tag_cmd.all_commands:
                raise commands.BadArgument("That tag name is a reserved keyword")
            return arg


class Tags(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tag_manager = TagManager(self.bot, self.bot.loop)
        self._blacklist_names = ["create"]

    @commands.group(name="tag", invoke_without_command=True)
    @commands.guild_only()
    async def tag(self, ctx: Context, tag_name: str):
        tag_name, *_ = tag_name.lower().partition(" ")
        data = await self.tag_manager.get_tag(tag_name, ctx.guild.id)
        if not data:
            # Assume that they misspelled a subcommand
            return await ctx.show_help()
        await ctx.send(data["response"])

    @tag.command(name="create")
    @commands.guild_only()
    async def tag_create(self, ctx: Context, name: ValidTag, *, response: clean_content):
        if await self.tag_manager.get_tag(name, ctx.guild.id):
            return await ctx.send("That tag already exists.")
        await self.tag_manager.save_tag(name, ctx.author.id, response, ctx.guild.id)
        await ctx.tick()

    @tag.command(name="delete")
    @commands.guild_only()
    async def tag_delete(self, ctx: Context, name: ValidTag):
        tag = await self.tag_manager.get_tag(name, ctx.guild.id)
        if not tag:
            return await ctx.send("I could not find that tag.")
        if tag["author_id"] != ctx.author.id and not (await self.bot.is_owner(ctx.author) or ctx.guild.owner_id == ctx.author.id):
            return await ctx.send("You are not the author of that tag")
        await self.tag_manager.delete_tag(name, ctx.guild.id)
        await ctx.tick()

    @tag.command(name="list")
    @commands.guild_only()
    async def tag_list(self, ctx: Context):
        tags = await self.tag_manager.get_tags(ctx.guild.id)
        if not tags:
            return await ctx.send("This guild does not have any tags.")
        data = ""
        for key, value in tags.items():
            res = value["response"]
            if len(res) > 30:
                res = res[:30] + "..."
            data += f"{key}: {res}\n"
        source = TagSource(pagify(data))
        await TagMenu(ctx, source).start()


def setup(bot: Bot) -> None:
    bot.add_cog(Tags(bot))
