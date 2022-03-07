# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands  # type:ignore

if TYPE_CHECKING:
    from ..bot import Bot


class Context(commands.Context):
    """An extension of discord.ext.commands.Context"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if TYPE_CHECKING:
            bot: Bot

    async def tick(self, *, check: bool = True) -> bool:
        emoji = "\N{WHITE HEAVY CHECK MARK}" if check else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            return False
        else:
            return True

    async def show_help(self, command: Optional[commands.Command] = None) -> None:
        """A wrapper for bot's send help"""
        command = command or self.command
        await self.bot.show_help(self, command)

    send_help = show_help  # I forgot about this

    async def maybe_send_embed(
        self,
        msg: str,
        *,
        title: Optional[str] = discord.embeds.EmptyEmbed,
        use_title: bool = False,
    ) -> discord.Message:
        if self.guild and not self.channel.permissions_for(ctx.me).embed_links:
            msg = msg if not use_title or not title else f"**{title}**\n{msg}"
            return await self.send(msg)
        return await self.send(embed=discord.Embed(title=title, description=msg, colour=0x00FFFF))


__all__ = ["Context"]
