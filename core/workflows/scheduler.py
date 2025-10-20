"""
Background Scheduler for Creative Engine (Task 10.4).

Uses APScheduler to run Creative Engine workflow every 30 minutes in the background.
Handles job management, cleanup, and graceful shutdown.
"""

import os
import logging
from typing import Optional
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from .creative_engine import run_creative_engine_sync


# ============================================================================
# Configuration
# ============================================================================

SCHEDULER_CONFIG = {
    "interval_minutes": int(os.getenv("CE_INTERVAL_MINUTES", "30")),
    "max_instances": int(os.getenv("CE_MAX_INSTANCES", "1")),
    "coalesce": os.getenv("CE_COALESCE", "true").lower() == "true",
    "misfire_grace_time": int(os.getenv("CE_MISFIRE_GRACE_TIME", "300")),  # 5 minutes
}


# ============================================================================
# Global Scheduler Instance
# ============================================================================

_scheduler: Optional[BackgroundScheduler] = None
_job_id = "creative_engine_job"

logger = logging.getLogger(__name__)


# ============================================================================
# Job Execution
# ============================================================================

def _run_creative_engine_job():
    """
    Job function executed by scheduler.

    Runs the Creative Engine workflow synchronously.
    Logs execution status and errors.
    """
    session_id = f"scheduled_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info(f"🚀 Starting Creative Engine run (session: {session_id})")

    try:
        result = run_creative_engine_sync(session_id=session_id)
        logger.info(f"✓ Creative Engine run completed successfully")
        return result

    except Exception as e:
        logger.error(f"❌ Creative Engine run failed: {str(e)}", exc_info=True)
        raise


# ============================================================================
# Event Listeners
# ============================================================================

def _job_executed_listener(event):
    """Log successful job executions."""
    logger.info(f"✓ Job executed: {event.job_id} at {datetime.now()}")


def _job_error_listener(event):
    """Log job execution errors."""
    logger.error(
        f"❌ Job error: {event.job_id} - {event.exception}",
        exc_info=event.exception
    )


# ============================================================================
# Scheduler Management
# ============================================================================

def start_creative_engine_scheduler() -> BackgroundScheduler:
    """
    Start the Creative Engine background scheduler.

    Configures and starts APScheduler with:
    - 30-minute interval (configurable)
    - Coalesce=True to prevent overlapping runs
    - Max 1 instance running at a time
    - Automatic error recovery

    Returns:
        BackgroundScheduler instance

    Example:
        >>> from core.workflows import start_creative_engine_scheduler
        >>> scheduler = start_creative_engine_scheduler()
        >>> # Workflow runs every 30 minutes in background
        >>> # ...
        >>> stop_creative_engine_scheduler()
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("⚠️  Scheduler already running")
        return _scheduler

    # Create scheduler
    _scheduler = BackgroundScheduler(
        daemon=True,  # Allow process to exit
        timezone='UTC',
    )

    # Add job with interval trigger
    trigger = IntervalTrigger(
        minutes=SCHEDULER_CONFIG["interval_minutes"],
        timezone='UTC',
    )

    _scheduler.add_job(
        func=_run_creative_engine_job,
        trigger=trigger,
        id=_job_id,
        name="Creative Engine",
        max_instances=SCHEDULER_CONFIG["max_instances"],
        coalesce=SCHEDULER_CONFIG["coalesce"],
        misfire_grace_time=SCHEDULER_CONFIG["misfire_grace_time"],
        replace_existing=True,
    )

    # Add event listeners
    _scheduler.add_listener(_job_executed_listener, EVENT_JOB_EXECUTED)
    _scheduler.add_listener(_job_error_listener, EVENT_JOB_ERROR)

    # Start scheduler
    _scheduler.start()

    logger.info(
        f"✓ Creative Engine scheduler started "
        f"(interval: {SCHEDULER_CONFIG['interval_minutes']} min)"
    )

    # Print next run time
    job = _scheduler.get_job(_job_id)
    if job:
        next_run = job.next_run_time
        logger.info(f"  Next run: {next_run}")

    return _scheduler


def stop_creative_engine_scheduler(wait: bool = True):
    """
    Stop the Creative Engine background scheduler.

    Args:
        wait: If True, wait for running jobs to complete before shutdown

    Example:
        >>> stop_creative_engine_scheduler(wait=True)
        >>> # Waits for current job to finish, then shuts down
    """
    global _scheduler

    if _scheduler is None:
        logger.warning("⚠️  No scheduler to stop")
        return

    if not _scheduler.running:
        logger.warning("⚠️  Scheduler not running")
        return

    logger.info("Stopping Creative Engine scheduler...")
    _scheduler.shutdown(wait=wait)
    _scheduler = None
    logger.info("✓ Scheduler stopped")


def is_scheduler_running() -> bool:
    """
    Check if the scheduler is running.

    Returns:
        True if scheduler is running, False otherwise
    """
    return _scheduler is not None and _scheduler.running


def get_next_run_time() -> Optional[datetime]:
    """
    Get the next scheduled run time.

    Returns:
        Next run datetime, or None if scheduler not running
    """
    if not is_scheduler_running():
        return None

    job = _scheduler.get_job(_job_id)
    return job.next_run_time if job else None


def trigger_immediate_run():
    """
    Trigger an immediate Creative Engine run (outside of schedule).

    Does not affect the regular schedule.

    Example:
        >>> trigger_immediate_run()
        >>> # Runs immediately, next scheduled run unaffected
    """
    if not is_scheduler_running():
        raise RuntimeError("Scheduler not running - call start_creative_engine_scheduler() first")

    logger.info("🚀 Triggering immediate Creative Engine run")
    _scheduler.add_job(
        func=_run_creative_engine_job,
        trigger='date',  # Run once immediately
        id=f"{_job_id}_immediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        name="Creative Engine (Immediate)",
        max_instances=1,
        replace_existing=False,
    )


def get_scheduler_status() -> dict:
    """
    Get detailed scheduler status.

    Returns:
        Dict with scheduler state, job info, next run time

    Example:
        >>> status = get_scheduler_status()
        >>> print(status)
        {
            'running': True,
            'job_id': 'creative_engine_job',
            'next_run_time': '2025-10-20 15:30:00',
            'interval_minutes': 30,
            'max_instances': 1,
            'coalesce': True
        }
    """
    if not is_scheduler_running():
        return {
            'running': False,
            'job_id': None,
            'next_run_time': None,
        }

    job = _scheduler.get_job(_job_id)

    return {
        'running': True,
        'job_id': _job_id,
        'next_run_time': str(job.next_run_time) if job else None,
        'interval_minutes': SCHEDULER_CONFIG["interval_minutes"],
        'max_instances': SCHEDULER_CONFIG["max_instances"],
        'coalesce': SCHEDULER_CONFIG["coalesce"],
        'misfire_grace_time': SCHEDULER_CONFIG["misfire_grace_time"],
    }


# ============================================================================
# Cleanup Job
# ============================================================================

def cleanup_expired_strategies():
    """
    Remove expired strategy JSON files based on TTL.

    Called periodically to prevent unbounded storage growth.
    Removes files where current time > expires_at timestamp.
    """
    from pathlib import Path
    import json
    from datetime import datetime

    from .creative_engine import CREATIVE_ENGINE_CONFIG

    output_dir = Path(CREATIVE_ENGINE_CONFIG["output_dir"])
    if not output_dir.exists():
        return

    now = datetime.now()
    removed_count = 0

    # Check all bucket directories
    for bucket_dir in ["low", "medium", "high"]:
        bucket_path = output_dir / bucket_dir
        if not bucket_path.exists():
            continue

        for filepath in bucket_path.glob("*.json"):
            try:
                # Read file to check expiry
                with open(filepath, 'r') as f:
                    data = json.load(f)

                expires_at_str = data.get("expires_at")
                if not expires_at_str:
                    continue

                expires_at = datetime.fromisoformat(expires_at_str)

                # Remove if expired
                if now > expires_at:
                    filepath.unlink()
                    removed_count += 1
                    logger.debug(f"Removed expired file: {filepath.name}")

            except Exception as e:
                logger.error(f"Error checking file {filepath}: {e}")

    if removed_count > 0:
        logger.info(f"✓ Cleanup complete: removed {removed_count} expired strategies")


def start_cleanup_scheduler():
    """
    Start a separate scheduler for cleanup jobs.

    Runs cleanup every 24 hours.
    """
    if not is_scheduler_running():
        raise RuntimeError("Main scheduler not running")

    cleanup_trigger = IntervalTrigger(hours=24, timezone='UTC')

    _scheduler.add_job(
        func=cleanup_expired_strategies,
        trigger=cleanup_trigger,
        id="cleanup_job",
        name="Strategy Cleanup",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    logger.info("✓ Cleanup scheduler started (interval: 24 hours)")
