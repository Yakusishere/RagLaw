# Backend MVP Runbook

## Local setup

1. Copy `.env.example` to `.env.local`
2. Fill in `DATABASE_URL` and `OPENAI_API_KEY`
3. If using an OpenAI-compatible provider such as DashScope, also set `OPENAI_BASE_URL`
4. Install dependencies with `python -m pip install -e ".[dev]"`

## Start the API

```bash
uvicorn app.main:app --reload
```

## Required pre-launch data state

- promoted corpus exists in `rag.chunks`
- promoted real embeddings exist in `rag.chunk_embeddings`
- `OPENAI_EMBEDDING_MODEL` matches the promoted embedding model name
- if `OPENAI_BASE_URL` points to a non-OpenAI provider, that provider must also support the configured embedding model

## Real embedding cutover

Generate real embeddings:

```powershell
$env:OPENAI_API_KEY="your_api_key"
python .\scripts\build_openai_embeddings.py `
  --chunks .\build\ingestion\chunks.jsonl `
  --output .\build\embeddings\openai_embeddings.jsonl `
  --model text-embedding-v4 `
  --enabled-only
```

Load and promote:

```powershell
python .\scripts\load_embeddings_to_pg.py `
  --container law-helper-pg `
  --db-user law `
  --db-name law_helper `
  --embeddings .\build\embeddings\openai_embeddings.jsonl `
  --run-label "dashscope-embedding-v4" `
  --model-name "text-embedding-v4" `
  --distance-metric cosine `
  --chunk-scope enabled_only `
  --promote-if-clean
```

## Smoke-test commands

After `.env.local` is configured and the promoted corpus / embeddings exist:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/retrieve -H "Content-Type: application/json" -d "{\"query\":\"商家拒绝退款怎么办\"}"
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"query\":\"网购商品质量有问题，商家不同意退货怎么办？\"}"
```
