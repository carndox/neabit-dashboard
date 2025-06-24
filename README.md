# NEA Dashboard

This project provides a web based dashboard for orchestrating monthly National Electrification Administration reports. It combines Flask, APScheduler and SQLAlchemy to schedule and track Excel based report generation tasks. OCR helpers use **pytesseract** and **pdf2image** to pull values from PDF forms, while **xlwings** automates Microsoft Excel.

## Features

* Task management with a SQLite backend
* Background scheduling via APScheduler
* Manual or scheduled execution of five reporting steps
* Email notifications with optional reply polling
  that filters out old or unrelated emails
* Configurable timezone for scheduler and database timestamps
* Modern Bootswatch 5 based UI with optional dark mode
* Simple JSON API for integrations

## Requirements

The application was developed for Windows with Python 3.11. The following packages are required:

```
Flask
Flask-SQLAlchemy
APScheduler
pandas
xlwings
pdf2image
Pillow
pytesseract
python-dotenv
pywin32 ; sys_platform == "win32"
```

External dependencies such as Tesseract OCR, Microsoft Excel and Poppler are also needed.

## Usage

1. Copy `.env.example` to `.env` and fill in email credentials, file paths and
   your preferred `APP_TIMEZONE`. The application uses `python-dotenv` so these
   values are automatically loaded when the server starts.
2. Create the SQLite database and initial tasks:

```bash
python populate_tasks.py
```

3. Start the development server:

```bash
python run.py
```

Visit `http://localhost:5000` to view and run tasks.

## Security

**Do not commit credentials.** Store all sensitive values in the `.env` file.
`config.py` reads from this file on startup so secrets never reside in source
code.

## License

MIT
