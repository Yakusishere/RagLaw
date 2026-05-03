# `/draft` Guidance Enhancement Design

**日期：** 2026-05-04  
**范围：** 为 `POST /draft` 增强确定性的 `next_steps` 输出，并新增 `missing_materials`，用于支撑 Phase 2 文书生成后的行动指引与材料补齐提示。

## 1. 背景

当前 `/draft` 已能：

- 读取模板元数据
- 校验必填字段
- 渲染模板
- 调用 LLM 生成文书草稿

但当前返回的流程提示仍然过于粗糙：

- `missing_fields` 仅覆盖“字段没填”
- `next_steps` 只有固定文案，未区分投诉信、催告函、起诉状
- 接口无法指出“文书能生成，但后续材料仍不齐”

Phase 2 已整理好的资料已经足以支撑更稳定的后端输出：

- `docs/phase2_materials/rule_12315投诉流程说明.md`
- `docs/phase2_materials/rule_网上立案流程说明.md`
- `docs/phase2_materials/rule_起诉材料要求.md`
- `docs/phase2_materials/rule_消费者权益保护法实施条例_投诉处理退货规则摘录.md`

本次只做后端可稳定判定的最小增强，不把流程推理交给 LLM。

## 2. 目标与非目标

### 2.1 目标

1. `/draft` 返回按 `template_type` 区分的 `next_steps`
2. `/draft` 返回 `missing_materials: string[]`
3. 输出逻辑不依赖 LLM，自测与真实联调结果可重复
4. 保持当前 `/draft/templates*` 接口不变
5. 对前端保持增量兼容：仅新增字段，不破坏已有字段含义

### 2.2 非目标

- 不新增数据库表
- 不把流程规则入库
- 不新增 `recommended_attachments` 等新响应块
- 不对证据充分性做法律实质判断
- 不试图从自由文本中高精度抽取全部材料，只做保守提示

## 3. 方案选择

### 方案 A：结构化规则 + 确定性逻辑（采用）

新增一个纯后端规则模块，按模板类型和已填写事实生成：

- `next_steps`
- `missing_materials`

规则来源固定为当前已整理的 Phase 2 文本材料，但运行时不直接解析这些 Markdown 的自然语言段落，而是把 MVP 需要的规则人工沉淀为 Python 常量与映射。

优点：

- 输出稳定
- 易测
- 前端契约稳定
- 真正联调时不容易因文档格式变化而失效

缺点：

- 初期扩展新模板时需要手工补规则

### 方案 B：运行时直接解析 `docs/phase2_materials/*.md`

优点是资料与逻辑看似统一；缺点是 Markdown 一改格式就可能影响接口行为，且测试脆弱。

### 方案 C：让 LLM 同时生成 `next_steps` / `missing_materials`

实现快，但输出不可预测，不适合作为前端稳定依赖的后端契约。

## 4. 设计概览

### 4.1 响应结构

`DraftResponse` 在现有字段基础上新增：

- `missing_materials: string[]`

最终响应字段为：

- `template_type`
- `template_name`
- `draft_text`
- `missing_fields`
- `missing_materials`
- `cited_laws`
- `next_steps`

这是一个纯增量变更。已有前端如果忽略未知字段，不会被破坏。

### 4.2 新增后端边界

新增一个“文书指引规则”模块，职责单一：

- 接收 `template_type`
- 接收 `facts`
- 接收 `missing_fields`
- 生成 `missing_materials`
- 生成 `next_steps`

它不负责：

- 生成文书正文
- 模板加载
- 检索
- LLM 调用

`DraftService.generate()` 继续负责主流程，只在返回前调用该模块补齐指引信息。

### 4.3 数据来源

MVP 规则以当前 Phase 2 文本为依据，沉淀为代码内结构化配置：

- 投诉信 / 催告函：
  - `rule_12315投诉流程说明.md`
  - `rule_消费者权益保护法实施条例_投诉处理退货规则摘录.md`
- 起诉状：
  - `rule_网上立案流程说明.md`
  - `rule_起诉材料要求.md`

后续若模板增多，再考虑把这些规则外置成独立 JSON/YAML。

## 5. `missing_materials` 判定规则

### 5.1 总原则

`missing_materials` 只提示“后端可以保守判断出可能仍未准备的材料”，不声称这些材料绝对缺失。

判定来源分两类：

1. **结构化字段缺失**
   - 例如 `plaintiff_id_no` 为空，可提示“原告身份证明材料”
2. **证据摘要文本未覆盖关键材料关键词**
   - 例如 `evidence_list`、`attachments_summary` 未提到订单、支付记录、聊天记录等，可提示相应材料

### 5.2 关键词检测边界

MVP 不做 NLP 抽取，只做关键词组命中：

- 每类材料配置一组中文关键词
- 从证据类字段拼接出的文本中做不区分大小写匹配
- 任一关键词命中即视为该类材料“已体现”

这种方式不完美，但可预测、可测试，适合当前阶段。

### 5.3 模板级规则

#### `complaint_letter`

优先检查：

- 订单页面
- 支付记录
- 聊天/协商记录
- 商品问题照片或视频
- 发票或收据
- 平台售后/投诉记录

主要读取字段：

- `attachments_summary`
- `issue_details`
- `negotiation_history`

#### `demand_letter`

优先检查：

- 订单页面
- 支付记录
- 聊天/协商记录
- 商品问题照片或视频
- 发函前已有售后处理记录

主要读取字段：

- `attachments_summary`
- `issue_summary`
- `breach_summary`
- `negotiation_history`

不要求在生成催告函前就必须具备“催告函送达凭证”；这是发出之后才会产生的材料，因此不计入 `missing_materials`。

#### `lawsuit_draft`

优先检查：

- 原告身份证明材料
- 被告主体信息材料
- 订单页面
- 支付记录
- 发票或收据
- 聊天记录
- 商品问题照片/视频截图
- 平台售后或投诉处理记录
- 送达地址确认书

主要读取字段：

- `evidence_list`
- `plaintiff_id_no`
- `defendant_type`

其中：

- `plaintiff_id_no` 为空时，提示“原告身份证明材料”
- 若 `defendant_type` 指向公司/商家，且 `evidence_list` 未体现工商登记、统一社会信用代码或企业主体信息，提示“被告主体信息材料”
- `evidence_list` 未体现“送达地址确认书”时，提示该材料

## 6. `next_steps` 生成规则

### 6.1 通用规则

所有模板都遵循：

1. 若 `missing_fields` 非空，`next_steps` 第一条固定为“先补全必填字段再重新生成或核对文书”
2. 若 `missing_materials` 非空，较靠前位置提示优先补齐材料
3. 剩余步骤按模板类型追加固定流程步骤

### 6.2 `complaint_letter`

完整场景下的核心步骤：

1. 核对投诉对象、事实经过、诉求和期限
2. 整理关键证据材料
3. 先向商家或平台提交投诉信并留痕
4. 未解决时转入 `12315` 投诉或行政调解
5. 关注 `7 个工作日` 处理告知与 `60 日` 调解期限
6. 仍无果时再考虑仲裁或起诉

### 6.3 `demand_letter`

完整场景下的核心步骤：

1. 核对催告事项、金额、履行期限
2. 通过可留痕方式送达催告函
3. 保存送达凭证
4. 逾期未履行时转入投诉、调解或诉讼
5. 继续补强订单、支付、沟通、问题证据

### 6.4 `lawsuit_draft`

完整场景下的核心步骤：

1. 核对法院、案由、诉讼请求、事实与理由
2. 准备身份材料、被告主体信息、证据目录、送达地址确认书
3. 通过 `人民法院在线服务` 进入在线立案
4. 按流程填写当事人信息、标的金额、诉讼请求并上传材料
5. 提交后关注 `7 日内` 是否立案或要求补正

## 7. 服务流程调整

### 7.1 字段不完整时

当前逻辑在 `missing_fields` 非空时不会调用检索与 LLM。这个行为保持不变。

新增变化：

- 即使未进入 LLM 生成，也要返回：
  - `missing_materials`
  - 与当前状态匹配的 `next_steps`

这样前端在“字段未填完”的情况下也能展示更完整的引导。

### 7.2 字段完整时

保持当前流程：

1. 加载模板
2. 检索依据
3. 渲染模板
4. 调用 LLM 生成正文

在返回前新增：

5. 计算 `missing_materials`
6. 生成 `next_steps`

## 8. API 契约

### 8.1 `POST /draft`

请求体不变。

响应新增：

```json
{
  "template_type": "lawsuit_draft",
  "template_name": "民事起诉状（网络购物纠纷）",
  "draft_text": "民事起诉状正文...",
  "missing_fields": [],
  "missing_materials": [
    "原告身份证明材料",
    "送达地址确认书"
  ],
  "cited_laws": [
    "《中华人民共和国民事诉讼法》第一百二十四条"
  ],
  "next_steps": [
    "优先补齐以下材料：原告身份证明材料、送达地址确认书。",
    "核对受理法院、案由、诉讼请求与事实理由是否准确。",
    "整理身份材料、被告主体信息、证据目录后再进入人民法院在线服务提交立案。"
  ]
}
```

### 8.2 兼容性约束

- `missing_materials` 必须始终返回数组
- 即使没有缺失，也返回 `[]`
- `next_steps` 仍保持数组，不改成对象结构
- `/draft/templates` 和 `/draft/templates/{template_type}` 不受本次变更影响

## 9. 测试与联调

### 9.1 单元测试

至少覆盖：

- 三个模板的 `missing_materials` 基本判定
- `missing_fields` 非空时 `next_steps` 是否优先补字段
- `missing_materials` 非空时 `next_steps` 是否优先补材料
- 公司被告场景下“被告主体信息材料”提示
- 关键词已覆盖时不重复提示材料

### 9.2 集成测试

至少覆盖：

- `POST /draft` 响应 shape 新增 `missing_materials`
- 缺字段场景返回 `missing_materials` 和增强后的 `next_steps`
- 完整字段场景返回草稿、`missing_materials` 与模板相关步骤

### 9.3 真实联调

至少跑四类真实请求：

1. 投诉信完整案例
2. 催告函完整案例
3. 起诉状完整案例
4. 至少一个缺字段案例

联调检查重点：

- SSE 改动不受影响
- 新字段不会破坏前端已有解析
- `missing_materials` 不出现明显反常提示
- `next_steps` 与模板类型一致

## 10. 风险与约束

### 风险 1：关键词判定过粗

可能出现“用户其实有材料，但文本没写到”的提示。

处理方式：

- 保持文案为“优先补齐”或“建议准备”，避免宣称绝对缺失
- 把逻辑设计成可扩展配置，后续可细化关键词

### 风险 2：规则硬编码分散

若直接把规则写进 `DraftService`，后续会难维护。

处理方式：

- 单独抽出纯规则模块
- `DraftService` 只做编排

### 风险 3：接口变更影响前端

本次是增量字段，风险较低，但仍需要更新联调文档并做真实 API 回归。

## 11. 结论

本次采用“结构化规则 + 确定性逻辑”的最小方案：

- 不动模板接口
- 不引入新存储
- 为 `/draft` 增强稳定可测的 `next_steps`
- 新增 `missing_materials`
- 用真实联调验证三个模板和缺字段场景

这能把 Phase 2 中已有的流程规则和材料清单真正接到后端返回里，同时保持当前实现复杂度可控。
