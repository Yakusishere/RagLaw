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
- Phase 2 draft template files exist under `docs/phase2_materials`
- at least one `template_*.json` file is present and matches the current `DraftTemplate` schema

## Real embedding cutover

Generate real embeddings:

```powershell
$env:OPENAI_API_KEY="your_api_key"
$env:OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 仅在使用 DashScope 等 OpenAI-compatible provider 时设置
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

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST http://127.0.0.1:8000/retrieve `
  -H "Content-Type: application/json" `
  --data '{"query":"商家拒绝退款怎么办"}'
curl.exe -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  --data '{"query":"网购商品质量有问题，商家不同意退货怎么办？"}'
curl.exe -X POST http://127.0.0.1:8000/draft `
  -H "Content-Type: application/json" `
  --data '{"template_type":"complaint_letter","facts":{"consumer_name":"张三","merchant_name":"某商家","product_name":"蓝牙耳机"}}'
```

Expected success:
- `/health` returns a JSON body containing `"status":"ok"`
- `/retrieve` returns JSON with a non-empty `results` array when promoted data is present
- `/chat` returns JSON containing `answer.summary`, `citations`, and `retrieval.result_count`
- `/draft` returns JSON containing `template_name`, `draft_text`, `missing_fields`, `cited_laws`, and `next_steps`

SSE smoke test:

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/chat/stream `
  -H "Content-Type: application/json" `
  --data '{"query":"商家拒绝退款怎么办"}'
```

Expected success:
- HTTP status is `200`
- output starts with `event: meta`
- then includes one or more `event: delta`
- and ends with `event: citations` plus `event: done`
- if a runtime failure happens after streaming starts, expect `event: error` on the SSE channel rather than an HTTP `500` body

Draft smoke-test note:
- if `/draft` returns a non-empty `missing_fields` array, treat that as a valid business response rather than a server error
- if `/draft` returns an empty `draft_text` with missing fields, confirm the request facts cover all required template placeholders
