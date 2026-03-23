"""APScheduler-based daily job runner.

Runs Monday–Thursday and Sunday only (skips Friday & Saturday).
Schedule is reconfigurable at runtime without restarting the app.
"""

import logging
import threading
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(daemon=True)
_job_lock = threading.Lock()
JOB_ID = "timesheet_job"


def start(job_fn: Callable, hour: int, minute: int) -> None:
    """Start the scheduler with the given daily job at hour:minute."""
    _scheduler.start()
    _schedule_job(job_fn, hour, minute)
    logger.info("Scheduler started — job runs Mon–Thu & Sun at %02d:%02d", hour, minute)


def reschedule(job_fn: Callable, hour: int, minute: int) -> None:
    """Update the run time without restarting the scheduler."""
    with _job_lock:
        if _scheduler.get_job(JOB_ID):
            _scheduler.remove_job(JOB_ID)
        _schedule_job(job_fn, hour, minute)
    logger.info("Scheduler rescheduled to %02d:%02d", hour, minute)


def stop() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def _schedule_job(job_fn: Callable, hour: int, minute: int) -> None:
    # day_of_week: 0=Mon … 6=Sun  →  Mon-Thu (0-3) + Sun (6)
    trigger = CronTrigger(day_of_week="0-3,6", hour=hour, minute=minute)
    _scheduler.add_job(job_fn, trigger=trigger, id=JOB_ID, replace_existing=True)
