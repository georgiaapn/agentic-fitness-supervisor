# Agentic Fitness Supervisor

A multi-agent RAG fitness coaching board for adaptive training, nutrition, and recovery planning.

The app is designed as a recruiter-friendly, local-first project:

- **Local OSS mode:** FastAPI, LangGraph-ready orchestration, PostgreSQL/pgvector, Ollama, and Docker Compose.
- **Azure demo mode:** Azure Static Web Apps, Azure Container Apps, and a free Postgres provider such as Neon or Supabase.

## Product Flow

```text
User profile + morning check-in
  -> Recovery Agent
  -> Supervisor Agent
  -> Trainer Agent + Nutritionist Agent in parallel
  -> Daily Briefing Card
  -> Saved plan version and decision audit
```

The Supervisor can route dynamically. For example, if sleep score is low and quad soreness is high, it can skip heavy lower-body training, call the Recovery Agent first, and ask the Trainer for a mobility-compatible alternative.

## Stack

| Layer | Tools |
| --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn-style primitives, Recharts |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Agents | LangGraph-ready workflow, specialist agent modules |
| RAG | PostgreSQL, pgvector, sentence-transformers |
| Local LLM | Ollama with Qwen, Llama, or Mistral |
| Jobs | APScheduler for MVP, Celery + Redis for v2 |
| Observability | OpenTelemetry, Jaeger |
| DevOps | Docker Compose, GitHub Actions |

## Repository Layout

```text
apps/
  api/      FastAPI backend and agent workflow
  web/      Next.js dashboard
docs/       Architecture and deployment notes
```

## Local Development

Copy the example environment files:

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Start the local stack:

```bash
docker compose up --build
```

Local URLs:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## First Milestone

This scaffold includes:

- product/design contracts;
- FastAPI app skeleton;
- multi-agent workflow modules;
- deterministic recovery and safety rules;
- RAG service interface;
- Next.js daily briefing dashboard;
- local and Azure-oriented environment files.

