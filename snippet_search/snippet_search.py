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
    @commands.command()
    async def tag(self, ctx: commands.Context, *, query: Optional[str] = None) -> None:
        """
        Search for a snippet.
        """
        if not self.bot.snippets:
            embed = discord.Embed(
                color=self.bot.error_color,
                description="You dont have any snippets at the moment.",
            )
            embed.set_footer(
                text=f'Check "{self.bot.prefix}help snippet add" to add a snippet.'
            )
            embed.set_author(name="Snippets", icon_url=ctx.guild.icon_url)
            return await ctx.send(embed=embed)

        if query is None:
            snippets = self.bot.snippets
        else:
            snippets = {k: v for k, v in self.bot.snippets if query.lower() in k}

        embeds = []

        for name, val in snippets.items():
            description = f"{name}\n\n{truncate(escape_code_block(val), 2048 - 7)}"
            embed = discord.Embed(color=self.bot.main_color, description=description)
            embed.set_author(name="Snippets", icon_url=ctx.guild.icon_url)
            embeds.append(embed)

        session = EmbedPaginatorSession(ctx, *embeds)
        await session.run()


def setup(bot: ModmailBot) -> None:
    """Add the SnippetSearch cog to the bot."""
    bot.add_cog(SnippetSearch(bot))
