# DOCX 到 RAG 中间库

当前仓库先落的是资料导入层，不直接写数据库。流程是：

`docx -> manifest -> documents.jsonl + chunks.jsonl -> 后续 embedding / pgvector`

## 文件

- [data/manifest.jsonl](/D:/coding_projects/law_helper/data/manifest.jsonl): 当前资料清单和元数据
- [scripts/import_materials.py](/D:/coding_projects/law_helper/scripts/import_materials.py): `docx` 解析、清洗、法条切分、JSONL 导出

## 运行

在仓库根目录执行：

```powershell
python scripts/import_materials.py --manifest data/manifest.jsonl --output-dir build/ingestion
```

## 输出

脚本会生成 3 个文件：

- `build/ingestion/documents.jsonl`
- `build/ingestion/chunks.jsonl`
- `build/ingestion/stats.json`

### `documents.jsonl`

文档级记录，保留：

- 文档元数据
- `raw_text`
- `clean_text`
- 解析警告

### `chunks.jsonl`

法规类和规章类默认按 `一条 = 一个 chunk` 导出。每条 chunk 至少带：

- `document_id`
- `doc_type`
- `article_no`
- `part_title`
- `chapter_title`
- `section_title`
- `chunk_text`
- `embedding_text`
- `citation_label`
- `canonical_key`
- `enabled_for_retrieval`

## 当前处理规则

### 1. DOCX 解析

- 直接读取 `word/document.xml`
- 不依赖 Word 段落是否规范

### 2. 大段法规拆分

像 [侵害消费者权益行为处罚办法.docx](/D:/coding_projects/law_helper/data/侵害消费者权益行为处罚办法.docx) 和 [合同违法行为监督处理办法.docx](/D:/coding_projects/law_helper/data/合同违法行为监督处理办法.docx) 这种“多条压成一段”的文件，脚本会先在连续空格后的 `第X条` 前插入换行，再按条识别。

### 3. 目录去除

若文档含 `目录`，脚本会删除目录块，保留正文结构标题。

### 4. 重复版本控制

当前 `manifest` 默认设置为：

- 整部 [中华人民共和国民法典_20200528.docx](/D:/coding_projects/law_helper/data/中华人民共和国民法典_20200528.docx) 可以留在 `data/` 作为原始档案，但不写入 `manifest`
- [民法典-合同编.docx](/D:/coding_projects/law_helper/data/民法典-合同编.docx) 和 [民法典-侵权责任编.docx](/D:/coding_projects/law_helper/data/民法典-侵权责任编.docx) 作为主检索版本

## 下一步

这层跑通以后，下一步建议接两件事：

1. 对 `chunks.jsonl` 生成 embedding
2. 把 `documents.jsonl` 和 `chunks.jsonl` 写入 PostgreSQL + pgvector
