import asyncio
import typing as t
import weakref

import discord
from discord.ext import commands

from bot import ModmailBot
from core import checks
from core.models import PermissionLevel, getLogger
from core.thread import Thread
from .utils import get_or_fetch

PYDIS_NO_KICK_ROLE_IDS = (
    267627879762755584,  # Owners in PyDis
    409416496733880320,  # DevOps in PyDis
)
APPEAL_NO_KICK_ROLE_ID = 890270873813139507  # Staff in appeals server
APPEAL_GUILD_ID = 890261951979061298

BAN_APPEAL_MESSAGE = (
    "Please be patient, it may take a while for us to respond to ban appeals.\n\n"
    "To ensure we can respond to your appeal, make sure you keep your DMs "
    "open, stay in the appeal server, and do not block the bot."
)

log = getLogger(__name__)


class BanAppeals(commands.Cog):
    """A plugin to manage threads from a separate ban appeal server."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

        self.pydis_guild: t.Optional[discord.Guild] = None
        self.appeal_categories: list[discord.CategoryChannel] = []

        self.appeals_guild: t.Optional[discord.Guild] = None
        self.logs_channel: t.Optional[discord.TextChannel] = None

        self.db = self.bot.plugin_db.get_partition(self)

        self.user_locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()
        self.ignore_next_remove_event: set[int] = set()

    async def cog_load(self) -> None:
        """Initialise the plugin's configuration."""
        self.pydis_guild = self.bot.guild
        self.appeals_guild = self.bot.get_guild(APPEAL_GUILD_ID)

        db_categories = await self.db.find_one({"_id": "ban-appeal-categories"})
        db_categories = db_categories or {}
        self.appeal_categories = db_categories.get("categories", [])
        log.info("Loaded %s appeal categories", len(self.appeal_categories))
        self.logs_channel = discord.utils.get(self.appeals_guild.channels, name="logs")

        log.info("Plugin loaded, checking if there are people to kick.")
        asyncio.create_task(self._sync_kicks())

    async def _sync_kicks(self) -> None:
        """Iter through all members in appeals guild, kick them if they meet criteria."""
        await asyncio.sleep(5)
        for member in self.appeals_guild.members:
            await self._maybe_kick_user(member)

    async def _maybe_kick_user(self, member: discord.Member) -> bool:
        """
        Kick members joining appeals if they are not banned, and not part of the bypass list.

        If they have a ModMail thread open, the kick is notified.

        Return a boolean for whether the member wes kicked.
        """
        if member.bot:
            return False

        if not await self._is_banned_pydis(member):
            pydis_member = await get_or_fetch.get_or_fetch_member(self.pydis_guild, member.id)
            if pydis_member and (
                any(role.id in PYDIS_NO_KICK_ROLE_IDS for role in pydis_member.roles)
                or APPEAL_NO_KICK_ROLE_ID in (role.id for role in member.roles)
            ):
                log.info("Not kicking %s (%d) as they have a bypass role", member, member.id)
                return False
            try:
                await member.kick(reason="Not banned in main server")
            except discord.Forbidden:
                log.error("Failed to kick %s (%d) due to insufficient permissions.", member, member.id)
            else:
                await self.logs_channel.send(
                    f"Kicked {member} ({member.id}) on join as they're not banned in main server."
                )
                log.info("Kicked %s (%d).", member, member.id)

                thread = await self.bot.threads.find(recipient=member)
                if not thread:
                    return False

                embed = discord.Embed(
                    description="The recipient joined the appeals server and has been automatically kicked.",
                    color=self.bot.error_color
                )
                await thread.channel.send(embed=embed)
                self.ignore_next_remove_event.add(member.id)

                return True

        return False

    async def _is_banned_pydis(self, member: discord.Member) -> bool:
        """See if the given member is banned in PyDis."""
        try:
            await self.pydis_guild.fetch_ban(member)
        except discord.errors.NotFound:
            return False
        return True

    async def _handle_join(self, member: discord.Member) -> None:
        """
        Kick members who cannot appeal and notify for rejoins.

        Members who join the appeal server but are in the main server
        are kicked.

        If a member rejoins while appealing, it's notified in their
        thread.
        """
        if member.guild == self.pydis_guild:
            # Join event from PyDis
            # Kick them from appeals guild now they're back in PyDis
            appeals_member = await get_or_fetch.get_or_fetch_member(self.appeals_guild, member.id)
            if appeals_member:
                await appeals_member.kick(reason="Rejoined PyDis")
                await self.logs_channel.send(f"Kicked {member} ({member.id}) as they rejoined PyDis.")
                log.info("Kicked %s (%d) as they rejoined PyDis.", member, member.id)

                thread = await self.bot.threads.find(recipient=member)
                if not thread:
                    return

                embed = discord.Embed(
                    description="The recipient has been kicked from the appeals server.",
                    color=self.bot.error_color
                )
                await thread.channel.send(embed=embed)
                self.ignore_next_remove_event.add(member.id)
        elif member.guild == self.appeals_guild:
            # Join event from the appeals server
            # Kick them if they are not banned and not part of the bypass list
            # otherwise notify that they rejoined while appealing.
            has_been_kicked = await self._maybe_kick_user(member)
            if has_been_kicked:
                return

            thread = await self.bot.threads.find(recipient=member)
            if not thread:
                return

            category = await self.get_useable_appeal_category()
            embed = discord.Embed(
                description=f"Moving thread to `{category}` category since recipient has joined the appeals server.",
                color=self.bot.mod_color
            )
            await thread.channel.send(embed=embed)

            await thread.channel.move(
                category=category,
                end=True,
                sync_permissions=True,
                reason=f"{member} joined appeals server.",
            )

    async def _handle_remove(self, member: discord.Member) -> None:
        """
        Notify if a member who is appealing leaves the appeals guild.

        If the member's id is in the ignore set, then the current
        event is skipped.

        An embed is sent in the thread once they leave.
        """
        if not member.guild == self.appeals_guild:
            return

        try:
            self.ignore_next_remove_event.remove(member.id)
        except KeyError:
            pass
        else:
            return

        thread = await self.bot.threads.find(recipient=member)
        if not thread:
            return

        embed = discord.Embed(description="The recipient has left the appeals server.", color=self.bot.error_color)
        await thread.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        Acquire a lock and handle member joins.

        A lock is acquired so that subsequent join and leave events
        happen only after the current member join event is fully
        handled.
        """
        user_lock = self.user_locks.setdefault(member.id, asyncio.Lock())
        async with user_lock:
            await self._handle_join(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """
        Acquire a lock and handle member removals.

        A lock is acquired so that subsequent join and leave events
        happen only after the current member remove event is fully
        handled.
        """
        user_lock = self.user_locks.setdefault(member.id, asyncio.Lock())
        async with user_lock:
            await self._handle_remove(member)

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.group(invoke_without_command=True, aliases=("appeal_category",))
    async def appeal_category_management(self, ctx: commands.Context) -> None:
        """Group of commands for managing appeal categories."""
        await ctx.send_help(ctx.command)

    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @appeal_category_management.command(name="get")
    async def get_categories(self, ctx: commands.Context) -> None:
        """Get the list of appeal categories of commands for managing appeal categories."""
        category_str = ", ".join(map(str, self.appeal_categories)) if self.appeal_categories else "None"

        await ctx.send(f"Currently configured appeal categories are: {category_str}")

    @checks.has_permissions(PermissionLevel.OWNER)
    @appeal_category_management.command(name="add")
    async def add_category(self, ctx: commands.Context, appeal_category: discord.CategoryChannel) -> None:
        """Add a category to the list of appeal categories."""
        if appeal_category.id in self.appeal_categories:
            await ctx.send(f":x: {appeal_category} already in the appeal category list.")
            return

        self.appeal_categories.append(appeal_category.id)
        await self.db.find_one_and_update(
            {"_id": "ban-appeal-categories"},
            {"$addToSet": {"categories": appeal_category.id}},
            upsert=True,
        )

        await ctx.send(f":+1: Added {appeal_category} to the available appeal categories.")

    @checks.has_permissions(PermissionLevel.OWNER)
    @appeal_category_management.command(name="delete", aliases=("remove", "del", "rem"))
    async def del_category(self, ctx: commands.Context, category_to_remove: discord.CategoryChannel) -> None:
        """Remove a category from the list of appeal categories."""
        if category_to_remove.id not in self.appeal_categories:
            await ctx.send(f":x: {category_to_remove} isn't in the appeal categories list.")
            return

        self.appeal_categories.remove(category_to_remove.id)
        await self.db.find_one_and_update(
            {"_id": "ping-delay-config"},
            {"$pull": {"ignored_categories": category_to_remove.id}},
        )
        await ctx.send(f":+1: Removed {category_to_remove} from the appeal categories list.")

    async def get_useable_appeal_category(self) -> t.Optional[discord.CategoryChannel]:
        """Get a useable (non-full) appeal category from the db, create a new one if needed."""
        for category_id in self.appeal_categories:
            category = await get_or_fetch.get_or_fetch_channel(self.pydis_guild, category_id)
            if len(category.channels) < 50:
                return category
        return None

    @commands.Cog.listener()
    async def on_thread_ready(self, thread: Thread, *args) -> None:
        """If the new thread is for an appeal, move it to the appeals category."""
        if await self._is_banned_pydis(thread.recipient):
            category = await self.get_useable_appeal_category()
            if category:
                await thread.channel.edit(category=category, sync_permissions=True)
            else:
                await thread.channel.send("ERROR! Could not move thread to an appeal category as they're all full!")

            embed = discord.Embed(
                colour=self.bot.mod_color,
                description=BAN_APPEAL_MESSAGE,
                timestamp=thread.channel.created_at,
            )

            recipient_thread_close = self.bot.config.get("recipient_thread_close")

            if recipient_thread_close:
                footer = self.bot.config["thread_self_closable_creation_footer"]
            else:
                footer = self.bot.config["thread_creation_footer"]

            embed.set_footer(text=footer, icon_url=self.bot.guild.icon.url)
            embed.title = "Ban appeal"

            await thread.recipient.send(embed=embed)


async def setup(bot: ModmailBot) -> None:
    """Add the BanAppeals cog."""
    await bot.add_cog(BanAppeals(bot))
