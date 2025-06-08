# dashboard/app.py

from flask import Flask
from dashboard.models import db
from dashboard.scheduler import schedule_all_tasks, sched
from dashboard.views import main_bp
import config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Required for flash() to work
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change_this_to_something_secret")

    db.init_app(app)

    with app.app_context():
        db.create_all()
        app.config["SCHEDULER"] = sched

        # Build all jobs, then start the scheduler exactly once:
        schedule_all_tasks()
        sched.start()

    app.register_blueprint(main_bp)
    return app
