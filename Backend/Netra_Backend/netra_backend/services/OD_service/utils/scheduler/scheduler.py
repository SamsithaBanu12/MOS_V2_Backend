"""
Scheduler for OD Service - Runs daily data export jobs.
Fetches satellite position and velocity data from the last 24 hours
and exports to CSV format.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# ---------------------------------------------------------------------
# Add OD_service root directory to path
# scheduler.py -> scheduler/ -> utils/ -> OD_service/
# ---------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.od_data_handler import fetch_od_data


# ---------------------------------------------------------------------
# Job logic
# ---------------------------------------------------------------------
def daily_od_export_job(start_time: str = None, end_time: str = None):
    """
    Scheduled job that runs daily at 12:00 AM UTC.
    Fetches OD data from the last 24 hours and exports to CSV.
    """

    # Determine end time
    if end_time is None:
        end_time_dt = datetime.now(pytz.UTC)
        end_time_str = end_time_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        end_time_str = end_time

    # Determine start time
    if start_time is None:
        if end_time is None:
            start_time_dt = datetime.now(pytz.UTC) - timedelta(hours=24)
        else:
            end_time_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            if end_time_dt.tzinfo is None:
                end_time_dt = pytz.UTC.localize(end_time_dt)
            start_time_dt = end_time_dt - timedelta(hours=24)

        start_time_str = start_time_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_time_str = start_time

    print(f"[{datetime.now(pytz.UTC).isoformat()}] Starting daily OD export job")
    print(f"Time range: {start_time_str} to {end_time_str}")

    try:
        result = fetch_od_data(start_time_str, end_time_str)

        print("Successfully exported data:")
        print(f"  - Position records: {result['record_count']['position']}")
        print(f"  - Velocity records: {result['record_count']['velocity']}")
        print(f"  - CSV file: {result['csv_exported']}")
        exec_res = result.get('executable_result', {})
        if exec_res.get('tle_saved'):
            print(f"  - TLE saved to DB from: {exec_res.get('tle_path')}")
        else:
            print("  - No TLE saved to DB.")
        print(f"[{datetime.now(pytz.UTC).isoformat()}] Job completed successfully\n")

    except Exception as e:
        print(f"[{datetime.now(pytz.UTC).isoformat()}] ERROR: Job failed - {e}\n")
        raise


# ---------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------
def start_scheduler(test_mode: bool = False):
    """
    Initialize and start the scheduler.
    """
    scheduler = BlockingScheduler(timezone=pytz.UTC)

    if test_mode:
        scheduler.add_job(
            daily_od_export_job,
            trigger=IntervalTrigger(minutes=1),
            id="test_od_export",
            name="Test OD Data Export (Every Minute)",
            replace_existing=True,
        )
        print("=" * 60)
        print("OD Service Scheduler Started (TEST MODE)")
        print("=" * 60)
        print(f"Current time (UTC): {datetime.now(pytz.UTC).isoformat()}")
        print("Job will run EVERY MINUTE for testing")
    else:
        scheduler.add_job(
            daily_od_export_job,
            trigger=CronTrigger(hour=0, minute=0, timezone=pytz.UTC),
            id="daily_od_export",
            name="Daily OD Data Export",
            replace_existing=True,
        )
        print("=" * 60)
        print("OD Service Scheduler Started")
        print("=" * 60)
        print(f"Current time (UTC): {datetime.now(pytz.UTC).isoformat()}")

    print("Scheduled jobs:")
    for job in scheduler.get_jobs():
        print(f"  - {job.name}")
        print(f"    ID: {job.id}")
        print(f"    Next run: {job.next_run_time}")

    print("=" * 60)
    print("\nScheduler is running. Press Ctrl+C to exit.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")


# ---------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OD Service Scheduler - Daily data export jobs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scheduler.py
  python scheduler.py --now
  python scheduler.py --test
  python scheduler.py --now --start-time "2026-03-01 10:00:00" --end-time "2026-03-01 12:00:00"
""",
    )

    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the job immediately once and exit",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: run job every minute instead of daily at midnight",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        help='Custom start time "YYYY-MM-DD HH:MM:SS" (use with --now)',
    )
    parser.add_argument(
        "--end-time",
        type=str,
        help='Custom end time "YYYY-MM-DD HH:MM:SS" (use with --now)',
    )

    args = parser.parse_args()

    if args.now:
        print("=" * 60)
        if args.start_time or args.end_time:
            print("Running OD export job with custom time range")
        else:
            print("Running OD export job immediately (last 24 hours)")
        print("=" * 60)

        daily_od_export_job(
            start_time=args.start_time,
            end_time=args.end_time,
        )

        print("=" * 60)
        print("Job completed. Exiting.")
        print("=" * 60)
    else:
        if args.start_time or args.end_time:
            print("WARNING: --start-time and --end-time are only used with --now")
            print("Ignoring custom times and starting scheduler normally.")
        start_scheduler(test_mode=args.test)
