import asyncio
import typing as t

import discord
from discord.ext import commands

from bot import ModmailBot
from core.models import getLogger
from core.thread import Thread

PYDIS_NO_KICK_ROLE_IDS = (
    267627879762755584,  # Owners in PyDis
    409416496733880320,  # DevOps in PyDis
)

APPEAL_NO_KICK_ROLE_ID = 890270873813139507  # Staff in appeals server

log = getLogger(__name__)

class BanAppeals(commands.Cog):
    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self._loaded = asyncio.Event()

        self._pydis_appeals_category_id = 890331800025563216  # The category in PyDis to move appeal threads to
        self.pydis_guild: t.Optional[discord.Guild] = None

        self._appeals_guild_id = 890261951979061298
        self.appeals_guild: t.Optional[discord.Guild] = None

        self.appeals_category: t.Optional[discord.CategoryChannel] = None

    async def wait_until_loaded(self) -> None:
        await self._loaded.wait()
    
    @commands.Cog.listener()
    async def on_plugins_ready(self):
        self.pydis_guild = self.bot.guild
        self.appeals_guild = self.bot.get_guild(self._appeals_guild_id)
        self.appeals_category = self.pydis_guild.get_channel(self._pydis_appeals_category_id)
        self._loaded.set()
        log.info("Plugin loaded, checking if there are people to kick.")

        await self._sync_kicks()
    
    async def _sync_kicks(self) -> None:
        """Iter through all members in appeals guild, kick them if they meet criteria."""
        for member in self.appeals_guild.members:
            await self._maybe_kick_user(member)

    async def _maybe_kick_user(self, member: discord.Member) -> None:
        """Kick members joining appeals if they are not banned, and not part of the bypass list."""
        if member.bot:
            return

        if not await self._is_banned_pydis(member):
            pydis_member = self.pydis_guild.get_member(member.id)
            if pydis_member and (
                any(role.id in PYDIS_NO_KICK_ROLE_IDS for role in pydis_member.roles)
                or APPEAL_NO_KICK_ROLE_ID in (role.id for role in member.roles)
            ):
                log.info("Not kicking %s as they have a bypass role", member)
                return
            await member.kick(reason="Not banned in main server")
            log.info("Kicked %s", member)
    
    async def _is_banned_pydis(self, member: discord.Member) -> bool:
        """See if the given member is banned in PyDis."""
        try:
            await self.pydis_guild.fetch_ban(member)
        except discord.errors.NotFound:
            return False
        return True

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Kick members who join appeal server, but are in main server."""
        await self.wait_until_loaded()

        if member.guild == self.pydis_guild:
            # Join event from PyDis
            # Kick them from appeals guild now they're back in PyDis
            if appeals_member := self.appeals_guild.get_member(member.id):
                await appeals_member.kick(reason="Rejoined PyDis")
                log.info("Kicked %s as they rejoined PyDis.", member)
        elif member.guild == self.appeals_guild:
            # Join event from the appeals server
            # Kick them if they are not banned and not part of the bypass list
            await self._maybe_kick_user(member)
    
    @commands.Cog.listener()
    async def on_thread_ready(
        self,
        thread: Thread,
        creator: discord.Member,
        category: discord.CategoryChannel,
        initial_message: discord.Message
    ) -> None:
        """If the new thread is for an appeal, move it to the appeals category."""
        await self.wait_until_loaded()
        if await self._is_banned_pydis(thread.recipient):
            await thread.channel.edit(category=self.appeals_category)


def setup(bot: ModmailBot):
    bot.add_cog(BanAppeals(bot))
