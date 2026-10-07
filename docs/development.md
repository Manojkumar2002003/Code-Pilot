# Development Guide

This document contains the practical developer workflow for the current CodePilot repository.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Git

## Backend setup

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

### PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

### Command Prompt
```cmd
.venv\Scripts\activate.bat
```

### macOS/Linux
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Frontend setup

From the repository root:

```bash
cd frontend
npm install
```

Start the development app:

```bash
npm run dev
```

Visit:

```text
http://localhost:5173
```

## Configure environment values

Create the local backend configuration:

```bash
cp .env.example .env
```

For Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The current example file contains local development values for the backend and the frontend API URL. The backend reads the root `.env`, while the frontend can also use a `frontend/.env` file if you need to override the default API URL.

## Start the backend

From the backend directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then verify the health endpoint:

```bash
curl http://localhost:8000/api/health
```

## Run tests

From the root backend folder:

```bash
pytest
```

Use the frontend build as the current validation check:

```bash
cd frontend
npm run build
```

## Local SQLite database

The project creates the database file at `data/codepilot.db` during startup and health checks. The application creates the `data` directory automatically if it does not exist.

## Troubleshooting

### Missing data directory
The database layer creates the `data` directory automatically when the engine initializes. If the directory is missing, restart the backend and verify the app is initializing the database correctly.

### Port collisions
If port 8000 or 5173 is already in use, either stop the conflicting process or adjust the local configuration.

### Frontend API mismatch
Ensure the backend is running and that the frontend is configured to point to the same origin or API URL.

### Dependency drift
Recreate the backend virtual environment if the Python package set becomes inconsistent.
