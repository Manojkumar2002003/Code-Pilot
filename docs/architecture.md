# Architecture

This document describes the current architecture of the CodePilot repository and separates it clearly from the future agentic architecture that is planned for later Sprints.

## Current Architecture

```text
                         CodePilot
                            │
             ┌──────────────┴──────────────┐
             │                             │
      React + TypeScript              FastAPI
             │                             │
       API Service                  Configuration
             │                             │
             └──────── HTTP ───────────────┤
                                           │
                                      SQLAlchemy
                                           │
                                         SQLite
                                           │
                                  data/codepilot.db
```

### Frontend
The frontend is a Vite + React + TypeScript application. It renders the developer shell, navigation, and the current Settings/System Status page. It communicates with the backend through a typed API service.

### API client
The frontend service layer is the only point where browser code calls the backend. It keeps HTTP requests centralized and makes it easier to normalize errors consistently.

### FastAPI backend
The backend is the application boundary that serves the current health API and is responsible for local startup behavior, CORS settings, and end-to-end validation logic.

### Configuration layer
The backend settings object reads local configuration values from `.env` and exposes them via a central configuration module. The app currently uses app name, environment, debug flag, prefix, host, port, and database URL settings.

### SQLAlchemy
The ORM layer is used to provide a database abstraction and keep the project flexible for future database choices.

### SQLite
SQLite is the current local persistence layer. The database file is created in the repository's `data` directory and is used for local development validation.

## Planned Architecture

```text
User
 ↓
React
 ↓
FastAPI
 ↓
LangGraph
 ↓
┌───────────────────────────────────┐
│ Requirement Analyst               │
│ Architect                         │
│ Planner                           │
│ Developer                         │
│ QA                                │
│ Code Review                       │
│ Security                          │
└───────────────────────────────────┘
 ↓
Tools
 ├── Filesystem
 ├── Git
 ├── Docker Sandbox
 └── RAG
```

This planned architecture is not implemented yet. It represents the future direction of the project after the foundation is complete.

## Architectural Notes

- The current architecture is intentionally thin and local-first.
- The system does not require external cloud services to run in development.
- The current backend and frontend are separate but intentionally small and understandable.
- Future features should be added incrementally so the current foundation remains stable.
