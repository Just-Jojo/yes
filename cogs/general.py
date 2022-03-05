# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

from typing import TYPE_CHECKING

import nextcord as discord
from nextcord.ext import commands

from utils import Context

import logging

if TYPE_CHECKING:
    from bot import Bot


log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)


class General(commands.Cog):
    """General commands"""

    def __init__(self, bot: Bot):
        self.bot = bot

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


def setup(bot: Bot):
    bot.add_cog(General(bot))
