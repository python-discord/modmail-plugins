from typing import Optional
import discord
from discord.ext import commands
from bot import ModmailBot
from core import checks
from core.models import PermissionLevel
from core.paginator import EmbedPaginatorSession
from core.utils import truncate, escape_code_block
from collections import defaultdict, Counter
import re


WORD_PATTERN = re.compile(r"[a-zA-Z]+")
THRESHOLD = 1.0


def score(query, name, content):
    if query is None:
        return THRESHOLD
    return (
        (common_word_count(query, name) + common_word_count(query, content))
        / len(words(query))
    )


def words(s):
    return WORD_PATTERN.findall(s)


def common_word_count(s1, s2):
    return sum(
        (
            Counter(map(str.casefold, words(s1)))
            & Counter(map(str.casefold, words(s2)))
        ).values()
    )


def group_snippets_by_content(snippets: dict[str, str]) -> list[tuple[set[str], str]]:
    names_by_content = defaultdict(set)
    for name, content in snippets.items():
        names_by_content[content.strip()].add(name)
    grouped_snippets = []
    for group in names_by_content.values():
        name, *_ = group
        content = snippets[name]
        grouped_snippets.append((group, content))
    return grouped_snippets


class SnippetSearch(commands.Cog):
    """A plugin that provides a command for searching snippets."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.command(name="snippetsearch")
    async def snippet_search(
        self, ctx: commands.Context, *, query: Optional[str] = None
    ) -> None:
        """
        Search for a snippet.
        """
        grouped_snippets = group_snippets_by_content(self.bot.snippets)

        scored_groups = []
        for i, (names, content) in enumerate(grouped_snippets):
            group_score = max(score(query, name, content) for name in names)
            scored_groups.append((group_score, i, names, content))

        scored_groups.sort(reverse=True)

        matching_snippet_groups = [
            (names, content)
            for group_score, _, names, content in scored_groups
            if group_score >= THRESHOLD
        ]

        if not matching_snippet_groups:
            embed = discord.Embed(
                description="No matching snippets found.",
                color=self.bot.error_color,
            )
            await ctx.send(embed=embed)
            return

        result_summary_embed = discord.Embed(
            color=self.bot.main_color,
            title=f"Found {len(matching_snippet_groups)} Matching Snippet{'s' if len(matching_snippet_groups) > 1 else ''}:",
            description=", ".join(
                "/".join(f"`{name}`" for name in sorted(names))
                for names, content in matching_snippet_groups
            ),
        )

        await ctx.send(embed=result_summary_embed)

        embeds = []

        for names, content in matching_snippet_groups:
            formatted_content = (
                f"```\n{truncate(escape_code_block(content), 1000)}\n```"
            )
            embed = (
                discord.Embed(
                    color=self.bot.main_color,
                )
                .add_field(
                    name=f"Name{'s' if len(names) > 1 else ''}",
                    value=",".join(f"`{name}`" for name in sorted(names)),
                    inline=False,
                )
                .add_field(
                    name="Raw Content",
                    value=formatted_content,
                    inline=False,
                )
            )
            embeds.append(embed)

        session = EmbedPaginatorSession(ctx, *embeds)
        await session.run()


def setup(bot: ModmailBot) -> None:
    """Add the SnippetSearch cog to the bot."""
    bot.add_cog(SnippetSearch(bot))
