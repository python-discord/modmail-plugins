import typing as t

import discord
from discord.ext import commands

from bot import ModmailBot
from core import checks
from core import time
from core.models import PermissionLevel

DEFAULT_CLOSE_MESSAGE = "Feel free to open a new thread if you need anything else."


class UserFriendlyDuration(time.UserFriendlyTime):
    """
    A converter which parses user-friendly time durations.

    Since this converter is meant for parsing close messages while
    closing threads, both custom close messages and time durations are
    parsed.

    A default duration of time to close after can be provided.
    """

    def __init__(self, *, default_close_duration: t.Optional[str] = None) -> None:
        self.default_close_duration = default_close_duration

    async def convert(self, ctx: commands.Context, argument: str) -> "UserFriendlyDuration":
        """
        Parse the time duration if provided and prefix any message.

        The default close message is used as the close message.
        The default close message is appended if a custom close
        message is provided.

        Phrases which are removed to parse time durations correctly
        are restored if a time duration wasn't provided.

        If only an integer is passed in, it is treated as the number
        of minutes to close after.
        """
        if argument.strip().isdigit():
            argument = f'{argument}m'

        await super().convert(ctx, argument)

        # These changes are always made to the argument by the super
        # class so they need to be replicated before the raw argument
        # is compared with the parsed message.
        argument_without_phrases = argument.removeprefix('in ').removesuffix(' from now').strip()

        if self.default_close_duration and self.arg == argument_without_phrases:
            # A time duration hasn't been provided. The original
            # argument is passed instead of the one without phrases to
            # allow the phrases to be a part of the close message.
            new_time_duration = self.default_close_duration
            message = argument
        else:
            # Extract the portion of the argument that constitued the
            # time duration.
            if argument.endswith(self.arg):
                new_time_duration = argument.removesuffix(self.arg)
            elif argument_without_phrases.endswith(self.arg):
                new_time_duration = argument_without_phrases.removesuffix(self.arg)
            elif argument_without_phrases.startswith(self.arg):
                new_time_duration = argument_without_phrases.removeprefix(self.arg)

            new_time_duration = new_time_duration.strip()
            message = self.arg

        if message:
            add_period = not message.endswith((".", "!", "?"))
            new_close_message = message + (". " if add_period else " ") + DEFAULT_CLOSE_MESSAGE
        else:
            new_close_message = DEFAULT_CLOSE_MESSAGE

        await super().convert(ctx, f'{new_time_duration} {new_close_message}')
        return self


class CloseMessage(commands.Cog):
    """A plugin that adds a close command with a default close message."""

    def __init__(self, bot: ModmailBot) -> None:
        self.bot = bot
        self.close_command = self.bot.get_command('close')

    @commands.group(
        name="closemessage",
        aliases=("cm",),
        usage="[after] [close message]",
        invoke_without_command=True
    )
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @checks.thread_only()
    async def close_message(
        self,
        ctx: commands.Context,
        *,
        after: str = ''
    ) -> t.Optional[discord.Message]:
        """
        Close the current thread with a message.

        The default close message is used as the close message.
        The default close message is appended if a custom close
        message is provided.

        15 minutes is the default period of time before the thread
        closes.

        If only an integer is passed in, it is treated as the number
        of minutes to close after.

        Run `{prefix}help close` for additional information on how
        durations and custom close messages can be provided.
        """
        # We're doing the conversion here to make the argument optional
        # while still passing the converted argument instead of an
        # empty string to the close command.
        after = await UserFriendlyDuration(default_close_duration='15m').convert(ctx, after)
        return await self.close_command(ctx, after=after)

    @close_message.command(aliases=('msg', 'm'))
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @checks.thread_only()
    async def message(self, ctx: commands.Context) -> None:
        """Send the default close message."""
        await ctx.send(f'> {DEFAULT_CLOSE_MESSAGE}')


def setup(bot: ModmailBot) -> None:
    """Load the CloseMessage plugin."""
    bot.add_cog(CloseMessage(bot))
