from typing import Optional

from discord.ext import commands

from core import checks
from core.models import PermissionLevel


class Tagging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.command()
    async def tag(self, ctx, tag: Optional[str]):
        """
        Append a tag at the beginning of the channel name.
        Using the command without any argument will reset it.
        """
        clean_name = ctx.channel.name.split("｜", maxsplit=1)[-1]

        if tag:
            name = f"{tag}｜{clean_name}"
        else:
            name = clean_name

        await ctx.channel.edit(name=name)
        await ctx.message.add_reaction("\u2705")


def setup(bot):
    bot.add_cog(Tagging(bot))
