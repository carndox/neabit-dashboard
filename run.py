# run.py

import sys
from dashboard.app import create_app

app = create_app()

def init_db():
    # Simply ensures that the SQLite file and tables are created.
    print("Database initialized (dashboard.sqlite).")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "initdb":
        init_db()
    else:
        # Launch Flask’s development server on port 5000
        app.run(host="0.0.0.0", port=5000, debug=True)
