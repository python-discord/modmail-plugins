import discord
from discord.ext import commands

PYDIS_NO_KICK_ROLES = (
    267627879762755584,  # Owners
    409416496733880320,  # DevOps
)


class KickNonBanned(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def is_banned(guild, user) -> bool:
        try:
            await guild.fetch_ban(user)
        except discord.errors.NotFound:
            return False
        return True

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Kick members who join appeal server, but are in main server."""
        pydis_guild = self.bot.modmail_guild
        appeals_guild = self.bot.guild

        if member.guild == pydis_guild:
            # Join event from PyDis
            # Kick them from appeals guild now they're back in Pydis
            if appeals_member := appeals_guild.get_member(member.id):
                await appeals_member.kick(reason="Rejoined PyDis")
        elif member.guild == appeals_guild:
            # Join event from the appeals guild
            # Kick them from appeal server if:
            # - they're not banned from PyDis and not in PyDis
            # - they're not banned from PyDis, they're in PyDis and don't have a bypass role
            if not await self.is_banned(pydis_guild, member):
                pydis_member = pydis_guild.get_member(member.id)
                if pydis_member and any(role.id in PYDIS_NO_KICK_ROLES for role in pydis_member.roles):
                    return
                await member.kick(reason="Not banned in main server")


def setup(bot):
    bot.add_cog(KickNonBanned(bot))
