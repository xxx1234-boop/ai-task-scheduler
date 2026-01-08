"""Background scheduler for automated tasks."""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import engine
from app.services.schedule_service import ScheduleService
from app.schemas.workflow_requests import SchedulePreferences, DailyHours
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def generate_weekly_schedule_job():
    """Job to automatically generate weekly schedule every Monday."""
    logger.info("Starting automated weekly schedule generation...")

    try:
        async with AsyncSession(engine) as session:
            service = ScheduleService()

            # Calculate next Monday (or today if it's Monday)
            today = datetime.now().date()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                # Today is Monday, schedule for this week
                week_start = datetime.combine(today, datetime.min.time())
            else:
                # Schedule for next Monday
                next_monday = today + timedelta(days=days_until_monday)
                week_start = datetime.combine(next_monday, datetime.min.time())

            # Default preferences (can be made configurable via settings)
            preferences = SchedulePreferences(
                daily_hours=DailyHours(
                    mon=6.0,
                    tue=6.0,
                    wed=6.0,
                    thu=6.0,
                    fri=6.0,
                    sat=0.0,
                    sun=0.0,
                ),
                avoid_context_switch=True,
                max_hours_per_task_per_day=4.0,
            )

            result = await service.generate_weekly_schedule(
                session=session,
                week_start=week_start,
                preferences=preferences,
                fixed_events=[],
                clear_existing=True,
            )

            logger.info(
                f"Weekly schedule generated successfully. "
                f"Total planned hours: {result.summary.total_planned_hours}, "
                f"Schedules created: {len(result.schedules)}"
            )

            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"Schedule warning: {warning}")

    except Exception as e:
        logger.error(f"Failed to generate weekly schedule: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler."""
    # Schedule job to run every Monday at 6:00 AM JST (= Sunday 21:00 UTC)
    scheduler.add_job(
        generate_weekly_schedule_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0, timezone="Asia/Tokyo"),
        id="weekly_schedule_generation",
        name="Generate weekly schedule",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started. Weekly schedule will generate every Monday at 6:00 AM JST.")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")
