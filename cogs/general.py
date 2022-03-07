# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import Context

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger("general")


class General(commands.Cog):
    """General commands"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self._task = self.bot.loop.create_task(self._init())

    def cog_unload(self) -> None:
        self._task.cancel()

    @commands.command(name="ping")
    async def ping(self, ctx: Context):
        """Pong."""
        await ctx.send("Pong tbh.")

    @commands.command()
    @commands.is_owner()
    async def show_prefix(self, ctx: Context):
        await ctx.send(await self.bot.get_prefixes(ctx))

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx: Context):
        await ctx.send("Okay, I'm shutting down")
        await self.bot.shutdown()

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Bot is online tbh imo fr")

    @commands.command()
    @commands.is_owner()
    async def sync_commands(self, ctx: Context):
        await self.bot.tree.sync(guild=ctx.guild)
        await ctx.tick()

    @commands.command()
    @commands.is_owner()
    async def change_avatar_url(self, ctx: Context):
        if not ctx.message.attachments:
            return await ctx.send("no, fuck you")
        data = await ctx.message.attachments[0].read()
        await self.bot.user.edit(avatar=data)
        await ctx.tick()

    async def _init(self) -> None:
        await self.bot.wait_until_ready()
        await self.bot.tree.sync()


def setup(bot: Bot):
    bot.add_cog(General(bot))
