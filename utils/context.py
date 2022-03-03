from __future__ import annotations

import nextcord as discord

from nextcord.ext import commands # type:ignore
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..bot import Bot


class Context(commands.Context):
    """An extension of discord.ext.commands.Context"""
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

__all__ = ["Context"]
