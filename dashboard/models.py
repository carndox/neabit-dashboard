from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import APP_TIMEZONE

def now_local():
    return datetime.now(APP_TIMEZONE).replace(tzinfo=None)

db = SQLAlchemy()

class Task(db.Model):
    __tablename__ = "tasks"
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), unique=True, nullable=False)
    module_path    = db.Column(db.String(200), nullable=False)
    function_name  = db.Column(db.String(100), nullable=False)
    schedule       = db.Column(db.String(50), nullable=True)   # cron string, e.g. "0 3 1 * *"
    default_offset = db.Column(db.Integer, default=1, nullable=False)  # auto‐run offset
    last_run       = db.Column(db.DateTime, nullable=True)
    last_status    = db.Column(db.String(10), nullable=True)  # "SUCCESS" or "FAILED"
    enabled        = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=now_local)
    updated_at     = db.Column(db.DateTime, default=now_local, onupdate=now_local)

    logs = db.relationship("TaskLog", backref="task", lazy="dynamic")

class TaskLog(db.Model):
    __tablename__ = "task_logs"
    id       = db.Column(db.Integer, primary_key=True)
    task_id  = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    run_time = db.Column(db.DateTime, default=now_local)
    status   = db.Column(db.String(10), nullable=False)  # "SUCCESS" or "FAILED"
    message  = db.Column(db.Text, nullable=True)