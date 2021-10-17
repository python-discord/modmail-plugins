import typing as t

import discord

from core.models import getLogger

log = getLogger(__name__)


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
