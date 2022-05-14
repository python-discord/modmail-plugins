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
                name: content
                for name, content in self.bot.snippets.items()
                if query.lower() in name
            }

        if not snippets:
            embed = discord.Embed(
                description="No matching snippets found.",
                color=self.bot.error_color,
            )
            await ctx.send(embed=embed)
            return

        result_summary_embed = discord.Embed(
            color=self.bot.main_color,
            title=f"{len(snippets)} Matching Snippet{'s' if len(snippets) > 1 else ''}",
            description=', '.join(f"`{name}`" for name in snippets),
        )

        embeds = []

        for i, (name, val) in enumerate(snippets.items(), start=1):
            content = truncate(escape_code_block(val), 2048 - 7)
            embed = (
                discord.Embed(
                    color=self.bot.main_color,
                    title="Snippet {i}",
                )
                .add_field(name="Name", value=f"`{name}`", inline=False)
                .add_field(name="Raw Content", value=f"```\n{content}\n```", inline=False)
            )
            embeds.append(embed)

        session = EmbedPaginatorSession(ctx, *embeds)
        await session.run()


def setup(bot: ModmailBot) -> None:
    """Add the SnippetSearch cog to the bot."""
    bot.add_cog(SnippetSearch(bot))
