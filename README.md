# Krishi Rental — Agricultural Equipment Rental Platform

A full-stack Flask application for managing agricultural equipment rental workflows, users, equipment, bookings, and supporting media.

## Overview

Krishi Rental is an application focused on making agricultural equipment discoverable and rentable through a web-based workflow. The repository contains a Flask backend, PostgreSQL integration, Supabase storage integration, server-rendered templates, static assets, and deployment configuration.

## Engineering highlights

- **Flask backend** with structured route handling and reusable authentication/authorization decorators.
- **Role-aware workflows** for administrator, producer, farmer, and quality-control users.
- **PostgreSQL persistence** through `psycopg2` and environment-based `DATABASE_URL` configuration.
- **Supabase integration** for storage and application services.
- **Secure file handling** with extension validation, filename sanitization, size limits, and generated storage paths.
- **Session-based authentication** and role-based route protection.
- **Deployment-ready configuration** using Gunicorn and a Procfile.
- **Environment-based configuration** for secrets and service credentials.

## Architecture

```text
Browser
   │
   ▼
Flask application
   ├── Authentication & role checks
   ├── Equipment / rental workflows
   ├── File upload handling
   └── Business logic
        │
        ├── PostgreSQL database
        └── Supabase Storage
```

## Tech stack

- Python
- Flask
- PostgreSQL
- psycopg2
- Supabase
- Jinja2
- HTML / CSS / JavaScript
- Gunicorn
- python-dotenv

## Project structure

```text
.
├── app.py
├── database.sql
├── requirements.txt
├── Procfile
├── static/
├── templates/
├── homepagebackground/
└── render_update.json
```

## Run locally

```bash
python -m venv .venv
```

Activate the environment and install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables, including the database URL, Supabase credentials, storage bucket, and Flask secret key, then start the application with Flask/Gunicorn according to the deployment configuration.

## Security notes

Do not commit production credentials. Configure secrets through environment variables. Uploaded files are validated and sanitized before being sent to storage.

## Author

**Manvanth M.** — MCA | Full-Stack Development | Machine Learning | Data Analytics
