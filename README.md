# CodePilot

CodePilot is a local-first, human-supervised multi-agent AI software engineering platform designed to take software requirements through analysis, architecture, planning, development, testing, review, and security validation.

This repository currently contains the foundation for that platform: a working React frontend, a FastAPI backend, local configuration, SQLite persistence, health checks, and basic developer experience tooling.

## Current Status

Sprint 0 establishes the application foundation.

### Current capabilities
- React + TypeScript frontend shell
- FastAPI backend application
- Frontend to backend connectivity
- Environment configuration through .env files
- SQLite local database setup with SQLAlchemy
- Health endpoints and system status page
- Standard loading, error, and empty UI states
- Local development workflow for Windows and Unix-like systems

### Data model and schema separation
- SQLAlchemy `Project` model: persistence layer and database representation
- Pydantic `ProjectCreate` / `ProjectUpdate` / `ProjectResponse`: API contract and validation layer
- Project status is normalized to the canonical `active` / `archived` enum values
### Planned capabilities
- Project creation and editing workflows
- LLM integration
- Gemini or Ollama-based agent orchestration
- LangGraph workflows
- RAG and vector search
- Git-backed project tools
- Docker sandbox execution
- QA and security agents
- Production deployment architecture

## Current Architecture

```text
                    CodePilot
                       │
             ┌─────────┴─────────┐
             │                   │
       React Frontend       FastAPI Backend
             │                   │
             │ HTTP              │
             └─────────┬─────────┘
                       │
                Configuration
                       │
                  SQLAlchemy
                       │
                     SQLite
                       │
              data/codepilot.db
```

### Component responsibilities
- React Frontend: UI shell, navigation, status page, developer-facing screens
- FastAPI Backend: HTTP API and application entrypoint
- Configuration: centralized settings for app name, environment, port, database URL
- SQLAlchemy: database abstraction layer for local SQLite use
- SQLite: local persistence for current development workflow

## Planned Architecture

```text
User
 ↓
React
 ↓
FastAPI
 ↓
LangGraph Orchestrator
 ↓
Requirement Analyst
 ↓
Architect
 ↓
Planner
 ↓
Developer
 ↓
QA
 ↓
Code Review
 ↓
Security
```

This architecture is planned for future Sprints and is not currently implemented in this repository.

## Technology Stack

### Current stack
- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI, Pydantic, SQLAlchemy
- Database: SQLite
- Testing: pytest for backend,
- Tooling: npm for frontend package management

### Planned technologies
- LangGraph
- LLM providers
- Vector databases such as Qdrant
- Sandbox and containerized execution
- Git-aware project workflows
- Production deployment infrastructure

## Project Structure

```text
CodePilot/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── database/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── .venv/
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig*.json
├── data/
│   └── codepilot.db
├── docs/
│   ├── architecture.md
│   ├── development.md
│   └── roadmap.md
├── .env
├── .env.example
├── .gitignore
├── README.md
└── .vscode/
```

### Important directories
- backend/app: FastAPI application code and configuration
- backend/tests: backend regression and API tests
- frontend/src: React application source
- data: local SQLite database files for development
- docs: project documentation and developer guidance

## Prerequisites

Before starting, install:
- Python 3.10+
- Node.js 18+ or an equivalent LTS version
- npm
- Git

Verify installation:

```bash
python --version
node --version
npm --version
git --version
```

## Environment Configuration

This project uses local environment configuration for developer setup.

### Backend configuration
Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The repository includes a working example:

```env
APP_NAME=CodePilot API
APP_ENV=development
DEBUG=true
API_PREFIX=/api
HOST=127.0.0.1
PORT=8000
DATABASE_URL=sqlite:///./data/codepilot.db
VITE_API_BASE_URL=http://localhost:8000
```

Important notes:
- `.env` is local developer configuration and should not be committed.
- `VITE_*` variables are exposed to the browser and must never contain secrets.
- If you want to override the frontend API URL, create a separate `frontend/.env` file with `VITE_API_BASE_URL=http://localhost:8000`.

## Backend Setup

From the project root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows Command Prompt
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

## Frontend Setup

From the project root:

```bash
cd frontend
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Expected local URL:
- http://localhost:5173

## Backend Startup

From the backend directory with the virtual environment active:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected API base URL:
- http://localhost:8000

The backend exposes the following available routes:
- GET /
- GET /api/health
- GET /api/health/dependencies

## Database

The current project uses SQLite for local development.

- Database file: `data/codepilot.db`
- Database layer: SQLAlchemy
- File generation: auto-created by the app when the database is initialized
- Local runtime data: tracked in `.gitignore`

This is a local-first foundation. The current architecture intentionally keeps the database simple while future Sprints decide how project data and agent state should evolve.

## API

### GET /api/health
Purpose: confirm the backend is running and responding.

Example response:

```json
{
  "status": "ok",
  "service": "codepilot-api"
}
```

### GET /api/health/dependencies
Purpose: report backend and database health for the current local environment.

Example response:

```json
{
  "status": "healthy",
  "environment": "development",
  "service": "codepilot-api",
  "dependencies": {
    "backend": { "status": "healthy", "type": "fastapi" },
    "database": { "status": "healthy", "type": "sqlite" }
  }
}
```

## System Status

The React application includes a Settings page that shows the current local system status.

It reports:
- Backend status
- Database status
- Environment status
- Last checked time

The page supports manual refresh and displays loading, error, and empty states.

## Testing

### Backend tests
From the backend directory:

```bash
pytest
```

The repository currently includes backend API and dependency-health checks in `backend/tests/test_main.py`.

### Frontend tests
No frontend test framework is currently configured in this project. Frontend validation is performed through `npm run build`.

## Troubleshooting

### Backend does not start
Check:
- Python virtual environment is active
- `requirements.txt` has been installed
- the `.env` file exists and is valid
- port 8000 is not already in use

### Frontend cannot connect to backend
Check:
- backend is running on port 8000
- `VITE_API_BASE_URL` matches the backend URL
- CORS rules are enabled in the backend app
- the frontend is using the local dev server port 5173

### Database issue
Check:
- the `data` directory exists
- `DATABASE_URL` points to the expected SQLite file
- the database file is writable by the current user

### Dependency installation issue
If setup is inconsistent, recreate the backend environment:

```bash
cd backend
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Developer Workflow

1. Pull the latest repository state.
2. Create or activate the backend virtual environment.
3. Install backend dependencies.
4. Configure `.env` for local development.
5. Start the backend.
6. Configure or override the frontend API URL if needed.
7. Install frontend dependencies.
8. Start the frontend.
9. Run backend tests and frontend build checks.
10. Implement the next feature incrementally.
11. Review changes and commit them.

## Development Principles

### Incremental development
Features are added in small, testable increments rather than large rewrites.

### Preserve existing architecture
The project keeps working foundations stable while adding new capabilities.

### Reuse existing services/components
New features should integrate with the current backend and frontend patterns instead of duplicating logic.

### Local-first
The current system is designed to work reliably on a local developer machine before production infrastructure is introduced.

### Human-supervised AI
Future agents should operate under explicit supervision and should not execute unrestricted actions without review.

### Security by design
As agent-based workflows grow, sandboxing, validation, and review gates should be introduced deliberately.

## Sprint 0 Completion Checklist

Sprint 0 — Project Foundation

- [x] Frontend created
- [x] Backend created
- [x] Application shell
- [x] Frontend/backend connectivity
- [x] Configuration system
- [x] SQLite foundation
- [x] System health
- [x] Error/loading handling
- [x] Documentation

Status: Sprint 0 — Project Foundation = COMPLETE

## Documentation

- Architecture overview: [docs/architecture.md](docs/architecture.md)
- Development guide: [docs/development.md](docs/development.md)
- Roadmap: [docs/roadmap.md](docs/roadmap.md)

## Clean Setup Verification

A new developer should follow this sequence:

1. Clone the repository.
2. Create the backend `.env` from `.env.example`.
3. Create and activate the backend virtual environment.
4. Install backend dependencies with `pip install -r requirements.txt`.
5. Start the backend with `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
6. Create a frontend `.env` if you need a custom `VITE_API_BASE_URL`.
7. Install frontend dependencies with `npm install`.
8. Start the frontend with `npm run dev`.
9. Open http://localhost:5173.
10. Check system status from the app and verify backend health endpoints.
11. Run backend tests with `pytest`.
12. Run frontend compile validation with `npm run build`.

## Commit Recommendation

```bash
git add .
git commit -m "docs: complete sprint 0 documentation"
```


