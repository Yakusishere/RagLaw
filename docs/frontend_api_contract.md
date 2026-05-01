# Frontend API Contract

本文档面向前端联调，描述当前后端真实可用接口契约。

## Base URL

- 本地开发默认：`http://127.0.0.1:8000`
- 所有请求和响应均使用 `application/json`

## Endpoints

### `GET /health`

用途：
- 判断后端进程是否启动

成功响应：

```json
{
  "status": "ok"
}
```

前端建议：
- 只用于启动探活，不参与业务渲染

### `POST /retrieve`

用途：
- 只做检索，不生成答案
- 适合“法条检索结果页”或“问答前预览依据”

请求体：

```json
{
  "query": "平台内商家虚假宣传如何维权",
  "top_k": 5
}
```

字段说明：
- `query: string`
  - 用户原始问题
  - 后端会做轻量规范化，例如去掉首尾空白
- `top_k: number | null`
  - 可选
  - 控制最终返回结果数
  - 不传时使用后端默认值

成功响应：

```json
{
  "query": "平台内商家虚假宣传如何维权",
  "results": [
    {
      "chunk_id": "law-cn-cpr-44",
      "doc_type": "law",
      "title": "中华人民共和国消费者权益保护法",
      "article_no": "第四十五条",
      "chunk_text": "第四十五条 消费者因经营者利用虚假广告或者其他虚假宣传方式提供商品或者服务，其合法权益受到损害的，可以向经营者要求赔偿。",
      "citation": {
        "chunk_id": "law-cn-cpr-44",
        "citation_label": "《中华人民共和国消费者权益保护法》第四十五条",
        "title": "中华人民共和国消费者权益保护法",
        "doc_type": "law",
        "article_no": "第四十五条",
        "effective_date": "2014-03-15",
        "source_name": "全国人大网",
        "source_url": "https://www.npc.gov.cn/"
      },
      "scores": {
        "vector_score": 0.6513740420341492,
        "keyword_score": 0.10638297872340426,
        "hybrid_score": 0.6196253825375374
      }
    }
  ]
}
```

响应字段说明：
- `query: string`
  - 后端规范化后的查询文本
- `results: RetrievalResultItem[]`
  - 按后端最终排序返回，前面的相关性更高

`RetrievalResultItem` 字段说明：
- `chunk_id: string`
  - chunk 唯一标识
- `doc_type: "law" | "rule"`
  - 当前 MVP 阶段只会返回法规类材料
- `title: string`
  - 法规标题
- `article_no: string | null`
  - 条文号
- `chunk_text: string`
  - 可直接展示的条文正文
- `citation: CitationPayload`
  - 标准化引用信息，前端展示引用优先使用这里
- `scores.vector_score: number | null`
  - 向量召回分数
- `scores.keyword_score: number | null`
  - 关键词召回分数
- `scores.hybrid_score: number | null`
  - 最终排序分数

空值约定：
- `article_no` 可能为 `null`
- `effective_date` 可能为 `null`
- `source_url` 可能为空字符串 `""`
- `vector_score` 和 `keyword_score` 可能有一个为 `null`
  - 这是正常情况，不表示数据异常
  - 前端不要把 `null` 渲染成 `0`

前端展示建议：
- 检索列表主标题建议使用 `citation.citation_label`
- 次级信息建议显示 `title`、`doc_type`、`effective_date`
- 正文建议显示 `chunk_text`
- `scores` 默认不对普通用户展示，可用于调试面板

### `POST /chat`

用途：
- 基于检索结果生成带依据的问答结果
- 适合“法律问答主面板”

请求体：

```json
{
  "query": "电商平台知道商家侵害消费者权益还要承担责任吗"
}
```

说明：
- 当前 `/chat` 内部会先调用检索，再生成回答
- 当前版本不接受 `top_k`

成功响应：

```json
{
  "query": "电商平台知道商家侵害消费者权益还要承担责任吗",
  "answer": {
    "summary": "需要承担责任，但需满足“明知或应知商家侵权”且“未采取必要措施”这两个条件时，平台才依法与商家承担连带责任。",
    "basis": [
      "《中华人民共和国消费者权益保护法》第四十四条",
      "《中华人民共和国电子商务法》第三十八条",
      "《中华人民共和国电子商务法》第八十五条"
    ],
    "suggested_steps": [
      "保留证据并先向商家主张退换或赔偿。"
    ],
    "risk_notes": [
      "模型回答受限于当前检索材料。"
    ],
    "insufficient_basis": false
  },
  "citations": [
    {
      "chunk_id": "law-cn-cpr-44",
      "citation_label": "《中华人民共和国消费者权益保护法》第四十四条",
      "title": "中华人民共和国消费者权益保护法",
      "doc_type": "law",
      "article_no": "第四十四条",
      "effective_date": "2014-03-15",
      "source_name": "全国人大网",
      "source_url": "https://www.npc.gov.cn/"
    }
  ],
  "retrieval": {
    "result_count": 8
  }
}
```

响应字段说明：
- `query: string`
  - 后端规范化后的查询文本
- `answer.summary: string`
  - 主回答文本
  - 当前为完整文本块，前端按富文本之外的普通多行文本渲染即可
- `answer.basis: string[]`
  - 回答重点依据，内容是引用标签，不是完整正文
- `answer.suggested_steps: string[]`
  - 建议动作列表
- `answer.risk_notes: string[]`
  - 风险提示列表
- `answer.insufficient_basis: boolean`
  - `true` 表示检索依据不足
- `citations: CitationPayload[]`
  - 本次问答可追溯的引用列表
- `retrieval.result_count: number`
  - 本次问答底层使用的检索条数

前端展示建议：
- 问答页至少显示：
  - `answer.summary`
  - `answer.basis`
  - `citations`
- 当 `answer.insufficient_basis === true` 时：
  - 将回答降级展示
  - 明确提示“依据不足，仅供参考”
- `answer.basis` 适合展示为短标签
- `citations` 适合展示为“展开查看依据”

## Error Handling

### `422 Unprocessable Entity`

触发场景：
- 缺少必填字段
- 字段类型不匹配

前端建议：
- 当成请求参数错误处理
- 不要重试

### `500 Internal Server Error`

触发场景：
- 数据库不可用
- 上游模型接口不可用
- 服务内部异常

前端建议：
- 给用户展示通用失败提示
- 可提供“重试”按钮
- 不要假设返回体结构稳定

## Integration Notes

- `/retrieve` 和 `/chat` 都依赖当前已 promote 的法规数据和向量数据
- `/chat` 的引用来自检索结果，不保证每次顺序完全一致，但字段结构稳定
- 当前后端未提供流式响应，前端按普通单次请求处理即可
- 当前后端未提供会话上下文，前端若要做多轮对话，需要自行保留历史问题和历史回答

## Real Test Cases

以下问题已完成真实联调：

- `商家拒绝退款怎么办`
- `网购商品质量有问题但商家不同意退货怎么办`
- `平台内商家虚假宣传如何维权`
- `七天无理由退货被商家拒绝怎么办`
- `电商平台知道商家侵害消费者权益还要承担责任吗`
