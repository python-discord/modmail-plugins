from typing import Optional

from discord.ext import commands

from bot import ModmailBot
from core import checks
from core.models import PermissionLevel


class Tagging(commands.Cog):
    """A plugin that enables mods to prefix the thread name with a tag."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.command()
    @checks.thread_only()
    async def tag(self, ctx: commands.Context, *, tag: Optional[str]) -> None:
        """
        Append a tag at the beginning of the channel name.

        Using the command without any argument will reset it.
        """
        clean_name = ctx.channel.name.split("｜", maxsplit=1)[-1]

        if tag:
            name = f"{tag}｜{clean_name}"
        else:
            name = clean_name

        await ctx.reply(
            "Changes may take up to 10 minutes to take effect due to rate-limits."
        )
        await ctx.channel.edit(name=name)
        await ctx.message.add_reaction("\u2705")


def setup(bot: ModmailBot) -> None:
    """Add the Tagging plugin."""
    bot.add_cog(Tagging(bot))
