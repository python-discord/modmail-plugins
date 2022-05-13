from typing import Optional
from discord.ext import commands
from bot import ModmailBot
from core import checks
from core.models import PermissionLevel


class SnippetSearch(commands.Cog):
    """A plugin that provides a command for searching snippets."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.command()
    async def tag(self, ctx: commands.Context, *, query: Optional[str]) -> None:
        """
        Search for a snippet.
        """
        ...


def setup(bot: ModmailBot) -> None:
    """Add the SnippetSearch cog to the bot."""
    bot.add_cog(SnippetSearch(bot))

