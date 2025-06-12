import typing as t

from discord.ext import commands
from discord.utils import escape_markdown

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
    async def mdlink(
        self,
        ctx: commands.Context,
        plain: t.Optional[t.Literal["plain", "p", "mobile", "m"]] = None,
        *,
        text: str = "ModMail",
    ) -> None:
        """Return a link to the modmail thread in markdown syntax."""
        link = await self.bot.api.get_log_link(ctx.channel.id)
        if plain:
            await ctx.send(escape_markdown(f"[{text}]({link})", as_needed=True, ignore_links=False))
        else:
            await ctx.send(f"`[{text}]({link})`")


async def setup(bot: ModmailBot) -> None:
    """Add the MDLink plugin."""
    await bot.add_cog(MDLink(bot))
