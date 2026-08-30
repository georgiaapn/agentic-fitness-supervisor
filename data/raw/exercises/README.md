# Exercises Dataset

This folder may contain the JSON exercise dataset used for Trainer Agent RAG ingestion.

## License Scope

The dataset structure, tooling, instruction text, translations, and JSON metadata are covered by the upstream MIT License:

```text
MIT License
Copyright (c) 2026 Hasan Emir Yildirim
```

## Media Exception

Exercise media referenced by fields such as `image` and `gif_url` is not included in this project. The upstream repository states that media in `images/` and `videos/` belongs to Gym visual and is governed by separate terms.

Do not commit or serve copied exercise media unless a separate license has been obtained.

## Ingestion

From `apps/api`, ingest the JSON into Postgres:

```powershell
python -m app.scripts.ingest_exercises_dataset --replace
```

The ingestion script stores exercise text and metadata in `knowledge_documents` and `knowledge_chunks` under `collection = "exercise_knowledge_base"`.
