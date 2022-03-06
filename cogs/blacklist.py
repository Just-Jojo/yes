# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Union

import discord as discord  # Lmao
from discord.ext import commands  # type:ignore

from utils import Context
from utils.chat_formatting import pagify, box
import logging

if TYPE_CHECKING:
    from bot import Bot

log = logging.getLogger("blacklist")


class BlacklistPages:
    def __init__(self, blacklist: List[str]):
        self.pages = blacklist
        self.max_pages = len(self.pages)
        self.title = "Blacklist"

    def get_page(self, index: int) -> str:
        return self.pages[index]

    async def format_page(self, menu: BlacklistMenu, page: str) -> Union[str, discord.Embed]:
        ctx = menu.ctx
        footer = f"Page {menu.current_page + 1}/{self.max_pages}"
        if ctx.guild and not ctx.channel.permissions_for(ctx.me).embed_links:
            return f"**{self.title}**\n{box(page, 'yml')}\n{footer}"
        return discord.Embed(
            title=self.title,
            colour=0x00FFFF,
            description=box(page, "yml"),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        ).set_footer(text=footer)


class BlacklistMenu(discord.ui.View):
    def __init__(self, ctx: Context, source: BlacklistPages):
        self.ctx = ctx
        self.source = source
        self.current_page: int = 0
        self.msg: discord.Message = None
        super().__init__()

    async def show_checked_page(self, page_number: int) -> None:
        try:
            if self.source.max_pages > page_number >= 0:
                await self.show_page(page_number)
            elif self.source.max_pages <= page_number:
                await self.show_page(0)
            elif 0 > page_number:
                await self.show_page(self.source.max_pages - 1)
        except IndexError:
            pass

    async def show_page(self, page_number: int) -> None:
        page = self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        if not self.msg:
            self.msg = await self.ctx.send(**kwargs)
        await self.msg.edit(**kwargs)

    async def _get_kwargs_from_page(self, page: str) -> dict:
        data = await self.source.format_page(self, page)
        ret = {"view": self}
        if isinstance(data, str):
            ret["content"] = data
        else:
            ret["embed"] = data
        return ret

    async def start(self) -> None:
        await self.show_page(0)

    @discord.ui.button(emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", style=discord.ButtonStyle.gray)
    async def go_to_first_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_page(0)

    @discord.ui.button(emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.gray)
    async def go_to_previous_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_checked_page(self.current_page - 1)

    @discord.ui.button(emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.red)
    async def stop_pages(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.msg.delete()
        self.stop()

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.gray)
    async def go_to_next_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_checked_page(self.current_page + 1)

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", style=discord.ButtonStyle.gray)
    async def go_to_last_page(self, button: discord.ui.Button, inter: discord.Interaction):
        await self.show_checked_page(-1) # This is easier methinks


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
        users = {u.id for u in users}
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
        users = {user.id for user in users}
        await self.bot.blacklist_manager.remove_from_blacklist(users)
        await ctx.tick()

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx: Context):
        bl = await self.bot.blacklist_manager.get_blacklist()
        if not bl:
            return await ctx.send("There are no blacklisted users")
        msg = "Blacklisted Users:\n"
        msg += "\n".join(f"\t- {u_id}: {reason}" for u_id, reason in bl.items())
        source = BlacklistPages(pagify(msg))
        await BlacklistMenu(ctx, source).start()


def setup(bot: Bot):
    bot.add_cog(Blacklist(bot))
