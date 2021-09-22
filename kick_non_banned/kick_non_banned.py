import discord
from discord.ext import commands

PYDIS_MOD_ROLES = (
    267627879762755584,  # Owners
    267628507062992896,  # Admins
    267629731250176001,  # Moderation Team
)


class KickNonBanned(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Kick members who join appeal server, but are in main server."""
        if py_dis_member := self.bot.modmail_guild.get_member(member.id):
            if not any(role.id in PYDIS_MOD_ROLES for role in py_dis_member.roles):
                await member.kick(reason="Not banned in main server")


def setup(bot):
    bot.add_cog(KickNonBanned(bot))
