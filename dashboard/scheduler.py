# dashboard/scheduler.py

import importlib
import os
import traceback
from datetime import datetime
from config import SCHEDULER_TIMEZONE, APP_TIMEZONE
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pywintypes import com_error
from pandas.errors import EmptyDataError

from flask import current_app
from dashboard.models import db, Task, TaskLog
sched = BackgroundScheduler(timezone=SCHEDULER_TIMEZONE)


def run_task_by_id(task_id: int, offset: int = 1):
    """
    Called by APScheduler or manually via the UI.
    Imports the task’s module + function, runs it with the given offset,
    then writes one TaskLog entry, updates Task.last_run/status,
    and returns (status, message, files) so that callers can flash alerts
    and optionally use the generated file paths.
    """
    task = Task.query.get(task_id)
    if not task or not task.enabled:
        return None, "Task is disabled or does not exist."

    start = datetime.now(APP_TIMEZONE).replace(tzinfo=None)
    try:
        module = importlib.import_module(task.module_path)
        fn     = getattr(module, task.function_name)

        # Attempt to run the actual task function
        generated_files = fn(offset=offset)

        # Mark SUCCESS on Task
        task.last_run    = start
        task.last_status = "SUCCESS"
        db.session.add(task)
        db.session.commit()

        # Build a friendly message
        if generated_files:
            # Assume generated_files is a list of filepaths
            filenames = [os.path.basename(f) for f in generated_files]
            user_message = "Generated: " + ", ".join(filenames)
        else:
            user_message = "No files were generated (check templates or source files)."

        # Write one TaskLog row
        log = TaskLog(
            task_id=task.id,
            run_time=start,
            status="SUCCESS",
            message=user_message
        )
        db.session.add(log)
        db.session.commit()

        return "SUCCESS", user_message, generated_files

    except com_error:
        # Excel COM error (e.g. Excel not installed, hung instance)
        task.last_run    = start
        task.last_status = "FAILED"
        db.session.add(task)
        db.session.commit()

        user_message = (
            "Error: Excel could not start. "
            "Make sure Microsoft Excel is installed and no hung instance is open."
        )
        log = TaskLog(
            task_id=task.id,
            run_time=start,
            status="FAILED",
            message=user_message
        )
        db.session.add(log)
        db.session.commit()
        return "FAILED", user_message, []

    except FileNotFoundError as fnf:
        # Missing PDF, Excel, or other file
        task.last_run    = start
        task.last_status = "FAILED"
        db.session.add(task)
        db.session.commit()

        user_message = (
            f"Error: A required file was not found: {fnf.filename}. "
            "Please check that all source files and templates exist."
        )
        log = TaskLog(
            task_id=task.id,
            run_time=start,
            status="FAILED",
            message=user_message
        )
        db.session.add(log)
        db.session.commit()
        return "FAILED", user_message, []

    except EmptyDataError:
        # Pandas read_excel or similar found empty/malformed data
        task.last_run    = start
        task.last_status = "FAILED"
        db.session.add(task)
        db.session.commit()

        user_message = "Error: One of the data sheets was empty or malformed."
        log = TaskLog(
            task_id=task.id,
            run_time=start,
            status="FAILED",
            message=user_message
        )
        db.session.add(log)
        db.session.commit()
        return "FAILED", user_message, []

    except Exception:
        # Catch-all for any other unhandled exception
        task.last_run    = start
        task.last_status = "FAILED"
        db.session.add(task)
        db.session.commit()

        tb = traceback.format_exc().strip().splitlines()
        brief = tb[-1] if tb else "Unknown error."
        user_message = f"Unexpected error: {brief}"

        log = TaskLog(
            task_id=task.id,
            run_time=start,
            status="FAILED",
            message=user_message
        )
        db.session.add(log)
        db.session.commit()
        return "FAILED", user_message, []


def schedule_all_tasks():
    """
    Rebuild APScheduler’s job list from the database’s enabled tasks.
    We do NOT call sched.start() here, since that belongs in app.py’s create_app().
    """
    sched.remove_all_jobs()

    for task in Task.query.filter_by(enabled=True).all():
        if not task.schedule:
            continue

        parts = task.schedule.split()
        if len(parts) != 5:
            # Invalid cron string, skip
            continue

        minute, hour, day, month, dow = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=dow,
            timezone=SCHEDULER_TIMEZONE
        )

        sched.add_job(
            func=run_task_by_id,
            trigger=trigger,
            args=[task.id, task.default_offset],
            id=str(task.id),
            name=task.name,
            replace_existing=True
        )

    # Note: We do NOT call sched.start() here.
    # The Flask app’s create_app() should call sched.start() exactly once.


# In your `dashboard/app.py`, ensure you do:
#
#     with app.app_context():
#         schedule_all_tasks()
#         sched.start()
