import asyncio
import typing as t
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from bot import ModmailBot
from core import checks
from core.models import PermissionLevel, getLogger
from core.thread import Thread
from .utils import async_tasks

log = getLogger(__name__)


@dataclass
class PingConfig:
    """Hold the current ping configuration."""

    _id: str = field(repr=False, default="ping-delay-config")

    ping_string: str = "@here"
    wait_duration: int = 5 * 60
    ignored_categories: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class PingTask:
    """Data about an individual ping later task."""

    when_to_ping: str  # ISO datetime stamp
    channel_id: int


class PingManager(commands.Cog):
    """A plugin to manage what and when to ping in ModMail threads."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

        self.config: t.Optional[PingConfig] = None
        self.ping_tasks: list[PingTask] = None
        self.db = bot.api.get_plugin_partition(self)

        self.init_task = async_tasks.create_task(self.init_plugin(), self.bot.loop)

    async def init_plugin(self) -> None:
        """Fetch the current config from the db."""
        db_config = await self.db.find_one({"_id": "ping-delay-config"})
        db_config = db_config or {}
        self.config = PingConfig(**db_config)

        db_ping_tasks = await self.db.find_one({"_id": "ping-delay-tasks"})
        self.ping_tasks = [PingTask(**task) for task in db_ping_tasks.get("ping_tasks", [])]

        log.info("Loaded config: %s", self.config)
        log.info("Loaded %d ping tasks", len(self.ping_tasks))
        for task in self.ping_tasks:
            async_tasks.create_task(self.maybe_ping_later(task), self.bot.loop)

    @commands.group(invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    async def ping_delay(self, ctx: commands.Context) -> None:
        """Manage when to ping in threads without a staff response."""
        await ctx.send_help(ctx.command)

    @ping_delay.command(name="set")
    @checks.has_permissions(PermissionLevel.OWNER)
    async def set_delay(self, ctx: commands.Context, wait_duration: int) -> None:
        """Set the number of seconds to wait after a thread is opened to ping."""
        await self.init_task

        await self.db.find_one_and_update(
            {"_id": "ping-delay-config"},
            {"$set": {"wait_duration": wait_duration}},
            upsert=True,
        )
        self.config.wait_duration = wait_duration
        await ctx.send(f":+1: Set ping delay to {wait_duration} seconds.")

    @ping_delay.command(name="get")
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    async def get_delay(self, ctx: commands.Context) -> None:
        """Get the number of seconds to wait after a thread is opened to ping."""
        await ctx.send(f"The current ping delay is {self.config.wait_duration} seconds.")

    @commands.group(invoke_without_command=True)
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    async def ping_string(self, ctx: commands.Context) -> None:
        """Manage what message to send in threads without a staff response."""
        await ctx.send_help(ctx.command)

    @checks.has_permissions(PermissionLevel.OWNER)
    @ping_string.command(name="set")
    async def set_ping(self, ctx: commands.Context, ping_string: str) -> None:
        """Set what to send after a waiting for a thread to be responded to."""
        await self.init_task

        await self.db.find_one_and_update(
            {"_id": "ping-delay-config"},
            {"$set": {"ping_string": ping_string}},
            upsert=True,
        )
        self.config.wait_duration = ping_string
        await ctx.send(f":+1: Set ping string to {ping_string}.", allowed_mentions=None)

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @ping_string.command(name="get")
    async def get_ping(self, ctx: commands.Context) -> None:
        """Get the number of seconds to wait after a thread is opened to ping."""
        await ctx.send(f"The ping string is {self.config.ping_string}.", allowed_mentions=None)

    @commands.group(invoke_without_command=True, aliases=("ping_ignored_categories", "ping_ignore"))
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    async def ping_ignore_categories(self, ctx: commands.Context) -> None:
        """Manage what categories never get sent pings in them."""
        await ctx.send_help(ctx.command)

    @checks.has_permissions(PermissionLevel.OWNER)
    @ping_ignore_categories.command(name="add", aliases=("set",))
    async def set_category(self, ctx: commands.Context, category_to_ignore: discord.CategoryChannel) -> None:
        """Add a category to the list of ignored categories."""
        await self.init_task

        if category_to_ignore.id in self.config.ignored_categories:
            await ctx.send(f":x: {category_to_ignore} already in the ignored categories.")
            return

        self.config.ignored_categories.append(category_to_ignore.id)
        await self.db.find_one_and_update(
            {"_id": "ping-delay-config"},
            {"$addToSet": {"ignored_categories": category_to_ignore.id}}
        )

        await ctx.send(f":+1: Added {category_to_ignore} to the ignored categories list.")

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @ping_ignore_categories.command(name="get")
    async def get_category(self, ctx: commands.Context) -> None:
        """Get the list of ignored categories."""
        await self.init_task

        if not self.config.ignored_categories:
            await ctx.send("There are currently no ignored categories.")
            return

        ignored_categories_str = ', '.join(map(str, self.config.ignored_categories))
        await ctx.send(f"The currently ignored categories are: {ignored_categories_str}.")

    @checks.has_permissions(PermissionLevel.OWNER)
    @ping_ignore_categories.command(name="delete", aliases=("remove", "del", "rem"))
    async def del_category(self, ctx: commands.Context, category_to_ignore: discord.CategoryChannel) -> None:
        """Remove a category from the list of ignored categories."""
        await self.init_task

        if category_to_ignore.id not in self.config.ignored_categories:
            await ctx.send(f":x: {category_to_ignore} isn't in the ignored categories list.")
            return

        self.config.ignored_categories.remove(category_to_ignore.id)
        await self.db.find_one_and_update(
            {"_id": "ping-delay-config"},
            {"$pull": {"ignored_categories": category_to_ignore.id}},
        )
        await ctx.send(f":+1: Removed {category_to_ignore} from the ignored categories list.")

    async def should_ping(self, channel: discord.TextChannel) -> bool:
        """Check if a ping should be sent to a thread depending on current config."""
        if channel.category_id in self.config.ignored_categories:
            log.info("Not pinging in %s as it's currently in an ignored category", channel)
            return False

        first_message_list = await channel.history(limit=1, oldest_first=True).flatten()
        first_message = first_message_list[0]
        thread_author_name = first_message.embeds[0].author.name
        async for message in channel.history(oldest_first=True):
            if not message.embeds:
                log.info("Not pinging in %s as a mod has sent an internal message in the thread.", channel)
                return False
            if not message.embeds[0].author.name == thread_author_name:
                log.info("Not pinging in %s as a mod has sent a reply in the thread.", channel)
                return False
        return True

    async def maybe_ping_later(self, ping_task: PingTask) -> None:
        """Pings conditionally after waiting the configured wait duration."""
        when_to_ping = datetime.fromisoformat(ping_task.when_to_ping)
        now = datetime.utcnow()
        seconds_to_sleep = (when_to_ping - now).total_seconds()
        if seconds_to_sleep < 0:
            log.info("Pinging for %d is overdue, pinging now.", ping_task.channel_id)
        else:
            await asyncio.sleep(seconds_to_sleep)

        if not (channel := self.bot.get_channel(ping_task.channel_id)):
            log.info("Channel closed before we could ping.")
        else:
            try:
                if await self.should_ping(channel):
                    await channel.send(self.config.ping_string)
            except discord.NotFound:
                # Fail silently if the channel gets deleted during processing.
                pass
            finally:
                # Ensure the task always gets removed.
                self.ping_tasks.remove(ping_task)
                await self.db.find_one_and_update(
                    {"_id": "ping-delay-tasks"},
                    {"$pull": {"ping_tasks": asdict(ping_task)}},
                )

    @commands.Cog.listener()
    async def on_thread_ready(self, thread: Thread, *args) -> None:
        """Schedule a task to check if the bot should ping in the thread after the defined wait duration."""
        await self.init_task
        now = datetime.utcnow()
        ping_task = PingTask(
            when_to_ping=(now + timedelta(seconds=self.config.wait_duration)).isoformat(),
            channel_id=thread.channel.id
        )
        self.ping_tasks.append(ping_task)
        await self.db.find_one_and_update(
            {"_id": "ping-delay-tasks"},
            {"$addToSet": {"ping_tasks": asdict(ping_task)}},
        )

        async_tasks.create_task(self.maybe_ping_later(ping_task), self.bot.loop)


def setup(bot: ModmailBot) -> None:
    """Add the PingManager plugin."""
    bot.add_cog(PingManager(bot))
