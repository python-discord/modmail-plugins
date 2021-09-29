from discord.ext import commands

from bot import ModmailBot
from core import checks
from core import time
from core.models import PermissionLevel

CLOSING_MESSAGE = "Feel free to open a new thread if you need anything else."


class UserFriendlyTimeOnly(time.UserFriendlyTime):
    """A convertor class to convert user friendly time to a duration."""

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        """Convert the given argument to a user friendly time."""
        converted = await super().convert(ctx, argument)
        if converted.arg:
            raise commands.BadArgument(
                f'`{argument}` isn\'t a valid duration string.'
            )
        converted.arg = CLOSING_MESSAGE
        return converted


class CloseMessage(commands.Cog):
    """A plugin that adds a command to close a thread after a given period with a set message."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.close_command = self.bot.get_command('close')

    @commands.command(
        name="closemessage", aliases=("cm"),
        usage="[after]",
        help=f"Close the current thread with the message `{CLOSING_MESSAGE}`"
    )
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @checks.thread_only()
    async def close_message(self, ctx: commands.Context, *, after: str = '15m') -> commands.Command:
        """Close the thread after the given duration with the set message."""
        if after.isdigit():
            after = f'{after}m'
        after = await UserFriendlyTimeOnly().convert(ctx, after)
        return await self.close_command(ctx, after=after)


def setup(bot: ModmailBot) -> None:
    """Load the CloseMessage plugin."""
    bot.add_cog(CloseMessage(bot))
