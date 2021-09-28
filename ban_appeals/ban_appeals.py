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

        self._pydis_appeals_category_id = 890331800025563216  # The category in PyDis to move appeal threads to
        self.pydis_guild: t.Optional[discord.Guild] = None

        self._appeals_guild_id = 890261951979061298
        self.appeals_guild: t.Optional[discord.Guild] = None
        self.logs_channel: t.Optional[discord.TextChannel] = None

        self.appeals_category: t.Optional[discord.CategoryChannel] = None

        self.init_task = asyncio.create_task(self.ensure_plugin_init())
    
    @staticmethod
    async def get_or_fetch_member(guild: discord.Guild, member_id: int) -> t.Optional[discord.Member]:
        """
        Attempt to get a member from cache; on failure fetch from the API.

        Return `None` to indicate the member could not be found.
        """
        if member := guild.get_member(member_id):
            log.debug("%s (%d) retrieved from cache.", member, member.id)
        else:
            try:
                member = await guild.fetch_member(member_id)
            except discord.errors.NotFound:
                log.debug("Failed to fetch %d from API.", member_id)
                return None
            log.debug("%s (%d) fetched from API.", member, member.id)
        return member
    
    @staticmethod
    async def get_or_fetch_channel(guild: discord.Guild, channel_id: int) -> t.Optional[discord.ChannelType]:
        """
        Attempt to get a channel from cache; on failure fetch from the API.

        Return `None` to indicate the channel could not be found.
        """
        if channel := guild.get_channel(channel_id):
            log.debug("%s retrieved from cache.", channel)
        else:
            channels = await guild.fetch_channels()
            channel = discord.utils.get(channels, id=channel_id)
            if channel:
                log.debug("%s fetched from API.", channel)
            else:
                log.debug("Failed to fetch %d from API.", channel_id)

        return channel

    async def ensure_plugin_init(self) -> None:
        self.pydis_guild = self.bot.guild
        self.appeals_guild = self.bot.get_guild(self._appeals_guild_id)
        self.appeals_category = await self.get_or_fetch_channel(self.pydis_guild, self._pydis_appeals_category_id)
        self.logs_channel = discord.utils.get(self.appeals_guild.channels, name="logs")

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
            pydis_member = await self.get_or_fetch_member(self.pydis_guild, member.id)
            if pydis_member and (
                any(role.id in PYDIS_NO_KICK_ROLE_IDS for role in pydis_member.roles)
                or APPEAL_NO_KICK_ROLE_ID in (role.id for role in member.roles)
            ):
                log.info("Not kicking %s (%d) as they have a bypass role", member, member.id)
                return
            try:
                await member.kick(reason="Not banned in main server")
            except discord.Forbidden:
                log.error("Failed to kick %s (%d)due to insufficient permissions.", member, member.id)
            await self.logs_channel.send(f"Kicked {member} ({member.id}) on join as they're not banned in main server.")
            log.info("Kicked %s (%d).", member, member.id)
    
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
        await self.init_task

        if member.guild == self.pydis_guild:
            # Join event from PyDis
            # Kick them from appeals guild now they're back in PyDis
            appeals_member = await self.get_or_fetch_member(self.appeals_guild, member.id)
            if appeals_member:
                await appeals_member.kick(reason="Rejoined PyDis")
                await self.logs_channel.send(f"Kicked {member} ({member.id}) as they rejoined PyDis.")
                log.info("Kicked %s (%d) as they rejoined PyDis.", member, member.id)
        elif member.guild == self.appeals_guild:
            # Join event from the appeals server
            # Kick them if they are not banned and not part of the bypass list
            await self._maybe_kick_user(member)
    
    @commands.Cog.listener()
    async def on_thread_ready(self, thread: Thread, *args) -> None:
        """If the new thread is for an appeal, move it to the appeals category."""
        await self.init_task

        if await self._is_banned_pydis(thread.recipient):
            await thread.channel.edit(category=self.appeals_category, sync_permissions=True)


def setup(bot: ModmailBot):
    bot.add_cog(BanAppeals(bot))
