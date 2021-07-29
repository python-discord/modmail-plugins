from discord.ext import commands

from core import checks
from core import time
from core.models import PermissionLevel

CLOSING_MESSAGE = "Feel free to open a new thread if you need anything else."


class UserFriendlyTimeOnly(time.UserFriendlyTime):
    async def convert(self, ctx, argument):
        converted = await super().convert(ctx, argument)
        if converted.arg:
            raise commands.BadArgument(
                f'`{argument}` isn\'t a valid duration string.'
            )
        converted.arg = CLOSING_MESSAGE
        return converted


class CloseMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.close_command = self.bot.get_command('close')

    @commands.command(name='closemessage', aliases=['cm'],
                      usage="[after]",
                      help='Close the current thread with the message '
                           f'`{CLOSING_MESSAGE}`')
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @checks.thread_only()
    async def close_message(self, ctx, *, after='15m'):
        if after.isdigit():
            after = f'{after}m'
        after = await UserFriendlyTimeOnly().convert(ctx, after)
        return await self.close_command(ctx, after=after)


def setup(bot):
    bot.add_cog(CloseMessage(bot))
