# 后端 RAG MVP 设计说明

**日期：** 2026-05-01

**范围：** `law_helper` 项目的后端第一阶段 MVP

## 1. 设计目标

本阶段目标是在现有资料导入、数据库建模、staging/review/promote、embedding 装载底座之上，补齐一个可运行的后端应用层，使系统能够：

- 基于已入库的消费维权资料执行混合检索
- 返回可直接展示和调试的引用化检索结果
- 基于检索结果生成 grounded answer
- 为前端后续接入提供稳定 API

本阶段明确不包含：

- 爬虫、自动更新资料
- 多 agent、知识图谱、复杂 rerank
- 前端实现
- 模板管理后台
- 正式的 `/draft` 文书生成接口

`/draft` 被定义为第二阶段功能，不纳入第一阶段 MVP 交付。

## 2. 当前代码基线

当前项目已经完成：

- `docx -> JSONL -> PostgreSQL staging -> review -> promote`
- `embedding JSONL -> embedding staging -> review -> promote`
- `rag.documents`、`rag.chunks`、`rag.chunk_embeddings` 等运营表
- 针对文本和向量的 blocker/warning 审查函数

当前项目尚未完成：

- Python 应用层目录和配置体系
- 应用内数据库访问封装
- 检索 SQL / retrieval service
- FastAPI API
- LLM grounded answer
- 模板系统

当前运营资料实际只包含 `law` 和 `rule` 两类，尚无 `case`、`template` 资料进入运营库。因此第一阶段后端设计必须围绕现有资料结构展开，不应为了“完整覆盖 init 文档中的所有目标类型”而扩大范围。

## 3. 第一阶段 MVP 定义

### 3.1 交付能力

第一阶段后端 MVP 交付以下能力：

- `POST /retrieve`
  - 输入自然语言问题
  - 执行向量检索与关键词检索
  - 合并、去重、排序
  - 返回 chunks、citation、score、metadata

- `POST /chat`
  - 输入自然语言问题
  - 内部先执行 retrieval
  - 基于检索结果生成 grounded answer
  - 输出结构化回答和引用

- 健康检查与基础配置
  - `GET /health`
  - 环境变量配置
  - 应用启动和依赖校验

### 3.2 不纳入第一阶段的能力

- `POST /draft`
- `template` 资料入库
- `case` 专用结构切分
- 会话记忆
- 用户体系
- 中文分词优化
- 复杂重排序

## 4. 总体架构

后端第一阶段采用“薄 API + 服务层 + SQL 读模型 + 外部 LLM/Embedding API”的简单结构。

### 4.1 分层

- `app/main.py`
  - FastAPI 应用入口
  - 注册路由和生命周期

- `app/config.py`
  - 环境变量读取
  - 数据库、OpenAI、模型名、top_k 等配置

- `app/db/`
  - 只做连接与查询执行
  - 不在第一阶段引入复杂 ORM 映射

- `app/services/retrieval_service.py`
  - query 规范化
  - 向量召回
  - 关键词召回
  - 合并排序

- `app/services/citation_service.py`
  - 把 chunk 结果转成统一 citation 结构

- `app/services/llm_service.py`
  - 调用 LLM 生成 grounded answer

- `app/api/retrieve.py`
  - `/retrieve`

- `app/api/chat.py`
  - `/chat`

### 4.2 为什么不优先上 ORM

当前数据库已经以 SQL schema 和 SQL function 为核心，且检索逻辑会显著依赖：

- pgvector 距离计算
- `rag.chunks` 与 `rag.chunk_embeddings` join
- PostgreSQL 原生排序和过滤

第一阶段使用轻量查询封装比引入完整 ORM 更稳，能减少建模成本和隐式复杂度。

## 5. 数据与检索设计

### 5.1 读取来源

检索层只读取以下运营表：

- `rag.chunks`
- `rag.chunk_embeddings`

不直接读取 staging 表。

### 5.2 检索候选范围

第一阶段仅检索：

- `enabled_for_retrieval = true`
- `doc_type in ('law', 'rule')`

默认排除：

- `template`
- 未启用资料
- staging 数据

### 5.3 向量检索

向量检索依赖已 promote 的真实 embedding 模型。第一阶段上线前必须将当前 `mock-hash-16` 替换为真实 embedding 结果，例如 `text-embedding-3-small`。

向量检索过程：

1. 接收 query
2. 调用 embedding API 生成 query embedding
3. 按指定模型名在 `rag.chunk_embeddings` 中做 top_k 相似度检索
4. join `rag.chunks` 获取业务字段
5. 返回标准化候选结果

第一阶段要求模型名固定配置，不做多模型动态切换。

### 5.4 关键词检索

由于当前中文检索不应过早绑定复杂分词方案，第一阶段采用简化关键词检索：

- 对 query 做基础空白清洗
- 使用 `search_text` 做 `ILIKE` 匹配
- 可选增加 `pg_trgm` 方案作为增强，但不是第一阶段前置条件

第一阶段不依赖 PostgreSQL 中文分词插件。

### 5.5 混合检索

混合检索流程：

1. 执行向量召回，取 `vector_top_k`
2. 执行关键词召回，取 `keyword_top_k`
3. 按 `chunk_id` 去重
4. 生成统一混合分数
5. 对相同分值按文档优先级排序
6. 取最终 `final_top_k`

第一阶段采用轻量排序策略：

- 文档类型优先级：`law > rule`
- 同类型内优先相似度更高者
- 法条类按 `article_no_int` 保持可解释顺序

不做学习排序，不做交叉编码 rerank。

## 6. 引用设计

每个检索结果必须能稳定输出 citation。citation 结构应至少包含：

- `chunk_id`
- `citation_label`
- `title`
- `doc_type`
- `article_no`
- `effective_date`
- `source_name`
- `source_url`

如果 `source_url` 缺失，则允许返回空值，但 API 不应报错。因为当前资料元数据中仍有 `source_url` 缺口，这是已知 warning，不应阻塞第一阶段 API。

## 7. API 设计

### 7.1 `GET /health`

用途：

- 确认服务进程可用
- 返回基础状态信息

响应示例：

```json
{
  "status": "ok"
}
```

### 7.2 `POST /retrieve`

请求体：

```json
{
  "query": "商家拒绝退款怎么办",
  "top_k": 8
}
```

响应体：

```json
{
  "query": "商家拒绝退款怎么办",
  "results": [
    {
      "chunk_id": "cn_consumer_rights_law_20131025:article:0024",
      "doc_type": "law",
      "title": "中华人民共和国消费者权益保护法",
      "article_no": "第二十四条",
      "chunk_text": "...",
      "citation": {
        "citation_label": "《中华人民共和国消费者权益保护法》第二十四条",
        "source_name": "用户提供资料",
        "source_url": ""
      },
      "scores": {
        "vector_score": 0.91,
        "keyword_score": 0.75,
        "hybrid_score": 0.87
      }
    }
  ]
}
```

设计要求：

- `top_k` 允许缺省，由服务端默认值补齐
- 当没有命中结果时返回空数组，不抛 500
- 只返回最终排序后的结果，不暴露内部 staging 信息

### 7.3 `POST /chat`

请求体：

```json
{
  "query": "网购商品质量有问题，商家不同意退货怎么办？"
}
```

响应体：

```json
{
  "query": "网购商品质量有问题，商家不同意退货怎么办？",
  "answer": {
    "summary": "...",
    "basis": [
      "...",
      "..."
    ],
    "suggested_steps": [
      "...",
      "..."
    ],
    "risk_notes": [
      "..."
    ],
    "insufficient_basis": false
  },
  "citations": [
    {
      "chunk_id": "...",
      "citation_label": "...",
      "title": "...",
      "article_no": "..."
    }
  ],
  "retrieval": {
    "result_count": 6
  }
}
```

设计要求：

- `/chat` 必须内部复用 retrieval service
- 若检索结果不足，返回“依据不足”而不是编造结论
- 回答必须附 citations
- 第一阶段不做流式输出

## 8. LLM 生成约束

LLM 必须遵守以下硬约束：

- 只能根据提供的检索上下文回答
- 不得编造法条编号、文号、出处
- 检索依据不足时必须明确说明
- 输出结构固定，便于前端渲染

建议 prompt 输出结构：

1. 初步判断
2. 依据
3. 建议步骤
4. 风险提示
5. 引用

第一阶段不要求模型生成“绝对正确的法律结论”，要求的是：

- 可追溯
- 可引用
- 不胡编

## 9. 配置设计

第一阶段配置项至少包括：

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `RETRIEVAL_VECTOR_TOP_K`
- `RETRIEVAL_KEYWORD_TOP_K`
- `RETRIEVAL_FINAL_TOP_K`

所有配置通过环境变量注入，不把密钥写入仓库。

## 10. 测试策略

第一阶段测试重点不在前端联调，而在服务行为可验证。

至少覆盖：

- query 规范化
- 向量检索结果映射
- 关键词检索结果映射
- 混合去重与排序
- citation 结构输出
- `/retrieve` API 正常返回
- `/chat` 在“有依据”和“依据不足”两种场景下的行为

如果测试环境不方便直连真实 OpenAI，则：

- retrieval 相关测试优先做本地数据库集成测试
- LLM 相关测试通过 mock client 完成

## 11. 第二阶段预留

第二阶段再引入以下内容：

- `template` 文档结构和入库
- 文书模板字段校验
- `POST /draft`
- 基于模板和检索结果的文书草稿生成

原因：

- 当前运营资料没有模板实体
- 模板生成需要先明确模板来源、字段结构、缺失字段判断规则
- 若现在一并实现，会把第一阶段从“检索问答 MVP”扩大成“检索问答 + 模板系统”双项目

## 12. 实施原则

- 先读运营表，不改动现有 ingestion/promote 脚本主线
- 先做可用 API，再补扩展能力
- 先保证 grounded 和 citation，再追求回答丰富度
- 先让后端围绕现有 `law/rule` 跑通，再扩展 `case/template`

## 13. 结论

第一阶段后端 MVP 的正确落点是：

- 基于现有资料库和向量库
- 建立 FastAPI 应用层
- 实现混合检索
- 输出引用化结果
- 提供 grounded `/chat`

`/draft` 不应混入本阶段交付，应作为第二阶段单独设计和实现。
