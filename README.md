# CodePilot

CodePilot is a local-first, human-supervised AI software engineering platform designed to assist developers throughout the software development lifecycle.

The repository currently contains the implemented foundation for the platform and the first complete project-management vertical slice through Sprint 1.10. Autonomous agent orchestration, multi-agent execution, and other advanced AI runtime features are planned future work and are not yet implemented in this codebase.

## Current status

The project is currently in the Sprint 1 project-management phase. Sprint 0 established the application foundation, and Sprint 1 establishes the first end-to-end project lifecycle: create, persist, read, update, delete, and navigate projects.

### Currently implemented
- React + TypeScript frontend with Vite
- FastAPI backend with Python
- Local SQLite persistence through SQLAlchemy
- Project data model, validation, repository, and service layers
- Project CRUD API endpoints
- Project create, list, details, edit, and delete pages
- Project navigation and route flow
- Local health and dependency status endpoints
- Centralized frontend API client
- Loading, error, empty, and not-found UI states
- Local developer environment configuration

### Planned / future capabilities
- Requirement analysis and planning agents
- Architecture and design agents
- Developer and QA automation agents
- LangGraph orchestration
- LLM provider abstraction
- RAG and vector search
- Git integration
- Docker sandbox execution
- Human-in-the-loop review and approval flows
- Production deployment and observability infrastructure

## Sprint 0 — application foundation

Sprint 0 established the base platform architecture and developer workflow.

### Included foundation work
- Frontend application shell and layout
- Sidebar and header layout
- Backend FastAPI application startup and routing
- Local configuration with environment variables
- SQLite and SQLAlchemy database foundation
- Health and dependency checks
- Local system status in the frontend
- Error, loading, and empty state handling
- Local development setup and documentation

### Architecture snapshot

```text
React + TypeScript + Vite
          |
          v
       FastAPI
          |
          v
     SQLAlchemy
          |
          v
       SQLite
```

## Sprint 1 — project management foundation

Sprint 1 establishes the first complete vertical slice of CodePilot: project creation, persistence, retrieval, viewing, updating, deletion, and navigation.

### Feature status

| Feature | Description | Status |
| --- | --- | --- |
| S1.1 | Project Data Model | Complete |
| S1.2 | Project Schemas & Validation | Complete |
| S1.3 | Project Repository / Data Access | Complete |
| S1.4 | Project Service Layer | Complete |
| S1.5 | Project API | Complete |
| S1.6 | Create Project UI | Complete |
| S1.7 | Project List UI | Complete |
| S1.8 | Project Details UI | Complete |
| S1.9 | Project Update & Delete UI | Complete |
| S1.10 | Project Navigation & Routing | Complete |

## Current Sprint 1 architecture

```text
                     User
                      |
                      v
             React Frontend
                      |
             React Router + AppShell
                      |
           Project Pages / Components
                      |
                  API Client
                      |
                    HTTP
                      |
             FastAPI Backend
                      |
                 API Router
                      |
              Project Service
                      |
             Project Repository
                      |
                SQLAlchemy ORM
                      |
                    SQLite
```

### Responsibility of each layer
- React frontend: user-facing project screens and navigation
- API client: centralized fetch logic for project requests
- FastAPI backend: request handling, validation, and responses
- Project service: project business logic and not-found checks
- Project repository: database operations and CRUD behavior
- SQLAlchemy: ORM mapping and persistence behavior
- SQLite: local developer database storage

## Project data flow

### Create project

```text
User
  -> Create Project UI
  -> POST /api/projects
  -> Project Service
  -> Project Repository
  -> SQLAlchemy
  -> SQLite
```

### List projects

```text
User
  -> Projects page
  -> GET /api/projects
  -> FastAPI
  -> Service
  -> Repository
  -> SQLite
  -> React UI
```

### Update project

```text
User
  -> Edit Project page
  -> PATCH /api/projects/{project_id}
  -> Service
  -> Repository
  -> SQLite
```

### Delete project

```text
User
  -> Details page delete flow
  -> DELETE /api/projects/{project_id}
  -> Service
  -> Repository
  -> SQLite
```

## Project API

The project API is implemented in the backend and currently exposes the following endpoints.

### Health endpoints
- GET `/` — backend root response
- GET `/api/health` — backend service health status
- GET `/api/health/dependencies` — backend and database dependency status

### Project endpoints
- POST `/api/projects` — create a project
- GET `/api/projects` — list all projects
- GET `/api/projects/{project_id}` — fetch a single project by ID
- PATCH `/api/projects/{project_id}` — partially update a project
- DELETE `/api/projects/{project_id}` — delete a project

The project request and response model uses the existing Pydantic validation rules:
- project names are required and trimmed
- empty or whitespace-only names are rejected
- descriptions are optional and trimmed
- status values are limited to `active` and `archived`

## Frontend routes

The frontend uses the active route set defined in the application shell:

- `/` — dashboard
- `/projects` — project list
- `/projects/new` — create project
- `/projects/:projectId` — project details
- `/projects/:projectId/edit` — edit project
- `/knowledge` — knowledge page
- `/settings` — settings page

Unknown routes render a not-found page instead of redirecting silently.

## Project capabilities

### Project management
- Create a project
- Persist projects in SQLite
- List all projects
- View project details
- Update project details
- Change project status between active and archived
- Delete projects
- Navigate between project screens
- Display loading, error, empty, and not-found states

## Technology stack

### Frontend
- React
- TypeScript
- Vite
- React Router

### Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy

### Database
- SQLite

### Local validation
- pytest for backend testing
- Vitest for frontend testing

## Project structure

```text
CodePilot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── .venv/
│   ├── pytest.ini
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── ...
├── docs/
│   ├── architecture.md
│   ├── development.md
│   └── roadmap.md
├── data/
├── .env
├── .env.example
├── .gitignore
├── README.md
└── .git
```

## Local development

### Backend setup

From the project root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

#### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

#### Windows Command Prompt
```cmd
.venv\Scripts\activate.bat
```

#### macOS / Linux
```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend setup

From the project root:

```bash
cd frontend
npm install
npm run dev
```

Local URLs used by the current project:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

## Environment configuration

The project uses local environment files for developer setup.

### Backend
The repository includes `.env.example` with the current local defaults:

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

### Frontend
The frontend reads `VITE_API_BASE_URL` for the backend base URL. If a local override is needed, create a frontend-specific `.env` file in `frontend/`.

Do not commit local developer secrets or environment files with credentials.

## Local database

The current implementation uses SQLite for local-first persistence.

- Database file: `data/codepilot.db`
- ORM: SQLAlchemy
- Access layer: repository and service pattern
- Persistence model: project data is stored locally on disk

This is a local development database, not a production deployment database.

## Testing and validation

The repository includes local validation for the current implementation.

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm run test
```

This keeps the project checked against the project CRUD flow and local route behavior without introducing a broader production-ready platform stack.

## Roadmap

### Current documented position
- Sprint 0: foundation complete
- Sprint 1: project management foundation complete through S1.10

### Next milestone
The next area of development is the broader project workspace stage, where the project will expand from a project CRUD foundation into a richer engineering workspace.

Potential future work includes:
- project overview and workspace context
- requirements and architecture views
- task and execution tracking
- human review and approval flows
- execution observability and history
- deeper project lifecycle management

These are future capabilities and are not part of the current implementation.

## Development principles

- Keep the foundation stable while adding new product slices incrementally.
- Preserve the existing layered architecture: model, schema, repository, service, API, UI.
- Prefer local-first development over production infrastructure.
- Keep human review and validation central to future AI workflows.
- Do not introduce autonomous execution capabilities before the platform foundation is complete.

## Summary

CodePilot currently delivers a working local-first foundation and the first complete project-management slice: the backend, database, validation, project API, project UI, and routing flow are implemented and working together.

The project remains intentionally scoped to a local developer workflow while the larger AI software engineering platform vision stays clearly separated as future work.
