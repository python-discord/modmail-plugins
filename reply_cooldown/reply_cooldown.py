import time
from collections import deque

import discord
from discord.ext import commands

from bot import ModmailBot
from core.thread import Thread

# Number of messages kept in memory to check for double sends
BUFFER_LENGTH = 10
# Buffer of messages recently sent
# Each entry is under the format (channel_id, message_content, timestamp).
MESSAGES_BUFFER = deque(maxlen=BUFFER_LENGTH)
# Cooldown time
COOLDOWN_TIME = 10


async def setup(bot: ModmailBot) -> None:
    """Monkey patch the built-in reply function to add a cooldown between uses."""
    _reply = Thread.reply

    async def reply(self: commands.Cog, message: discord.Message, anonymous: bool = False, plain: bool = False) -> None:
        """The new reply function with a cooldown between uses."""
        # Bypass the cooldown if the message has attachments.
        if not message.attachments:
            for entry in MESSAGES_BUFFER:
                if (
                        entry[0] == message.channel.id
                        and entry[1] == message.content
                        and entry[2] > (time.time() - COOLDOWN_TIME)
                ):
                    await message.add_reaction("\u274c")
                    return

        MESSAGES_BUFFER.append((message.channel.id, message.content, time.time()))
        await _reply(self, message, anonymous, plain)

    Thread.reply = reply
