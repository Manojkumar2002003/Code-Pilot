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

## Cloud LLM Providers, Model Registry & Intelligent Failover (S3.1 & S3.2)

CodePilot integrates five cloud-hosted LLM providers behind a unified provider-independent interface, supported by a centralized model registry, lightweight health checks, and an intelligent failover routing coordinator.

### Supported Cloud Providers

CodePilot strictly uses cloud-hosted inference. Local Ollama or local model runners are strictly prohibited.

1. **Google Gemini API**: Native Google AI Studio endpoint (`https://generativelanguage.googleapis.com/v1beta`), API key header (`x-goog-api-key`), structured output schema support, and token usage metadata.
2. **OpenRouter**: OpenRouter routing gateway (`https://openrouter.ai/api/v1`), Bearer token authentication, optional routing headers (`HTTP-Referer`, `X-Title`), usage metadata with native pricing tier representation, and credit exhaustion (HTTP 402) detection.
3. **NVIDIA NIM**: NVIDIA cloud-hosted API (`https://integrate.api.nvidia.com/v1`), Bearer token authentication, OpenAI-compatible chat completions interface.
4. **Groq**: High-throughput cloud inference (`https://api.groq.com/openai/v1`), Bearer token authentication, OpenAI-compatible chat completions interface with hardware-accelerated rate limit headers.
5. **Ollama Cloud**: Remote cloud-hosted inference (`https://cloud.ollama.com` or custom remote gateway). Supports native `/api/chat` and `/v1/chat/completions` protocols. Localhost and loopback addresses (`127.0.0.1`, `localhost`, LAN IPs) are strictly prohibited and rejected by adapter validation.

### Official Provider Documentation & Consoles

| Provider | Official Documentation | Official Console (Obtain API Key) |
| --- | --- | --- |
| **Google Gemini** | [Gemini API Docs](https://ai.google.dev/gemini-api/docs) | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| **OpenRouter** | [OpenRouter Docs](https://openrouter.ai/docs) | [OpenRouter Keys](https://openrouter.ai/keys) |
| **NVIDIA NIM** | [NVIDIA API Catalog](https://build.nvidia.com/models) | [NVIDIA Build Console](https://build.nvidia.com/) |
| **Groq** | [Groq Cloud Docs](https://console.groq.com/docs) | [Groq Console Keys](https://console.groq.com/keys) |
| **Ollama Cloud** | [Ollama Cloud Docs](https://docs.ollama.com/) | [Ollama Cloud Portal](https://ollama.com/) |

### Environment Variables

Configure provider credentials and failover policies in your local `.env` file:

```env
# Primary Provider Configuration
LLM_DEFAULT_PROVIDER=gemini
LLM_REQUEST_TIMEOUT_SECONDS=60.0
LLM_MAX_OUTPUT_TOKENS=4096

# Failover & Routing Policies
LLM_FAILOVER_ENABLED=true
LLM_PROVIDER_PRIORITY=["gemini", "openrouter", "groq", "nvidia_nim", "ollama_cloud"]
LLM_MAX_FAILOVER_ATTEMPTS=3
LLM_TOTAL_REQUEST_DEADLINE_SECONDS=120.0
LLM_CIRCUIT_BREAKER_COOLDOWN_SECONDS=60.0

# 1. Google Gemini
LLM_GEMINI_API_KEY=
LLM_GEMINI_MODEL=gemini-2.0-flash
LLM_GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
LLM_GEMINI_ENABLED=true

# 2. OpenRouter
LLM_OPENROUTER_API_KEY=
LLM_OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
LLM_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_OPENROUTER_ENABLED=true

# 3. NVIDIA NIM
LLM_NVIDIA_NIM_API_KEY=
LLM_NVIDIA_NIM_MODEL=meta/llama-3.1-8b-instruct
LLM_NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_NVIDIA_NIM_ENABLED=true

# 4. Groq
LLM_GROQ_API_KEY=
LLM_GROQ_MODEL=llama-3.1-8b-instant
LLM_GROQ_BASE_URL=https://api.groq.com/openai/v1
LLM_GROQ_ENABLED=true

# 5. Ollama Cloud (Cloud remote endpoints only; no localhost)
LLM_OLLAMA_CLOUD_API_KEY=
LLM_OLLAMA_CLOUD_MODEL=llama3.1:latest
LLM_OLLAMA_CLOUD_BASE_URL=https://cloud.ollama.com
LLM_OLLAMA_CLOUD_ENABLED=false
```

### Model Registry & Verification

The centralized `ModelRegistry` maintains verified catalog entries for each provider:
- **Capabilities**: Structured output (`json_mode`), tool calling, streaming.
- **Limits**: Verified context window (e.g. 1,048,576 for Gemini 2.0 Flash; 131,072 for Groq Llama 3.1) and maximum output tokens.
- **Pricing & Tier**: Distinguishes verified free-tier models (e.g. OpenRouter `:free`, Gemini free-tier) from standard cloud tiers.
- **Unknown Attributes**: Fields that cannot be verified from official docs are marked `None` / unknown rather than invented.
- Dynamic registration allows runtime or user-defined models without requiring code changes.

### Intelligent Failover & Circuit Breaker Architecture

The router layer wraps provider adapters to guarantee high-reliability execution:

1. **Candidate Filtering**: Only providers that are enabled, configured with valid API keys, not tripped by a circuit breaker, and whose selected model meets all required capabilities (e.g., structured JSON) and context length are considered.
2. **Prioritized Routing**: Candidates are evaluated according to `LLM_PROVIDER_PRIORITY`.
3. **Error Classification**:
   - *Failover Eligible*: HTTP 429 (rate limits), HTTP 402 / quota exhaustion, HTTP 504 (gateway timeouts), network errors (HTTP 502/connect failures), transient server crashes (500/503), and HTTP 404 (model unavailable).
   - *Terminal / Non-Eligible*: HTTP 400 (malformed request), HTTP 401/403 (invalid API key / unauthorized), and unsupported capabilities. These terminate immediately with actionable error details to prevent wasted retry quota.
4. **Circuit Breaker**: When a provider encounters a transient or rate-limit failure, it enters an active cooldown for `LLM_CIRCUIT_BREAKER_COOLDOWN_SECONDS` (or provider's `Retry-After` header if longer). Subsequent requests bypass tripped providers automatically.
5. **Bounded Execution & Deadlines**: Requests enforce `LLM_MAX_FAILOVER_ATTEMPTS` and `LLM_TOTAL_REQUEST_DEADLINE_SECONDS`. If total elapsed time exceeds the deadline, failover halts and reports timeout.
6. **Task Semantics & Context Preservation**: Alternate models must satisfy capability requirements (such as structured JSON). Requests that exceed an alternate model's context window are rejected with clear capability errors rather than silently truncated.
7. **Disabling Failover**: Set `LLM_FAILOVER_ENABLED=false` in `.env`, or submit an `LLMRequest` with an explicit `provider` and `failover=False`.

### Health & Monitoring Endpoints

- `GET /api/llm/status`: Returns configured state, default provider, enabled providers, and circuit-breaker status. API keys are completely redacted.
- `GET /api/llm/models`: Returns catalog of all supported models, capabilities, and context limits.
- `POST /api/llm/health/check`: Actively polls lightweight provider metadata endpoints (e.g., `/v1beta/models` for Gemini, `/api/v1/auth/key` for OpenRouter, `/v1/models` for Groq/NVIDIA NIM, `/api/tags` for Ollama Cloud) without generating tokens or incurring inference quota.
- `POST /api/llm/generate`: Sends an inference request through the intelligent failover coordinator and returns normalized responses with detailed failover telemetry (`provider`, `model`, `failover_metadata`).

### Running Tests Without Real Credentials

All tests execute offline using deterministic mocked HTTP transports without making live network calls or consuming API credits:

```bash
cd backend
python -m pytest
```

### Troubleshooting

- **Authentication Failure (`401 / 403`)**: Ensure the API key in `.env` is correct and active in the provider's developer console. The router marks the provider as `AUTH_FAILURE` and avoids retry loops.
- **Rate Limits (`429`)**: The router will respect `Retry-After` headers and fail over to the next configured provider in priority. Check provider tier limits if multiple providers exhaust capacity.
- **Quota Exhaustion (`402` or quota errors)**: Verify whether free-tier credits or account quotas have expired. Transition priority to another configured provider.
- **Capability Mismatch (`UNSUPPORTED_CAPABILITY`)**: The request asked for features (e.g. strict JSON mode) unsupported by the candidate model. The router skips incompatible models.
- **Ollama Cloud Localhost Rejection**: If you see `Ollama Cloud endpoint cannot point to localhost or loopback address`, change `LLM_OLLAMA_CLOUD_BASE_URL` to a valid remote cloud URL.

## Project Context and Requirement Generation Schemas (S3.3)

S3.3 establishes the validated data contracts and context preparation layer that CodePilot will use for future AI-powered requirement generation (Requirement Analyst agent).

### Project Context Schema & Builder

The `ProjectContext` schema provides a typed snapshot of project data and user input:
- **Project Boundary Isolation**: Every context object is bound to a single `project_id`. Clarifications or inputs from other projects are strictly rejected via `CrossProjectContextError`.
- **Data Provenance**: Every entry tracks its origin using `ContextProvenance` (`PROJECT_METADATA`, `USER_CLARIFICATION`, `APPROVED_REQUIREMENT`, `USER_GOAL`).
- **Approved Requirement Refinement**: Existing requirements from the database are only loaded when `include_approved_requirements=True` is explicitly specified by the caller (e.g. for requirement refinement or regeneration), and only requirements with status `approved` are summarized.
- **Service Layer**: `ProjectContextBuilder` extracts repository models, validates project boundaries, records provenance, and outputs a validated `ProjectContext`.

### Clarification Contracts

Ambiguities in project descriptions are modeled using typed clarification schemas:
- `ClarificationQuestion`: Contains a stable identifier (`CQ-1`), question prompt, rationale explaining why the information matters, domain category, required flag, and suggested answer options.
- `ClarificationAnswer`: Captures user responses, selected options, and timestamp, validating project association.

### Requirement Generation Specification Schemas

The generated output is structured into specialized proposal models under `RequirementGenerationResult`:
- **Functional Requirements (`ProposedFunctionalRequirement`)**: Stable identifier (`FR-1`), title, description, expected system behavior, actor role, priority, acceptance criteria, dependencies, assumptions, and unresolved questions.
- **Non-Functional Requirements (`ProposedNonFunctionalRequirement`)**: Stable identifier (`NFR-1`), title, description, quality category (`NFRCategory`: Performance, Security, Reliability, Scalability, Accessibility, Maintainability, Availability, Compliance), priority, measurable target metric (`target_metric`), and an `is_target_unresolved` flag when the user has not specified a concrete threshold.
- **User Stories (`ProposedUserStory`)**: Agile format ("As a [actor], I want to [action], so that [benefit]"), verification criteria, and cross-references to requirement IDs.
- **Business Rules (`ProposedBusinessRule`)**: Business constraints with explicit provenance tracking (`USER_EXPLICIT` vs `MODEL_INFERRED`).
- **Dependencies & Assumptions (`ProposedDependency`, `ProposedAssumption`)**: Directed dependency graphs (`source_id` -> `target_id`) and unresolved operational hypotheses.

### Separation of Proposed vs. Approved Requirements

CodePilot strictly separates AI-generated proposals from persisted database records:
- **Proposal Review Lifecycle**: Proposals utilize an independent lifecycle (`ProposalReviewStatus`: `DRAFT`, `ACCEPTED`, `REJECTED`, `MODIFIED`).
- **No Automatic Persistence**: Generating proposals does NOT save them to the database. Rejected suggestions cannot be silently persisted.
- **Controlled Conversion**: Only proposals reviewed and transitioned to `ACCEPTED` or `MODIFIED` can be converted into `RequirementCreate` via `proposal.to_requirement_create()`. Attempting to convert draft or rejected proposals raises `ProposalLifecycleError`.
- **Referential Integrity**: `RequirementGenerationResult` validates that all IDs are unique across collections and that all story, rule, and dependency references map to valid proposed requirement IDs within the same specification.

### Integration with LLM Foundation

- `RequirementGenerationRequest.to_llm_request()` converts project context and scoping instructions into a provider-independent `LLMRequest` with JSON Schema structured output targeting `RequirementGenerationResult`.
- `RequirementGenerationResult.from_llm_response()` safely deserializes and validates raw provider output (structured dict or markdown JSON text) against the Pydantic schema boundary.

## Requirement Analyst Engine (S3.4)

S3.4 implements the core Requirement Analyst Agent (`RequirementAnalystAgent`) located in `backend/app/agents/requirement_analyst.py`, responsible for transforming user project ideas and context into structured software requirements specifications.

### Architecture & Agent Organization

- **Agent Package (`backend/app/agents/`)**: The core agent logic resides in `RequirementAnalystAgent` (`requirement_analyst.py`) alongside specialized system prompts (`prompts.py`).
- **Service Facade (`backend/app/services/requirement_analyst.py`)**: A lightweight service layer facade delegates directly to the agent in `app.agents` to maintain clean separation of concerns and backward compatibility.
- **Provider-Independent Routing**: Operates through `LLMRouter` (S3.2) utilizing remote cloud LLM providers (Google Gemini, OpenRouter, NVIDIA NIM, Groq, Ollama Cloud) with automatic failover, circuit breaking, and capability matching.

### Generation Modes

The agent supports three generation workflows governed by `GenerationMode`:
1. **Initial (`initial`)**: First-pass requirement generation from project description, domain goals, and constraints. Identifies ambiguities and formulates actionable `ClarificationQuestion` items.
2. **Refinement (`refinement`)**: Ingests user-answered clarification questions (`clarification_answers`) and supplemental guidance to refine existing draft proposals without losing previous decisions.
3. **Regeneration (`regeneration`)**: Scopes or re-generates proposals while preserving approved database requirements loaded into `ProjectContext`, preventing duplication or contradictory specifications.

### Reliability & Resilience Safeguards

- **Context Sufficiency Pre-validation**: Validates that project descriptions contain sufficient information (>= 15 characters, >= 3 distinct words) before making remote LLM calls, raising `InsufficientContextError` (HTTP 400) when context is deficient.
- **Context Window Budgeting**: Computes conservative token estimates against candidate model context limits, raising `ContextWindowExceededError` (HTTP 400) if the payload risks truncation or overflow.
- **Bounded Repair Loop**: If an LLM response produces malformed JSON or fails Pydantic schema validation, the agent executes up to `max_repair_attempts` (default 1) corrective requests providing specific Pydantic validation errors to the model before failing with `GenerationSchemaValidationError`.
- **Failover & Telemetry Tracking**: Propagates router failover metadata, token usage, latency, repair counts, and provider information in `GenerationExecutionMetadata`.
- **Strict Separation of Proposed vs. Persisted Data**: AI proposals remain purely in memory as `DRAFT` items and are never persisted to the database by the analyst engine.

## Clarification and Iterative Requirement Generation (S3.5)

S3.5 implements the clarification session lifecycle, answer management, context updating, and iterative refinement engine for CodePilot's Requirement Analyst.

### Clarification Session Lifecycle

Clarification sessions track the iterative dialogue between human developers and the Requirement Analyst Agent:
- **Session Lifecycle States**:
  - `awaiting_clarification`: Initial state when clarification questions exist and require developer input.
  - `ready_for_refinement`: All required questions (or optional questions) have been answered and the specification is ready to refine.
  - `refinement_in_progress`: An LLM refinement run is actively executing. Blocks concurrent duplicate executions with HTTP 409.
  - `completed`: Refinement succeeded and no further clarification questions remain.
  - `failed`: LLM call or validation failed; submitted answers are preserved intact, enabling immediate retry without re-entering answers.
  - `cancelled`: Session cancelled by developer.
- **State Transition Guardrails**: Enforces valid state transitions and rejects out-of-order operations.

### Clarification Question & Answer Management

- **Question Validation**: Rejects duplicate question submissions and questions not associated with the active session.
- **Required vs. Optional Questions**: Required questions must be answered before refinement proceeds; optional questions never block refinement.
- **Incremental Answer Preservation**: Answers are preserved incrementally across submissions unless explicitly modified by the user.
- **Project Isolation**: Every session and answer is bound strictly to `project_id`. Cross-project submissions are rejected with `ClarificationSessionProjectMismatchError`.

### Clarification-Aware Context Updating & Conflict Detection

- **Context Assembly**: When preparing for refinement, `ProjectContextBuilder` combines:
  - Original project description and metadata.
  - User-stated high-level goals.
  - Clarification questions and user responses (with provenance tracking).
  - Previously proposed draft requirements from the preceding revision.
  - Existing approved database requirements (only when explicitly requested).
- **Precedence & Conflict Surfacing**: User answers take strict precedence over AI model assumptions. If a user answer conflicts with an earlier stated goal or fact, `detect_context_conflicts` surfaces the conflict as an actionable warning rather than silently overriding it.

### Generation Revisions & History Preservation

- **Revision Traceability**: Every refinement iteration creates an immutable `GenerationRevision` recording `generation_id`, `parent_generation_id`, `revision_number` (1, 2, 3...), summary, and complete specification payload.
- **Requirement Diffing**: The service computes a structured `RequirementDiffSummary` comparing the previous generation against the new generation, categorizing requirements as `new`, `changed`, `retained`, or `removed`.
- **Preservation of Approved Requirements**: Existing approved requirements in the database remain completely untouched and are never modified, deleted, or converted by refinement iterations.

### Concurrency & Failure Recovery

- **Race Condition Prevention**: If a refinement request arrives while a session is in `refinement_in_progress`, the service immediately raises `ClarificationSessionConcurrencyError` (HTTP 409).
- **Safe Failure Recovery**: When a provider encounters timeouts, rate limits, or transient outages, the session transitions to `failed` and records `last_error`. Submitted answers remain safely stored in the database, allowing users to retry refinement with a single click.

### API Endpoints

- `POST /api/projects/{project_id}/clarifications/sessions`: Initialize a clarification session.
- `GET /api/projects/{project_id}/clarifications/sessions`: List sessions for a project.
- `GET /api/projects/{project_id}/clarifications/sessions/{session_id}`: Retrieve session details and status.
- `GET /api/projects/{project_id}/clarifications/sessions/{session_id}/questions`: Retrieve questions (supports `?pending_only=true`).
- `POST /api/projects/{project_id}/clarifications/sessions/{session_id}/answers`: Submit answers to clarification questions.
- `POST /api/projects/{project_id}/clarifications/sessions/{session_id}/refine`: Trigger iterative requirement refinement.
- `GET /api/projects/{project_id}/clarifications/sessions/{session_id}/result`: Retrieve the latest requirement specification.
- `GET /api/projects/{project_id}/clarifications/sessions/{session_id}/revisions`: List historical generation revisions.
- `GET /api/projects/{project_id}/clarifications/sessions/{session_id}/revisions/{revision_number}`: Retrieve a specific historical revision.

## Requirement Generation API (S3.6)

S3.6 delivers the project-scoped FastAPI endpoints exposing CodePilot's AI-powered requirement generation and clarification workflow.

### REST Endpoints

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/api/projects/{project_id}/requirement-generations` | Start initial requirement generation | `201 Created` |
| `GET` | `/api/projects/{project_id}/requirement-generations/latest` | Retrieve latest generation result for project | `200 OK` |
| `GET` | `/api/projects/{project_id}/requirement-generations/{generation_id}` | Retrieve status and specification of specific generation attempt | `200 OK` |
| `GET` | `/api/projects/{project_id}/clarification-sessions/{session_id}` | Retrieve session details, status, questions, and answers | `200 OK` |
| `GET` | `/api/projects/{project_id}/clarification-sessions/{session_id}/questions` | Retrieve questions (`?pending_only=true` supported) | `200 OK` |
| `POST` | `/api/projects/{project_id}/clarification-sessions/{session_id}/answers` | Submit answers to one or more questions | `200 OK` |
| `POST` | `/api/projects/{project_id}/clarification-sessions/{session_id}/refine` | Trigger or resume refinement with user answers | `200 OK` |
| `GET` | `/api/projects/{project_id}/clarification-sessions/{session_id}/result` | Retrieve latest requirement generation specification | `200 OK` |
| `GET` | `/api/projects/{project_id}/clarification-sessions/{session_id}/revisions` | List historical generation revisions for session | `200 OK` |
| `GET` | `/api/projects/{project_id}/clarification-sessions/{session_id}/revisions/{revision_number}` | Retrieve specific revision | `200 OK` |

### Request and Response Schema Contracts

#### 1. Start Requirement Generation (`POST /requirement-generations`)

**Request Payload (`RequirementGenerationStartRequest`):**
```json
{
  "instructions": "Focus on database persistence and security constraints",
  "target_categories": ["performance", "security"],
  "goals": ["Sub-second API latency", "Strict role-based access control"],
  "provider": "gemini",
  "model": null,
  "temperature": 0.2,
  "request_id": "optional-client-idempotency-key",
  "force_new": false
}
```

**Response Payload (`RequirementGenerationResponse`):**
```json
{
  "generation_id": "gen-initial-001",
  "project_id": "proj-123",
  "session_id": "sess-456",
  "status": "awaiting_clarification",
  "revision_number": 1,
  "summary": "Initial requirement specification for CodePilot developer workspace.",
  "result": {
    "generation_id": "gen-initial-001",
    "project_id": "proj-123",
    "summary": "Executive summary...",
    "functional_requirements": [
      {
        "id": "FR-1",
        "title": "Project Management",
        "description": "Manage software projects locally.",
        "expected_behavior": "User can create and list projects.",
        "acceptance_criteria": ["Can create project"]
      }
    ],
    "non_functional_requirements": [],
    "user_stories": [],
    "business_rules": [],
    "assumptions": [],
    "dependencies": [],
    "clarification_questions": [
      {
        "id": "CQ-1",
        "question": "Which database engine should be used for production storage?",
        "rationale": "Determines SQL dialect and pooling architecture.",
        "category": "architecture",
        "is_required": true,
        "suggested_options": ["PostgreSQL", "SQLite", "MySQL"]
      }
    ],
    "execution_metadata": {
      "generation_mode": "initial",
      "initial_provider": "gemini",
      "final_provider": "gemini",
      "duration_seconds": 1.2
    }
  },
  "clarification_session": {
    "id": "sess-456",
    "project_id": "proj-123",
    "generation_id": "gen-initial-001",
    "status": "awaiting_clarification",
    "current_revision": 1,
    "questions": [...],
    "answers": [],
    "unanswered_question_ids": ["CQ-1"],
    "has_unanswered_required_questions": true
  },
  "execution_metadata": { ... },
  "created_at": "2026-10-16T14:00:00Z"
}
```

### Idempotency & Concurrency

- **Idempotency**: Clients may supply `request_id`. When `force_new` is `false`, the API checks if an identical generation already exists for the project and returns the existing response immediately without invoking the LLM again.
- **Race Condition Prevention**: Active refinement operations set session state to `refinement_in_progress`. Any concurrent submission to the same session or project returns `HTTP 409 Conflict` (`SESSION_CONCURRENCY_ERROR`).

### HTTP Error Mapping

| HTTP Status | Error Code | Trigger Condition |
|---|---|---|
| `400 Bad Request` | `INVALID_CLARIFICATION_ANSWER` | Question does not exist in session, duplicate question submitted |
| `400 Bad Request` | `INSUFFICIENT_PROJECT_CONTEXT` | Project description contains insufficient substance (< 10 chars, no goals) |
| `400 Bad Request` | `CONTEXT_WINDOW_EXCEEDED` | Estimated prompt tokens exceed model's token limit |
| `404 Not Found` | `PROJECT_NOT_FOUND` | Project identifier does not exist |
| `404 Not Found` | `GENERATION_NOT_FOUND` | Generation run identifier does not exist |
| `404 Not Found` | `CLARIFICATION_SESSION_NOT_FOUND` | Clarification session identifier does not exist |
| `404 Not Found` | `GENERATION_PROJECT_MISMATCH` | Generation ID belongs to a different project |
| `404 Not Found` | `PROJECT_MISMATCH` | Clarification session belongs to a different project |
| `409 Conflict` | `SESSION_CONCURRENCY_ERROR` | Overlapping refinement run actively executing |
| `409 Conflict` | `INVALID_SESSION_STATE` | Attempting refinement with unanswered required questions or on a cancelled session |
| `422 Unprocessable`| `VALIDATION_ERROR` | Malformed request body, invalid parameter ranges, empty required strings |
| `422 Unprocessable`| `GENERATION_SCHEMA_VALIDATION_ERROR` | Model response fails schema validation after repair |
| `429 Too Many Req` | `RATE_LIMIT_EXCEEDED` / `QUOTA_EXHAUSTED` | Provider rate limit or token quota exhausted |
| `502 Bad Gateway` | `NETWORK_ERROR` / `INVALID_RESPONSE` | Provider network connection dropped or returned invalid format |
| `503 Service Unavail`| `PROVIDER_OUTAGE` | All configured providers unavailable after failover |
| `504 Gateway Timeout`| `REQUEST_TIMEOUT` | Generation deadline exceeded |

### Testing

Run the automated test suite for requirement generation API:
```bash
pytest tests/test_requirement_generation_api.py -v
```
All tests execute offline using deterministic mocked agent outputs and in-memory SQLite fixtures without network calls or external API keys.

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
