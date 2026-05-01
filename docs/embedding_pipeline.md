# Embedding 入库与审查流程

当前向量层刻意与主文本表解耦：

- 文本库：`rag.documents` / `rag.chunks`
- 向量 staging：`rag.embedding_runs` / `rag.staging_chunk_embeddings`
- 向量运营表：`rag.chunk_embeddings`

这样做的目的有两个：

- 更换 embedding 模型时不需要重建主文本表
- embedding 生成失败或错位时，不会污染运营检索表

## 核心原则

- embedding 永远绑定到具体 corpus run
- embedding 永远绑定到 `embedding_text_hash`
- 只有通过审查的 embedding run 才允许 promote

## 新表

### `rag.embedding_runs`

记录每次 embedding 装载：

- `source_ingestion_run_id`
- `model_name`
- `dimensions`
- `distance_metric`
- `chunk_scope`
- `expected_chunk_count`
- `status`

### `rag.staging_chunk_embeddings`

向量 staging 表，按 run 暂存：

- `chunk_id`
- `embedding_text_hash`
- `embedding vector`

### `rag.chunk_embeddings`

当前运营向量表。主键是：

```text
(chunk_id, model_name)
```

这意味着一个 chunk 可以同时保留多个模型的向量。

## 审查函数

### `rag.review_embedding_run(embedding_run_id uuid)`

blocker 包括：

- `embedding_run_exists`
- `embedding_source_run_is_current_corpus`
- `embedding_expected_chunk_count_match`
- `embedding_loaded_chunk_count_match`
- `embedding_unknown_chunk_ids`
- `embedding_missing_chunk_ids`
- `embedding_dimension_mismatch`
- `embedding_text_hash_mismatch`

### `rag.can_promote_embedding_run(embedding_run_id uuid)`

只要 blocker 不为 0，就不能 promote。

### `rag.promote_embedding_run(embedding_run_id uuid)`

将 staging 向量写入 `rag.chunk_embeddings`。

当前策略是：

- 同一 `model_name` 的旧 promoted embedding run 会被标记为 `superseded`
- 同一 `model_name` 的旧 active 向量会先删再写

### `rag.review_active_embeddings()`

对当前 active embeddings 做一致性审查，检查：

- `active_embedding_text_hash_mismatch`
- `active_embedding_source_run_mismatch`
- `active_embedding_dimension_mismatch`

## 推荐执行顺序

### 1. 生成测试向量

当前仓库先提供一套“伪 embedding”脚本，只用于验证数据库和导入流程，不代表真实语义效果：

```powershell
python .\scripts\build_mock_embeddings.py `
  --chunks .\build\ingestion\chunks.jsonl `
  --output .\build\embeddings\mock_embeddings.jsonl `
  --dimensions 16 `
  --enabled-only
```

### 1b. 生成真实 OpenAI embeddings

当前仓库也提供一个不依赖 OpenAI SDK 的真实生成脚本：

```powershell
$env:OPENAI_API_KEY="your_api_key"
python .\scripts\build_openai_embeddings.py `
  --chunks .\build\ingestion\chunks.jsonl `
  --output .\build\embeddings\openai_embeddings.jsonl `
  --model text-embedding-3-small `
  --enabled-only
```

如果你要更高质量，可以换成：

```powershell
--model text-embedding-3-large
```

如果要压缩向量维度，只能用于 `text-embedding-3` 系列：

```powershell
--dimensions 1024
```

脚本会直接调用 `/v1/embeddings`，并输出与数据库导入脚本兼容的 JSONL。

### 2. 装入 staging

```powershell
python .\scripts\load_embeddings_to_pg.py `
  --container law-helper-pg `
  --db-user law `
  --db-name law_helper `
  --embeddings .\build\embeddings\openai_embeddings.jsonl `
  --run-label "mock-16" `
  --model-name "text-embedding-3-small" `
  --distance-metric cosine `
  --chunk-scope enabled_only
```

如果不传 `--source-run-id`，脚本会自动绑定当前 promoted corpus run。

### 3. 审查

```sql
SELECT *
FROM rag.review_embedding_run('<embedding_run_id>'::uuid)
ORDER BY
  CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
  check_name;
```

### 4. promote

```sql
SELECT rag.promote_embedding_run('<embedding_run_id>'::uuid);
```

### 5. 审查 active embeddings

```sql
SELECT *
FROM rag.review_active_embeddings()
ORDER BY
  CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
  check_name;
```

## 真实 embedding 的 JSONL 格式

后面接真实模型时，导入文件格式保持这一行一个 JSON：

```json
{
  "chunk_id": "cn_consumer_rights_law_20131025:article:0001",
  "embedding_text_hash": "sha256-of-embedding_text",
  "embedding": [0.01, -0.02, 0.03]
}
```

要求：

- 同一批次所有 `embedding` 维度必须一致
- `chunk_id` 必须来自当前 promoted corpus
- `embedding_text_hash` 必须和库里的 `rag.chunks.embedding_text_hash` 一致

## 当前建议

## OpenAI 约束

按 OpenAI 官方 Embeddings 文档：

- `input` 可以一次传单条字符串，也可以传字符串数组
- 每条输入不能超过 8192 tokens
- 单次请求所有输入合计不能超过 300000 tokens
- `dimensions` 只支持 `text-embedding-3` 及后续模型
- 默认维度是 `text-embedding-3-small = 1536`，`text-embedding-3-large = 3072`

当前脚本没有引入 tokenizer 依赖，所以用保守的“每批最大字符数”做请求切分，而不是精确 token 计数。

## 当前建议

如果你要先低成本试跑，先用：

- `text-embedding-3-small`

如果后面发现中文法规检索召回不够，再切到：

- `text-embedding-3-large`
