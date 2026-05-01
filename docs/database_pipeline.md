# PostgreSQL 入库与审查流程

当前数据库层采用两阶段：

`JSONL -> staging -> 审查 -> promote -> corpus`

这样做的目的不是“多一层表”，而是避免一次坏导入直接污染主检索库。

## 目录

- [db/schema.sql](/D:/coding_projects/law_helper/db/schema.sql): schema、约束、审查函数、promote 函数
- [scripts/load_ingestion_to_pg.py](/D:/coding_projects/law_helper/scripts/load_ingestion_to_pg.py): 把 `documents.jsonl` 和 `chunks.jsonl` 装入 PostgreSQL staging

## 表

### 1. `rag.ingestion_runs`

记录每次导入 run 的元数据和状态：

- `loaded`
- `promoted`
- `superseded`
- `failed`

### 2. `rag.staging_documents`

文档级 staging 表。每次 run 独立存放，不覆盖历史。

### 3. `rag.staging_chunks`

chunk 级 staging 表。入库前先经过这层，再做审查。

### 4. `rag.documents`

当前已 promote 的运营文档表。

### 5. `rag.chunks`

当前已 promote 的运营 chunk 表。检索必须只查这张表，并且必须带：

```sql
WHERE enabled_for_retrieval = true
```

## 硬约束

### documents / staging_documents

- `document_id` 唯一
- `doc_type in ('law','rule','case','template')`
- `title` / `canonical_title` / `source_name` / `raw_text` / `clean_text` 非空
- `tags` / `warnings` 使用 `jsonb`
- `file_path` 在同一层表内唯一

### chunks / staging_chunks

- `chunk_id` 唯一
- `(document_id, chunk_order)` 唯一
- `(document_id, article_no)` 在 `article_no is not null` 时唯一
- `enabled_for_retrieval=true` 的 `canonical_key` 必须唯一
- `law` / `rule` 类型 chunk 必须有 `article_no`
- `chunk_order > 0`

## 审查函数

### `rag.review_findings(run_id uuid)`

对指定 staging run 做入库前审查，返回：

- `severity`
- `check_name`
- `finding_count`
- `detail`

当前包含：

- blocker
- `run_exists`
- `document_count_match`
- `chunk_count_match`
- `duplicate_enabled_canonical_keys`
- `non_contiguous_chunk_order`
- `documents_with_zero_chunks`
- `document_declared_chunk_count_mismatch`
- `law_rule_chunks_missing_article_no`

- warning
- `documents_with_parser_warnings`
- `enabled_documents_missing_effective_date`
- `enabled_documents_missing_source_url`

### `rag.can_promote_run(run_id uuid)`

只要还有 `blocker`，返回 `false`。

### `rag.promote_run(run_id uuid)`

只允许通过 blocker 检查的 run 进入运营表。

### `rag.review_corpus()`

对当前已 promote 的运营库做审查。

## 执行顺序

### 1. 应用 schema

```powershell
Get-Content -Path .\db\schema.sql | docker exec -i law-helper-pg psql -v ON_ERROR_STOP=1 -U law -d law_helper -f -
```

### 2. 把 JSONL 装入 staging

```powershell
python .\scripts\load_ingestion_to_pg.py `
  --container law-helper-pg `
  --db-user law `
  --db-name law_helper `
  --manifest .\data\manifest.jsonl `
  --documents .\build\ingestion\documents.jsonl `
  --chunks .\build\ingestion\chunks.jsonl `
  --stats .\build\ingestion\stats.json `
  --run-label "baseline-8docs"
```

### 3. 复核审查结果

```sql
SELECT *
FROM rag.review_findings('<run_id>'::uuid)
ORDER BY
  CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
  check_name;
```

### 4. promote

```sql
SELECT rag.promote_run('<run_id>'::uuid);
```

### 5. 审查运营库

```sql
SELECT *
FROM rag.review_corpus()
ORDER BY
  CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
  check_name;
```

## 当前基线

在当前 8 份材料下，期望基线是：

- `document_count = 8`
- `chunk_count = 911`
- `duplicate_enabled_canonical_keys = 0`

当前已知 warning：

- 至少一份启用文档缺 `effective_date`
- 多份启用文档缺 `source_url`

这些 warning 不阻塞 staging 装载，但建议在正式对外使用前补齐。
