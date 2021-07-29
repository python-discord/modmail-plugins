import discord
from discord.ext import commands

from core import checks
from core.models import PermissionLevel


class MDLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    @checks.thread_only()
    async def mdlink(self, ctx, *, text="ModMail"):
        """Return a link to the modmail thread in markdown syntax."""
        link = await self.bot.api.get_log_link(ctx.channel.id)
        await ctx.send(f"`[{text}]({link})`")


def setup(bot):
    bot.add_cog(MDLink(bot))
