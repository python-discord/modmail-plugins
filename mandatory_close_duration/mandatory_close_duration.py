import asyncio

import discord
from discord.ext import commands

from bot import ModmailBot
from core import time


async def close_after_confirmation(ctx: commands.Context, converted_arg: time.UserFriendlyTime) -> None:
    """
    Send a message and allow users to react to it to close the thread.

    The reaction times out after 5 minutes.
    """
    unicode_reaction = '\N{WHITE HEAVY CHECK MARK}'
    warning_message = ("\N{WARNING SIGN} A time duration wasn't provided, reacting to this message will close"
                       " this thread instantly with the provided custom close message.")

    message = await ctx.send(warning_message)
    await message.add_reaction(unicode_reaction)

    def checkmark_press_check(reaction: discord.Reaction, user: discord.User) -> bool:
        is_right_reaction = (
            user != ctx.bot.user
            and reaction.message.id == message.id
            and str(reaction.emoji) == unicode_reaction
        )

        return is_right_reaction

    try:
        await ctx.bot.wait_for('reaction_add', check=checkmark_press_check, timeout=5 * 60)
    except asyncio.TimeoutError:
        await message.edit(content=message.content+'\n\n**Timed out.**')
        await message.clear_reactions()
    else:
        await original_close_command(ctx, after=converted_arg)


async def safe_close(
    self: time.UserFriendlyTime,
    ctx: commands.Context,
    *,
    after: time.UserFriendlyTime = None
) -> None:
    """
    Close the current thread.

    Unlike the original close command, confirmation is awaited when
    a time duration isn't provided but a custom close message is.
    """
    modifiers = {'silently', 'silent', 'cancel'}

    argument_passed = after is not None

    if argument_passed:
        not_a_modifier = after.arg not in modifiers

        # These changes are always made to the argument by the super
        # class so they need to be replicated before the raw argument
        # is compared with the parsed message.
        stripped_argument = after.raw.strip()
        argument_without_phrases = stripped_argument.removeprefix('in ').removesuffix(' from now')

        no_duration = after.arg == argument_without_phrases

    if argument_passed and not_a_modifier and no_duration:
        # Ask for confirmation since only a close message was provided.
        await close_after_confirmation(ctx, after)
    else:
        await original_close_command(ctx, after=after)


def setup(bot: ModmailBot) -> None:
    """
    Monkey patch the close command's callback to safe_close.

    The help text is also updated to reflect the new behaviour.
    """
    global original_close_command

    command = bot.get_command('close')
    original_close_command = command.copy()
    original_close_command.cog = command.cog

    command.callback = safe_close
    command.help += '\n\n*Note: A time duration should be provided when closing with a custom message.*'


def teardown(bot: ModmailBot) -> None:
    """Restore the original close command."""
    bot.remove_command('close')
    bot.add_command(original_close_command)
