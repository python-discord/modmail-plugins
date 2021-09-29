import asyncio
import contextlib
import typing as t

from core.models import getLogger

log = getLogger(__name__)


def create_task(
    coro: t.Awaitable,
    event_loop: t.Optional[asyncio.AbstractEventLoop] = None
) -> asyncio.Task:
    """
    Wrapper for creating asyncio `Task`s which logs exceptions raised in the task.

    If the loop kwarg is provided, the task is created from that event loop, otherwise the running loop is used.
    """
    if event_loop is not None:
        task = event_loop.create_task(coro)
    else:
        task = asyncio.create_task(coro)
    task.add_done_callback(_log_task_exception)
    return task


def _log_task_exception(task: asyncio.Task, *args) -> None:
    """Retrieve and log the exception raised in `task` if one exists."""
    with contextlib.suppress(asyncio.CancelledError):
        exception = task.exception()
        # Log the exception if one exists.
        if exception:
            log.error(f"Error in task {task.get_name()} {id(task)}!", exc_info=exception)
