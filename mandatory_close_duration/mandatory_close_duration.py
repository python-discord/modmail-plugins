from discord.ext import commands

from bot import ModmailBot
from core import time


class StrictUserFriendlyDuration(time.UserFriendlyTime):
    """
    A converter which parses user-friendly time durations.

    Since this converter is meant for parsing close messages while
    closing threads, both custom close messages and time durations are
    parsed.

    Unlike the parent class, a time duration must be provided when
    a custom close message is provided.
    """

    MODIFIERS = {'silently', 'silent', 'cancel'}

    async def convert(self, ctx: commands.Context, argument: str) -> "StrictUserFriendlyDuration":
        """
        Parse the provided time duration along with any close message.

        Fail if a custom close message is provided without a time
        duration.
        """
        await super().convert(ctx, argument)

        argument_passed = bool(argument)
        not_a_modifier = argument not in self.MODIFIERS
        if argument_passed and not_a_modifier and self.arg == argument:
            # Fail since only a close message was provided.
            raise commands.BadArgument("A time duration must be provided when closing with a custom message.")

        return self


ADDED_HELP_TEXT = '\n\n*Note: Providing a time duration is necessary when closing with a custom message.*'


def setup(bot: ModmailBot) -> None:
    """
    Monkey patch the close command's callback.

    This makes it use the StrictUserFriendlyTime converter and updates
    the help text to reflect the new behaviour..
    """
    global previous_converter

    command = bot.get_command('close')

    previous_converter = command.callback.__annotations__['after']
    command.callback.__annotations__['after'] = StrictUserFriendlyDuration
    command.callback = command.callback

    command.help += ADDED_HELP_TEXT


def teardown(bot: ModmailBot) -> None:
    """Undo changes to the close command."""
    command = bot.get_command('close')

    command.callback.__annotations__['after'] = previous_converter
    command.callback = command.callback

    command.help = command.help.remove_suffix(ADDED_HELP_TEXT)
