# dashboard/views.py

from flask import (
    Blueprint, render_template, redirect,
    url_for, request, flash, current_app, jsonify
)
from dashboard.models import db, Task, TaskLog
from dashboard.scheduler import run_task_by_id, schedule_all_tasks
from nea_reports import run_all, send_email
import uuid
from threading import Thread

main_bp = Blueprint("main", __name__)

# Simple in-memory progress tracking for async runs
progress_map = {}


def _run_task_background(run_id: str, task: Task, offset: int):
    """Helper to run a single task in a thread and update progress."""
    progress_map[run_id] = {
        "current": 0,
        "total": 1,
        "message": f"Starting {task.name}",
        "done": False,
    }
    status, message, _ = run_task_by_id(task.id, offset=offset)
    progress_map[run_id].update({"current": 1, "message": message, "done": True, "status": status})


def _run_all_background(run_id: str, offset: int):
    tasks = Task.query.filter_by(enabled=True).order_by(Task.id).all()
    total = len(tasks)
    progress_map[run_id] = {
        "current": 0,
        "total": total,
        "message": "Starting...",
        "done": False,
    }
    all_generated_files = []
    for idx, task in enumerate(tasks, 1):
        progress_map[run_id]["message"] = f"Running {task.name}"
        status, message, files = run_task_by_id(task.id, offset=offset)
        if files:
            all_generated_files.extend(files)
        progress_map[run_id]["current"] = idx
        progress_map[run_id]["message"] = f"{task.name}: {status}"

    if all_generated_files:
        from datetime import datetime, timedelta
        d = datetime.today().replace(day=1) - timedelta(days=1)
        mmyy = d.strftime("%B %Y")
        subject = f"Monthly NEA Reports – {mmyy}"
        body = (
            f"Attached are all updated NEA workbooks for {mmyy}.\n\n"
            "May I proceed with submission? Reply with yes/no."
        )
        try:
            send_email(subject, body, all_generated_files)
            progress_map[run_id]["message"] = f"Email sent with {len(all_generated_files)} attachments"
        except Exception as e:
            progress_map[run_id]["message"] = f"Email failed: {e}"
    else:
        progress_map[run_id]["message"] = "No files generated"

    progress_map[run_id]["done"] = True


@main_bp.route("/")
def index():
    tasks = Task.query.order_by(Task.name).all()
    scheduler = current_app.config["SCHEDULER"]
    return render_template("task_list.html", tasks=tasks, scheduler=scheduler)


@main_bp.route("/task/<int:task_id>")
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    logs = task.logs.order_by(TaskLog.run_time.desc()).limit(20).all()
    return render_template("task_detail.html", task=task, logs=logs)


@main_bp.route("/task/<int:task_id>/run", methods=["POST"])
def task_run_now(task_id):
    task = Task.query.get_or_404(task_id)
    try:
        offset = int(request.form.get("offset", task.default_offset))
        if offset < 1:
            offset = task.default_offset
    except ValueError:
        offset = task.default_offset

    status, message, _ = run_task_by_id(task.id, offset=offset)
    flash(f"“{task.name}” has been queued (offset={offset}).", "success")
    return redirect(url_for("main.task_detail", task_id=task.id))


@main_bp.route("/task/<int:task_id>/run_async", methods=["POST"])
def task_run_async(task_id):
    task = Task.query.get_or_404(task_id)
    try:
        offset = int(request.form.get("offset", task.default_offset))
        if offset < 1:
            offset = task.default_offset
    except ValueError:
        offset = task.default_offset

    run_id = str(uuid.uuid4())
    th = Thread(target=_run_task_background, args=(run_id, task, offset))
    th.start()
    return jsonify({"run_id": run_id})


@main_bp.route("/task/<int:task_id>/toggle", methods=["POST"])
def task_toggle_enabled(task_id):
    task = Task.query.get_or_404(task_id)
    task.enabled = not task.enabled
    db.session.commit()
    schedule_all_tasks()
    state = "Enabled" if task.enabled else "Disabled"
    flash(f"“{task.name}” is now {state}.", "info")
    return redirect(url_for("main.index"))


# ← Make sure this exact route exists:
@main_bp.route("/task/<int:task_id>/clear_logs", methods=["POST"])
def task_clear_logs(task_id):
    """
    Delete all logs for a given task, but keep the task itself.
    """
    TaskLog.query.filter_by(task_id=task_id).delete()
    db.session.commit()
    flash("Logs cleared for this task.", "warning")
    return redirect(url_for("main.task_detail", task_id=task_id))


@main_bp.route("/run_all", methods=["POST"])
def run_all_tasks():
    """
    Trigger every enabled task sequentially. Each task is executed via
    ``run_task_by_id`` so individual results are logged in the database.
    After all tasks finish, send one consolidated email if any files were
    generated.
    """
    # 1) Determine offset from form
    try:
        offset = int(request.form.get("offset", 1))
        if offset < 1:
            offset = 1
    except ValueError:
        offset = 1

    # 2) Run each enabled task and collect generated file paths
    all_generated_files = []
    for task in Task.query.filter_by(enabled=True).order_by(Task.id).all():
        status, message, files = run_task_by_id(task.id, offset=offset)
        if files:
            all_generated_files.extend(files)

    # 3) If any files came back, send one email with all attachments
    if all_generated_files:
        # Build subject/body exactly as you did in your original script
        from datetime import datetime, timedelta

        d = datetime.today().replace(day=1) - timedelta(days=1)
        mmyy = d.strftime("%B %Y")
        subject = f"Monthly NEA Reports – {mmyy}"
        body = (
            f"Attached are all updated NEA workbooks for {mmyy}.\n\n"
            "May I proceed with submission? Reply with yes/no."
        )

        try:
            send_email(subject, body, all_generated_files)
            flash(
                f"Run All complete—email sent with {len(all_generated_files)} attachments.",
                "success"
            )
        except Exception as e:
            flash(f"Email sending failed: {e}", "danger")
    else:
        # No files were generated by any of the individual tasks
        flash("Run All complete—no files were generated, so no email was sent.", "warning")

    return redirect(url_for("main.index"))


@main_bp.route("/run_all_async", methods=["POST"])
def run_all_async():
    try:
        offset = int(request.form.get("offset", 1))
        if offset < 1:
            offset = 1
    except ValueError:
        offset = 1

    run_id = str(uuid.uuid4())
    th = Thread(target=_run_all_background, args=(run_id, offset))
    th.start()
    return jsonify({"run_id": run_id})


@main_bp.route("/progress/<run_id>")
def progress(run_id):
    data = progress_map.get(run_id)
    if not data:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)
