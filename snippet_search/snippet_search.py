from typing import Optional
import discord
from discord.ext import commands
from bot import ModmailBot
from core import checks
from core.models import PermissionLevel
from core.paginator import EmbedPaginatorSession
from core.utils import truncate, escape_code_block


class SnippetSearch(commands.Cog):
    """A plugin that provides a command for searching snippets."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.command(name="snippetsearch")
    async def snippet_search(self, ctx: commands.Context, *, query: Optional[str] = None) -> None:
        """
        Search for a snippet.
        """
        if query is None:
            snippets = self.bot.snippets
        else:
            snippets = {
                k: v
                for k, v in self.bot.snippets.items()
                if query.lower() in k
            }

        if not snippets:
            embed = discord.Embed(
                description="No snippets found.",
                color=self.bot.error_color,
            )
            await ctx.send(embed=embed)
            return

        embeds = []

        for name, val in snippets.items():
            content = truncate(escape_code_block(val), 2048 - 7)
            embed = (
                discord.Embed(
                    title=f'Snippets Found ({len(snippets)})',
                    color=self.bot.main_color,
                )
                .add_field(name="Name", value=f"`{name}`")
                .add_field(name="Raw Content", value=f"```\n{content}\n```")
            )
            embeds.append(embed)

        session = EmbedPaginatorSession(ctx, *embeds)
        await session.run()


def setup(bot: ModmailBot) -> None:
    """Add the SnippetSearch cog to the bot."""
    bot.add_cog(SnippetSearch(bot))
