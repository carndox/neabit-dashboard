from dashboard.app import create_app
from dashboard.models import db, Task
from tasks import ALL_TASKS

app = create_app()

with app.app_context():
    for name, modpath, func in ALL_TASKS:
        existing = Task.query.filter_by(
            module_path=modpath,
            function_name=func
        ).first()

        if existing:
            existing.name = name
            existing.schedule = "0 0 28 * *"    # always run on the 28th at 00:00
            existing.default_offset = 1
            db.session.add(existing)
        else:
            new_task = Task(
                name=name,
                module_path=modpath,
                function_name=func,
                schedule="0 0 28 * *",   # always run on the 28th at 00:00
                default_offset=1,
            )
            db.session.add(new_task)

    db.session.commit()
    print("Tasks registered in database.")
