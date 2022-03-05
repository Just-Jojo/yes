# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Union

import nextcord as discord  # Lmao
from nextcord.ext import commands  # type:ignore

from utils import Context

if TYPE_CHECKING:
    from bot import Bot


class BlacklistPages:
    def __init__(self, blacklist: List[str]):
        self.pages = []
        self.max_pages = len(self.pages)
        self.title = "Blacklist"

    def get_page(self, index: int) -> str:
        return self.pages[index]

    async def format_page(self, menu: BlacklistMenu, page: str) -> Union[str, discord.Embed]:
        ctx = menu.ctx
        footer = f"Page {menu.current_page + 1}/{self.max_pages}"
        if ctx.guild and not ctx.channel.permissions_for(ctx.me).embed_links:
            return f"**{self.title}**\n{page}\n{footer}"
        return discord.Embed(
            title=self.title,
            colour=0x00FFFF,
            description=page,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        ).set_footer(text=footer)


class BlacklistMenu(discord.ui.View):
    def __init__(self, ctx: Context):
        self.ctx = ctx


class Blacklist(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.group()
    async def blacklist(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.show_help()

    @blacklist.command(name="add")
    async def blacklist_add(
        self, ctx: Context, users: commands.Greedy[discord.User], *, reason: str = None
    ):
        if not users:
            return await ctx.show_help()
        for user in users:
            if user == ctx.me:
                return await ctx.send("Oh, I see how it is")
            elif user.bot:
                return await ctx.send("That user is a bot")
            elif await self.bot.is_owner(user):
                return await ctx.send("If you don't wanna talk to me just don't talk to me")

        reason = reason or "No reason provided"
        await self.bot.blacklist_manager.add_to_blacklist(users, reason)
        await ctx.tick()

    @blacklist.command(name="remove", require_var_positional=True)
    async def blacklist_remove(self, ctx: Context, *users: discord.User):
        for user in users:
            if user == ctx.me:
                return await ctx.send("Bruh")
            elif user.bot:
                return await ctx.send("That user is a bot")
            elif await self.bot.is_owner(user):
                return await ctx.send("*angery noises\*")
        await self.bot.blacklist_manager.remove_from_blacklist(users)


def setup(bot: Bot):
    bot.add_cog(Blacklist(bot))
