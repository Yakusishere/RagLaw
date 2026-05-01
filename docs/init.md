# 写给 Codex 的 MVP 系统实现指南

## 1. 项目目标

构建一个小型 RAG 后端系统，用于处理**用户手动提供的中国大陆消费维权资料**。

注意边界：

- 系统**不负责上网找资料**
- 系统**不负责自动爬取**
- 系统只处理用户已经整理好的资料
- 系统目标是：把资料加工成可检索、可引用的 RAG 知识库，并支持问答和模板化文书生成

---

## 2. 输入资料范围

只处理四类资料：

- `law`
- `rule`
- `case`
- `template`

每份输入资料至少包含：

- `title`
- `doc_type`
- `source_name`
- `source_url`
- `effective_date`（optional）
- `version_note`（optional）
- `raw_text`

支持输入格式：

- `md`
- `txt`
- `json`
- `docx`
- `pdf`（仅文本可提取的情况）

---

## 3. MVP 功能范围

需要实现：

1. 资料导入
2. 文本清洗
3. chunk 切分
4. embedding 生成
5. 向量索引
6. 关键词检索 + 向量检索
7. 基于检索结果的问答
8. 基于模板的文书生成
9. 引用输出

不需要实现：

- 爬虫
- 自动法规更新
- 多 agent
- 图谱
- 复杂 rerank
- 全量裁判文书处理
- 前端页面

---

## 4. 技术栈建议

- Python
- FastAPI
- PostgreSQL
- pgvector
- 一个 embedding 模型
- 一个 chat LLM

保持实现简单、模块化、可替换。

---

## 5. 核心系统模块

### A. ingestion

职责：

- 读取用户提供的资料
- 统一转成内部文档对象
- 保存 metadata
- 保存 raw_text

### B. preprocessing

职责：

- 清洗文本
- 去空白、重复标题、无关噪声
- 标准化条号/章节编号

### C. chunking

职责：按文档类型切分

- `law`: 按条切分
- `rule`: 按步骤/段落切分
- `case`: 按 `facts / issue / holding` 切分
- `template`: 按模板块切分，但单独管理

### D. embedding

职责：

- 为 chunk 生成向量
- 写入 pgvector

### E. retrieval

职责：

- 关键词检索
- 向量检索
- 合并结果
- 返回 top context chunks

### F. generation

职责：

- 问答
- 文书生成
- 输出引用

---

## 6. 推荐目录结构

```text
app/
  main.py
  config.py
  api/
    chat.py
    retrieve.py
    draft.py
  services/
    ingestion_service.py
    preprocessing_service.py
    chunking_service.py
    embedding_service.py
    retrieval_service.py
    llm_service.py
    citation_service.py
    template_service.py
  db/
    models.py
    session.py
  schemas/
    document.py
    chat.py
    draft.py
  prompts/
    qa_prompt.txt
    drafting_prompt.txt
scripts/
  import_materials.py
  build_embeddings.py
  rebuild_index.py
tests/
````

---

## 7. 数据模型建议

### documents

字段：

* `id`
* `title`
* `doc_type`
* `source_name`
* `source_url`
* `effective_date`
* `version_note`
* `raw_text`
* `created_at`

### chunks

字段：

* `id`
* `document_id`
* `chunk_type`
* `chunk_text`
* `chunk_order`
* `article_no`
* `section_title`
* `tags` (`jsonb`)
* `citation_label`
* `embedding`
* `created_at`

### templates

字段：

* `id`
* `name`
* `scene`
* `template_type`
* `required_fields`
* `template_text`
* `created_at`

---

## 8. chunk 规则

这是最重要的部分。

### law

* 一条法律条文 = 一个 chunk
* 保留 law title + article number + text
* `citation_label` 示例：`《消费者权益保护法》第24条`

### rule

* 一个办理步骤或一个独立规则点 = 一个 chunk
* 不要把整篇流程说明放成一个 chunk

### case

* 不存整篇原始判决为主检索单元
* 以摘要结构入库：

  * `facts`
  * `issue`
  * `holding`
* 优先让 `holding` 成为主要检索单元

### template

* 不混入普通法条检索主路径
* 单独存储，用于 drafting

---

## 9. 检索策略

MVP 使用混合检索：

* keyword retrieval
* vector retrieval

简单流程：

1. 接收 query
2. 做基础规范化
3. 向量召回 top_k
4. 关键词召回 top_k
5. 合并去重
6. 返回前 n 条 context

优先级建议：

* `law > rule > case`

模板默认不参与普通问答检索。

---

## 10. 问答生成约束

LLM 必须遵守：

* 只能基于检索结果回答
* 不允许编造法条编号
* 检索依据不足时明确说明
* 输出中附引用

建议输出结构：

1. 初步判断
2. 依据
3. 建议步骤
4. 证据建议
5. 风险提示
6. 引用

---

## 11. 文书生成约束

文书生成必须走：

* 结构化 facts 输入
* 选择模板
* 基于模板 + 检索到的法条生成草稿

不要做纯自由生成。

MVP 只支持：

* `complaint_letter`
* `demand_letter`
* `lawsuit_draft`

输出要求：

* 返回 `draft_text`
* 返回 `cited_laws`
* 返回 `missing_fields`

---

## 12. API 范围

至少实现三个接口：

### `POST /retrieve`

输入 query，返回相关 chunks 和引用。

### `POST /chat`

输入 query，执行 retrieval + grounded answer。

### `POST /draft`

输入 `template_type` + structured facts，返回文书草稿。

---

## 13. 成功标准

MVP 完成后应满足：

* 能导入用户提供资料
* 能按类型切分 chunk
* 能建立 embedding 和索引
* 能检索出相关法条/规则/案例摘要
* 能输出带引用的回答
* 能基于模板生成基础文书草稿

---

## 14. 开发顺序

按下面顺序实现：

1. 数据模型
2. 导入与清洗
3. chunking
4. embedding
5. retrieval
6. `/chat`
7. template system
8. `/draft`
9. basic tests

---

## 15. 给 Codex 的一句执行指令

Build a small FastAPI + PostgreSQL + pgvector RAG backend for user-provided Mainland China consumer-rights materials. The system must ingest curated legal materials, clean and chunk them by type, generate embeddings, support hybrid retrieval, answer only from retrieved context with citations, and generate template-based legal drafts from structured facts.
