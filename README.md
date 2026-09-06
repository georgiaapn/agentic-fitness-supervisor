# Agentic Fitness Supervisor

Agentic Fitness Supervisor is a full-stack AI fitness coaching board. It combines a
Next.js dashboard, a FastAPI backend, LangGraph orchestration, PostgreSQL/pgvector
RAG, wearable-data simulation, structured LLM outputs, and deterministic safety
guardrails to generate and adapt workout and nutrition plans.

Instead of one generic chatbot, the user is coached by a small AI team. A Trainer
Agent plans training, a Nutritionist Agent plans meals, a Recovery Agent evaluates
readiness, and a Supervisor Agent coordinates the final daily decision so
recommendations do not conflict.

The project is local-first and open-source-friendly. It is designed to demonstrate
practical agent architecture, retrieval pipelines, persistence, cloud-ready service
boundaries, and a polished user-facing product.

## Overview

The app supports three main user flows:

1. **Profile setup**

   The user edits a demo profile containing age, sex, height, weight, fitness
   level, goal, available equipment, dietary restrictions, and injury history.

2. **Weekly plan generation**

   The user generates a weekly workout plan and a weekly nutrition plan. These
   plans are grounded in the user's profile and retrieved knowledge from the RAG
   database. Generated plans are saved and can be viewed, replaced, downloaded, or
   deleted.

3. **Morning check-in**

   After weekly plans exist, the user can start the day with a morning check-in.
   The app reviews the user's wearable signals and self-reported condition, then
   decides whether today's workout and meals should stay as planned or be
   adjusted. For example, if readiness is high, the user may keep the planned
   session. If sleep, soreness, pain, or stress suggest lower readiness, the app
   can reduce training load, swap the workout for mobility/recovery work, and
   adapt the day's nutrition.

   **Demo disclaimer:** the current app simulates a smartwatch integration by
   sampling wearable-style rows from a local CSV. In a real deployment, this layer
   is intended to be replaced by actual wearable data from the user's device or a
   wearable provider API.

## Features

- Create a personalized weekly workout plan based on goals, fitness level,
  available equipment, and injury history.
- Create a personalized weekly nutrition plan with breakfast, lunch, dinner, and
  snack suggestions.
- Edit a fitness profile with body metrics, training goal, dietary restrictions,
  available equipment, and injuries.
- Run a morning readiness check before training.
- See whether today's plan should stay unchanged or be adjusted for recovery.
- Get a clear recovery status: `GREEN`, `YELLOW`, or `RED`.
- View today's planned workout and meals next to the adjusted recommendation.
- Save generated weekly plans and access them later.
- Save, update, or delete daily adjustments.
- Download generated workout and nutrition plans as PDFs.
- Receive user-friendly feedback when a check-in cannot run yet, such as when
  weekly plans have not been generated.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, lucide-react, Recharts |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Agent orchestration | LangGraph |
| LLM provider | Gemini API |
| LLM fallback | Deterministic Python planning logic |
| RAG storage | PostgreSQL + pgvector |
| Embeddings | sentence-transformers, `intfloat/multilingual-e5-small` |
| Database driver | psycopg 3 |
| Local infrastructure | Docker Compose |
| Cloud demo | Azure Container Apps Consumption for frontend and backend |
| LLM cost control | Backend-only demo access code with deterministic fallback |

## Architecture

```text
apps/web
  Next.js UI
  Profile editor
  Weekly plan modals
  Morning check-in modal
  Saved plans and adjustments

apps/api
  FastAPI routes
  Pydantic schemas
  LangGraph workflow
  Specialist agents
  RAG service
  LLM client
  SQLAlchemy models
  Alembic migrations
  Dataset ingestion scripts

data/raw
  exercises/
  nutrition/
  recovery/
  wearables/
```

At runtime:

```text
Frontend
  -> FastAPI endpoints
  -> agents / LangGraph workflow
  -> RAG service
  -> PostgreSQL + pgvector
  -> Gemini API when enabled
  -> deterministic fallback when needed
```

## Main Agent Responsibilities

### Trainer Agent

The Trainer Agent creates workout recommendations.

- Generates a 7-day weekly workout plan.
- Uses profile goal, fitness level, available equipment, and injury history.
- Retrieves exercise context from `exercise_knowledge_base`.
- Avoids unavailable equipment.
- Avoids stretch-dominant weekly plans for normal training.
- Creates daily adjusted workouts during morning check-in.
- Downshifts volume/intensity when the Supervisor issues recovery constraints.

### Nutritionist Agent

The Nutritionist Agent creates nutrition recommendations.

- Generates a 7-day nutrition plan with Breakfast, Snack, Lunch, and Dinner.
- Uses profile goal, dietary restrictions, body weight, and calculated targets.
- Retrieves meal context from `nutrition_knowledge_base`.
- Uses `meal_type` as grounding so Breakfast, Lunch, Dinner, and Snack remain
  slot-appropriate.
- Keeps daily calories and protein near calculated targets.
- Creates daily adjusted meals during morning check-in.

### Recovery Agent

The Recovery Agent evaluates readiness.

- Reads wearable data and self-report values.
- Produces `GREEN`, `YELLOW`, or `RED` recovery status.
- Calculates a readiness score.
- Emits constraints such as low sleep, high soreness, elevated pain, high stress,
  low SpO2, or high step-count load.
- Retrieves supporting recovery protocol context from `recovery_knowledge_base`.
- Keeps safety decisions deterministic instead of delegating them entirely to an
  LLM.

### Supervisor Agent

The Supervisor Agent coordinates the team.

- Reads the Recovery Agent report.
- Reads the user's long-term goal.
- Reads today's baseline workout and nutrition from saved weekly plans.
- Detects conflicts, such as high soreness or pain on the same body region as
  today's planned training.
- Issues directives to Trainer and Nutritionist.
- Decides which specialist nodes should run.
- Prevents heavy training recommendations when recovery constraints require a
  safer daily plan.

## LangGraph Daily Check-In Flow

```mermaid
flowchart TD
    Start((START)) --> LoadContext[load_context_node]
    LoadContext --> Recovery[recovery_node]
    Recovery --> Supervisor[supervisor_node]

    Supervisor --> Route{route_specialists}
    Route -->|trainer + nutritionist| Trainer[trainer_node]
    Route -->|trainer + nutritionist| Nutritionist[nutritionist_node]
    Route -->|nutrition only| NutritionSolo[nutritionist_solo]

    Trainer --> Aggregate[aggregate_node]
    Nutritionist --> Aggregate
    NutritionSolo --> Aggregate
    Aggregate --> End((END))

    LoadContext -.-> Profile[(profile)]
    LoadContext -.-> Wearable[(wearable snapshot)]
    LoadContext -.-> Baselines[(saved weekly plans)]
    Recovery -.-> RecoveryReport[(recovery report)]
    Supervisor -.-> Directives[(supervisor directives)]
    Trainer -.-> Workout[(adjusted workout)]
    Nutritionist -.-> Nutrition[(adjusted meals)]
```

The weekly workout and weekly nutrition generation flows do **not** run through
LangGraph. They are direct FastAPI endpoints that call the Trainer or
Nutritionist agent independently. LangGraph is used for the daily check-in,
because that is where multiple agents need coordinated state and conditional
routing.

## Core Flows

### Generate Weekly Workout Plan

```text
Get Workout Plan button
  -> POST /api/plans/workout/weekly
  -> generate_weekly_workout_plan
  -> RagService.training_exercises(profile)
  -> get_llm_client()
  -> create_weekly_workout_plan(...)
  -> Gemini structured output or deterministic fallback
  -> save_generated_plan(...)
  -> WeeklyWorkoutPlan returned to UI
```

### Generate Weekly Nutrition Plan

```text
Get Diet Plan button
  -> POST /api/plans/nutrition/weekly
  -> generate_weekly_nutrition_plan
  -> RagService.recovery_meals(profile)
  -> get_llm_client()
  -> create_weekly_nutrition_plan(...)
  -> Gemini structured output or deterministic fallback
  -> save_generated_plan(...)
  -> WeeklyNutritionPlan returned to UI
```

### Morning Check-In

```text
Check in button
  -> self-report modal
  -> POST /api/check-ins/simulate
  -> sample mock wearable CSV row
  -> POST /api/check-ins/morning
  -> run_morning_check_in(...)
  -> LangGraph invoke(...)
  -> DailyBriefingResponse returned to UI
  -> optional save/update daily adjustment
```

## RAG Design

RAG knowledge is stored in two database tables:

| Table | Purpose |
| --- | --- |
| `knowledge_documents` | One row per source item/document. |
| `knowledge_chunks` | Searchable text chunks, metadata, and optional pgvector embedding. |

Collections:

| Collection | Used by | Source |
| --- | --- | --- |
| `exercise_knowledge_base` | Trainer Agent | Exercise JSON dataset |
| `nutrition_knowledge_base` | Nutritionist Agent | Healthy eating meal CSV |
| `recovery_knowledge_base` | Recovery Agent | Curated recovery protocols |

Retrieval behavior:

- If embeddings exist, the app uses pgvector similarity search.
- If embeddings are missing or embedding dependencies are unavailable, it falls
  back to lexical keyword scoring.
- Exercise retrieval filters by available equipment.
- Nutrition retrieval avoids known dietary restriction terms.
- Recovery retrieval builds a query from wearable and self-report risk signals.

## Data Model Highlights

Important application tables:

- `users`
- `user_profiles`
- `daily_checkins`
- `agent_runs`
- `supervisor_decisions`
- `plan_versions`
- `saved_generated_plans`
- `saved_daily_adjustments`
- `knowledge_documents`
- `knowledge_chunks`

The MVP uses one demo user:

```text
demo-user
```

This keeps the demo focused on agentic behavior. A production version can add
email/password authentication while keeping the existing `user_id` ownership
model for profiles, plans, and adjustments.

## API Surface

Useful endpoints:

```text
GET    /health

GET    /api/profile/demo-user
PUT    /api/profile/demo-user

POST   /api/plans/workout/weekly
POST   /api/plans/nutrition/weekly

GET    /api/profile/{user_id}/generated-plans
DELETE /api/profile/{user_id}/generated-plans/{plan_id}

POST   /api/check-ins/simulate
POST   /api/check-ins/morning

GET    /api/profile/{user_id}/daily-adjustments
POST   /api/profile/{user_id}/daily-adjustments
DELETE /api/profile/{user_id}/daily-adjustments/{adjustment_id}

GET    /api/agent-runs
GET    /api/knowledge-chunks
```

Interactive API docs are available locally at:

```text
http://localhost:8000/docs
```

## Requirements

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Gemini API key for LLM generation
- PostgreSQL client tools are optional but useful
- Enough disk space for the local Hugging Face model cache when generating
  embeddings

## Environment Variables

Backend `.env` lives in `apps/api/.env`.

Create it from:

```text
apps/api/.env.example
```

Common backend variables:

```env
DATABASE_URL=postgresql+psycopg://fitness:fitness@localhost:5432/fitness_agents
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
LLM_ACCESS_CONTROL_ENABLED=true
DEMO_ACCESS_CODE=
LLM_TIMEOUT_SECONDS=30
EMBEDDING_MODEL=intfloat/multilingual-e5-small
ENVIRONMENT=local
PERSISTENCE_ENABLED=true
CORS_ORIGINS=http://localhost:3000
```

Frontend `.env` lives in `apps/web/.env.local`.

Create it from:

```text
apps/web/.env.example
```

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Local Development

### 1. Install Frontend Dependencies

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor\apps\web
npm install
```

### 2. Install Backend Dependencies

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[rag]"
```

### 3. Start PostgreSQL

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor
docker compose up -d postgres
```

Local database connection:

```text
Host: localhost
Port: 5432
Database: fitness_agents
Username: fitness
Password: fitness
Docker Compose service: postgres
```

### 4. Run Migrations

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor\apps\api
$env:PERSISTENCE_ENABLED="true"
python -m alembic upgrade head
```

### 5. Start The API

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor\apps\api
$env:PERSISTENCE_ENABLED="true"
python -m uvicorn app.main:app --reload
```

### 6. Start The Web App

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor\apps\web
npm run dev
```

Local URLs:

```text
Web:      http://localhost:3000
API:      http://localhost:8000
API docs: http://localhost:8000/docs
Health:   http://localhost:8000/health
```

## Docker Compose

The Compose stack defines:

- `postgres`: PostgreSQL 16 with pgvector
- `api`: FastAPI backend
- `web`: Next.js frontend

Start the full stack:

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor
docker compose up --build
```

For development, it is often easier to run only the database in Docker and run
the API/web dev servers directly:

```powershell
docker compose up -d postgres
```

## Dataset Ingestion

Run ingestion commands from `apps/api` after PostgreSQL is running and migrations
have been applied.

### Exercise Knowledge

Expected files:

```text
data/raw/exercises/exercises.json
data/raw/exercises/exercises.schema.json
```

Commands:

```powershell
$env:PERSISTENCE_ENABLED="true"
python -m app.scripts.ingest_exercises_dataset --replace
python -m app.scripts.embed_knowledge_chunks --collection exercise_knowledge_base
```

The exercise pipeline stores exercise name, category, body part, equipment,
target muscles, secondary muscles, English instructions, and metadata. It does
not redistribute exercise images or videos.

### Nutrition Knowledge

Expected file:

```text
data/raw/nutrition/healthy_meal_dataset.csv
```

Expected columns:

```text
meal_id, meal_name, meal_type, diet_type, calories, protein_g, carbs_g,
fat_g, fiber_g, sugar_g, sodium_mg, cholesterol_mg, serving_size_g
```

Commands:

```powershell
$env:PERSISTENCE_ENABLED="true"
python -m app.scripts.ingest_nutrition_dataset --replace
python -m app.scripts.embed_knowledge_chunks --collection nutrition_knowledge_base
```

All rows in the current custom dataset are treated as healthy. If a future
nutrition dataset includes an `is_healthy` column, ingestion will use it by
default and keep only healthy rows unless `--include-unhealthy` is passed.

### Recovery Knowledge

Expected file:

```text
data/raw/recovery/recovery_protocols.json
```

Commands:

```powershell
$env:PERSISTENCE_ENABLED="true"
python -m app.scripts.ingest_recovery_protocols --replace
python -m app.scripts.embed_knowledge_chunks --collection recovery_knowledge_base
```

Recovery protocols are intentionally small and curated. They provide grounding
for readiness, deload, low sleep, high stress, high soreness, high pain, low
SpO2, elevated resting heart rate, and high step-count situations.

## Wearable Simulation

The product architecture assumes the app receives the user's current wearable
data during the morning check-in. For this MVP, that external smartwatch
integration is mocked with a local CSV so the demo can run without connecting to
Apple Health, Fitbit, Garmin, Whoop, or another provider.

The wearable dataset is not used as RAG knowledge. It represents the live
wearable input layer that would be replaced by a real provider API in production.

Expected file:

```text
data/raw/wearables/unclean_smartwatch_health_data.csv
```

Mapping:

| Dataset column | App field |
| --- | --- |
| `Heart Rate (BPM)` | `resting_heart_rate` |
| `Blood Oxygen Level (%)` | `blood_oxygen_level` |
| `Step Count` | `step_count` |
| `Sleep Duration (hours)` | `sleep_hours` |
| `Activity Level` | `activity_level` |
| `Stress Level` | `stress_level` |

Derived fields:

- `sleep_score`
- `energy_level`

Self-reported check-in fields:

- `soreness_quads`
- `soreness_upper`
- `pain_level`
- `available_minutes`

## Reliability And Guardrails

The app does not rely on the LLM for every important decision.

- Recovery scoring and safety constraints are deterministic.
- Public cloud demo requests can run in deterministic fallback mode when no
  valid demo access code is provided.
- LLM-backed generation is gated in the backend through `DEMO_ACCESS_CODE`; the
  key is never exposed as a frontend environment variable.
- LLM responses must validate against Pydantic schemas.
- If Gemini is unavailable, rate-limited, times out, or returns invalid JSON,
  deterministic fallback plans are returned.
- Trainer outputs are checked for unavailable equipment and stretch-dominant
  weekly plans.
- Nutrition prompts instruct Gemini to respect `meal_type` slots and dietary
  restrictions.
- Backend data remains inspectable through saved plans, agent runs, and
  knowledge chunk endpoints.

## Testing And Verification

Common backend syntax check:

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor
python -m py_compile apps\api\app\main.py apps\api\app\workflow\graph.py
```

Frontend build:

```powershell
cd C:\FITNESS_AGENT\agentic-fitness-supervisor\apps\web
npm run build
```

Backend health:

```powershell
curl.exe http://localhost:8000/health
```

Expected healthy response includes:

```json
{
  "status": "ok",
  "persistence": "enabled",
  "llm_provider": "gemini",
  "llm": "enabled"
}
```

## Deployment Notes

The project can run fully locally with Docker Compose. For the current public
cloud demo, the recommended forever-free-friendly Azure shape is:

- frontend: Azure Container Apps Consumption with `minReplicas=0`
- backend: Azure Container Apps Consumption with `minReplicas=0`
- database: keep the existing local PostgreSQL/pgvector setup; deploy the Azure
  demo with `PERSISTENCE_ENABLED=false` unless a separate free database is added
- LLM: Gemini API behind backend-side demo access control, with deterministic
  fallback for public visitors

Running a local LLM such as Ollama is useful for development, but it is not a
good fit for a free Azure-hosted public demo because it needs persistent compute
and more memory.

Azure deployment reference:

```text
docs/azure-free-demo.md
.github/workflows/azure-container-app-web.yml
.github/workflows/azure-container-app-api.yml
```

## Limitations

- Authentication is not implemented yet; the MVP uses `demo-user`.
- The smartwatch integration is simulated from CSV.
- Nutrition data is synthetic demo data.
- Recovery guidance is educational and not medical advice.
- Gemini availability depends on the selected model and provider rate limits.
- Full post-generation nutrition meal-slot validation is a future improvement.

## Roadmap

- Add email/password authentication without Firebase dependency.
- Add per-user plan history and progress analytics.
- Add timezone-aware current-day selection.
- Add real wearable provider integration.
- Add richer nutrition recipe cards with ingredients and instructions if a
  suitable dataset is added.
- Add automated tests for graph routing, recovery decisions, RAG filters, and UI
  flows.
- Add deployment templates for Azure demo infrastructure.

## Licenses And Acknowledgements

### Project Code

Add a root `LICENSE` file before public release to define the license for this
application code.

### Exercise Dataset

Source:

```text
https://github.com/hasaneyldrm/exercises-dataset/tree/main/data
```

The repository states that code, tooling, dataset structure, instruction text,
and translations are MIT licensed.

Important media exception:

- exercise media under `images/` and `videos/` is not covered by MIT;
- media is attributed to Gym visual;
- cloning the dataset does not grant reuse rights for that media;
- this project ingests exercise JSON data and does not redistribute exercise
  image/video media.

### Nutrition Dataset

Source:

```text
data/raw/nutrition/healthy_meal_dataset.csv
```

The nutrition dataset is a custom generated demo dataset maintained with the
project. It is used as grounding data for meal recommendations and contains meal
type, diet type, serving size, calories, and macro/micronutrient fields.

### Wearable Dataset

The smartwatch simulation dataset is stored under:

```text
data/raw/wearables/
```

The included dataset license is Apache License 2.0. Keep
`data/raw/wearables/LICENSE` with the dataset when distributing or modifying it.

### Recovery Knowledge

Recovery protocols are curated educational demo content stored in:

```text
data/raw/recovery/recovery_protocols.json
```

They are not medical diagnosis or treatment guidance.
