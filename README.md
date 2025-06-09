# NEA Dashboard

This project provides a web based dashboard for orchestrating monthly National Electrification Administration reports. It combines Flask, APScheduler and SQLAlchemy to schedule and track Excel based report generation tasks. OCR helpers use **pytesseract** and **pdf2image** to pull values from PDF forms, while **xlwings** automates Microsoft Excel.

## Features

* Task management with a SQLite backend
* Background scheduling via APScheduler
* Manual or scheduled execution of five reporting steps
* Email notifications with optional reply polling
* Minimal Bootstrap 4 based UI

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

1. Copy `.env.example` to `.env` and fill in email credentials and file paths.
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

**Do not commit credentials**. The sample configuration file `config.py` contains plain-text passwords and should be replaced with environment variables.

## License

MIT
