# 当前进度总结

本文档总结截至当前为止，`law_helper` 项目已经完成的资料导入、数据库建模、向量层验证和后续待办。

## 1. 当前目标范围

项目当前聚焦于消费维权 RAG 后端的资料侧与数据库侧，不包含前端问答页面和正式 API 服务实现。

已经完成的主线是：

`docx -> JSONL -> PostgreSQL staging -> 审查 -> promote -> corpus -> embeddings staging -> 审查 -> promote`

## 2. 当前资料范围

当前纳入运营库的资料共 8 份，全部来自 `data/manifest.jsonl`：

- `中华人民共和国消费者权益保护法`
- `中华人民共和国消费者权益保护法实施条例`
- `中华人民共和国电子商务法`
- `侵害消费者权益行为处罚办法`
- `合同违法行为监督处理办法`
- `网络交易平台规则监督管理办法`
- `中华人民共和国民法典 合同编`
- `中华人民共和国民法典 侵权责任编`

特别说明：

- 整部 [中华人民共和国民法典_20200528.docx](/D:/coding_projects/law_helper/data/中华人民共和国民法典_20200528.docx) 仍保留在 `data/` 目录
- 但它已经从 [manifest.jsonl](/D:/coding_projects/law_helper/data/manifest.jsonl) 移除
- 因此它不会进入运营库，也不会被误用于检索或 embedding

## 3. 已完成的脚本与文档

### 导入层

- [import_materials.py](/D:/coding_projects/law_helper/scripts/import_materials.py)
- [manifest.jsonl](/D:/coding_projects/law_helper/data/manifest.jsonl)
- [ingestion_pipeline.md](/D:/coding_projects/law_helper/docs/ingestion_pipeline.md)

作用：

- 从 `docx` 提取正文
- 清洗目录和空白
- 对连续大段规章基于 `第X条` 做拆分
- 生成：
  - [documents.jsonl](/D:/coding_projects/law_helper/build/ingestion/documents.jsonl)
  - [chunks.jsonl](/D:/coding_projects/law_helper/build/ingestion/chunks.jsonl)
  - [stats.json](/D:/coding_projects/law_helper/build/ingestion/stats.json)

### 数据库层

- [schema.sql](/D:/coding_projects/law_helper/db/schema.sql)
- [load_ingestion_to_pg.py](/D:/coding_projects/law_helper/scripts/load_ingestion_to_pg.py)
- [database_pipeline.md](/D:/coding_projects/law_helper/docs/database_pipeline.md)

作用：

- 建立 `rag` schema
- 建立 staging 表和运营表
- 支持 `review -> promote`
- 支持 blocker / warning 分离审查

### 向量层

- [build_mock_embeddings.py](/D:/coding_projects/law_helper/scripts/build_mock_embeddings.py)
- [build_openai_embeddings.py](/D:/coding_projects/law_helper/scripts/build_openai_embeddings.py)
- [load_embeddings_to_pg.py](/D:/coding_projects/law_helper/scripts/load_embeddings_to_pg.py)
- [embedding_pipeline.md](/D:/coding_projects/law_helper/docs/embedding_pipeline.md)

作用：

- 生成 mock embeddings 用于流程验证
- 生成真实 OpenAI embeddings JSONL
- 装入 embedding staging
- 审查并 promote 到运营向量表

## 4. 当前数据库结构

当前 PostgreSQL 使用 Docker 容器 `law-helper-pg`。

### 文本相关表

- `rag.ingestion_runs`
- `rag.staging_documents`
- `rag.staging_chunks`
- `rag.documents`
- `rag.chunks`

### 向量相关表

- `rag.embedding_runs`
- `rag.staging_chunk_embeddings`
- `rag.chunk_embeddings`

### 关键设计

- 文本入库采用 staging -> 审查 -> promote
- 向量入库采用 staging -> 审查 -> promote
- `enabled_for_retrieval=true` 的 `canonical_key` 必须唯一
- embedding 不直接绑在 `rag.chunks` 上，而是单独存储
- embedding 绑定 `embedding_text_hash`，防止文本变了但向量没更新

## 5. 当前已验证结果

### 文本库基线

当前 corpus 已实际导入并 promote 成功。

基线如下：

- 文档数：`8`
- chunk 数：`911`
- `duplicate_enabled_canonical_keys = 0`

当前来源 run：

- `6d55645a-1da5-4d76-a723-7d055fb2ddc5`

### 文本库审查结果

`rag.review_corpus()` 的 blocker 已全部通过。

当前 warning 仍存在：

- `cn_consumer_rights_regulation` 缺 `effective_date`
- 8 份启用文档都缺 `source_url`

这些 warning 不阻塞当前原型，但正式对外使用前建议补齐。

### 向量库基线

当前 active embeddings 已实际导入并 promote 成功。

当前模型：

- `model_name = mock-hash-16`
- `distance_metric = cosine`
- `dimensions = 16`
- `embedding_count = 911`

当前 embedding run：

- `ccb3f6fc-6b35-40b0-8ef1-168c8020208d`

### 向量库审查结果

以下 blocker 已全部通过：

- `embedding_dimension_mismatch = 0`
- `embedding_expected_chunk_count_match = 0`
- `embedding_loaded_chunk_count_match = 0`
- `embedding_missing_chunk_ids = 0`
- `embedding_text_hash_mismatch = 0`
- `embedding_unknown_chunk_ids = 0`

`rag.review_active_embeddings()` 也已通过：

- `active_embedding_dimension_mismatch = 0`
- `active_embedding_source_run_mismatch = 0`
- `active_embedding_text_hash_mismatch = 0`

## 6. 当前中间产物

### 导入产物

- [documents.jsonl](/D:/coding_projects/law_helper/build/ingestion/documents.jsonl)
- [chunks.jsonl](/D:/coding_projects/law_helper/build/ingestion/chunks.jsonl)
- [stats.json](/D:/coding_projects/law_helper/build/ingestion/stats.json)

### 向量产物

- [mock_embeddings.jsonl](/D:/coding_projects/law_helper/build/embeddings/mock_embeddings.jsonl)

说明：

- `mock_embeddings.jsonl` 只是流程验证用，不代表真实语义质量
- 真实向量应通过 [build_openai_embeddings.py](/D:/coding_projects/law_helper/scripts/build_openai_embeddings.py) 重新生成

## 7. 当前真实 embedding 生成方式

已经支持基于 OpenAI Embeddings API 生成真实 JSONL：

示例：

```powershell
$env:OPENAI_API_KEY="your_api_key"
python .\scripts\build_openai_embeddings.py `
  --chunks .\build\ingestion\chunks.jsonl `
  --output .\build\embeddings\openai_embeddings.jsonl `
  --model text-embedding-3-small `
  --enabled-only
```

再导入数据库：

```powershell
python .\scripts\load_embeddings_to_pg.py `
  --container law-helper-pg `
  --db-user law `
  --db-name law_helper `
  --embeddings .\build\embeddings\openai_embeddings.jsonl `
  --run-label "openai-small" `
  --model-name "text-embedding-3-small" `
  --distance-metric cosine `
  --chunk-scope enabled_only `
  --promote-if-clean
```

## 8. 当前明确未完成的部分

以下还没有做：

- 正式的 Python 应用层数据库访问封装
- 向量检索 SQL / Python 检索服务
- 混合检索合并逻辑
- FastAPI 接口
- LLM grounded answer 生成
- 文书模板系统
- 前端与 API 联调

## 9. 下一步建议优先级

建议按下面顺序继续：

1. 做检索层
   - 向量检索
   - 关键词检索
   - 混合召回

2. 做应用层服务
   - Python 数据库配置
   - retrieval service
   - citation 组织

3. 做 API
   - `/retrieve`
   - `/chat`
   - `/draft`

4. 补资料元数据
   - `source_url`
   - 缺失的 `effective_date`

## 10. 当前项目状态一句话

当前项目已经完成“资料导入、数据库建模、审查机制、文本 promote、向量 promote”的底座，下一阶段可以直接进入检索层实现。
