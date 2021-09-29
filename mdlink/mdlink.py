from discord.ext import commands

from bot import ModmailBot
from core import checks
from core.models import PermissionLevel


class MDLink(commands.Cog):
    """A plugin to get a link to the modmail thread using MD syntax."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    @checks.thread_only()
    async def mdlink(self, ctx: commands.Context, *, text: str = "ModMail") -> None:
        """Return a link to the modmail thread in markdown syntax."""
        link = await self.bot.api.get_log_link(ctx.channel.id)
        await ctx.send(f"`[{text}]({link})`")


def setup(bot: ModmailBot) -> None:
    """Add the MDLink plugin."""
    bot.add_cog(MDLink(bot))
