# Draft Template Metadata API Design

**日期：** 2026-05-03

**范围：** `law_helper` 后端为 `/draft` 前端表单提供模板元数据接口

## 1. 目标

当前前端若要接 `/draft`，仍需要手写三套模板的字段配置。这会带来两个直接问题：

- 前后端重复维护 `required_fields` / `optional_fields`
- 模板字段一旦调整，前端容易和后端真实模板脱节

本阶段目标是补一个最小模板元数据接口，让前端直接从后端读取模板字段定义，动态渲染表单。

## 2. 范围定义

本阶段只交付“前端渲染表单必需的信息”，不扩展到模板预览或模板编辑。

交付内容：

- `GET /draft/templates`
- `GET /draft/templates/{template_type}`
- 对应 response schema
- 模板服务最小扩展
- API 合同与测试

不纳入本阶段：

- 返回 `template_text`
- 返回 `scene`
- 返回 `suggested_citations`
- 返回 `derived_placeholders`
- 模板管理后台
- 模板数据库化存储

## 3. 设计原则

- 只暴露前端当前真正需要的字段
- 复用现有 `docs/phase2_materials/template_*.json`，不引入新存储
- 复用现有 `FileTemplateService`，避免平行实现第二套模板加载逻辑
- 返回结构稳定、简单，便于前端直接建类型

## 4. API 设计

### 4.1 `GET /draft/templates`

用途：

- 获取当前可用模板列表
- 用于前端模板选择器或初始化缓存

成功响应示例：

```json
{
  "templates": [
    {
      "template_type": "complaint_letter",
      "template_name": "投诉信（商品质量纠纷）",
      "required_fields": [
        { "name": "consumer_name", "label": "投诉人姓名", "type": "string" }
      ],
      "optional_fields": [
        { "name": "consumer_id_no", "label": "投诉人证件号", "type": "string" }
      ]
    }
  ]
}
```

### 4.2 `GET /draft/templates/{template_type}`

用途：

- 获取单个模板的字段定义
- 用于前端在选定模板后渲染具体表单

成功响应示例：

```json
{
  "template_type": "complaint_letter",
  "template_name": "投诉信（商品质量纠纷）",
  "required_fields": [
    { "name": "consumer_name", "label": "投诉人姓名", "type": "string" }
  ],
  "optional_fields": [
    { "name": "consumer_id_no", "label": "投诉人证件号", "type": "string" }
  ]
}
```

错误约定：

- 不存在的 `template_type` 返回 `404`
- 响应体：

```json
{
  "detail": "unknown template_type: complaint_letter_x"
}
```

## 5. 数据结构

新增 schema：

- `DraftTemplateFieldResponse`
- `DraftTemplateMetadataResponse`
- `DraftTemplateListResponse`

字段定义：

- `template_type: "complaint_letter" | "demand_letter" | "lawsuit_draft"`
- `template_name: string`
- `required_fields: DraftTemplateFieldResponse[]`
- `optional_fields: DraftTemplateFieldResponse[]`

字段项结构：

- `name: string`
- `label: string`
- `type: string`

说明：

- 直接复用现有模板 JSON 的字段定义，不在这一层重新命名或映射
- 前端将 `type` 视为表单控件渲染提示，而不是严格数据库类型

## 6. 后端实现设计

### 6.1 模板服务扩展

在现有 `FileTemplateService` 上增加最小只读能力：

- `list_templates() -> list[DraftTemplate]`

要求：

- 使用当前已加载的模板缓存，不重复读文件
- 返回顺序稳定，建议按 `template_type` 排序

### 6.2 路由扩展

在现有 `app/api/draft.py` 中新增两个 GET 路由：

- `GET /draft/templates`
- `GET /draft/templates/{template_type}`

依赖：

- 复用当前 `get_draft_service` 所使用的同一模板来源
- 不新建独立的模板加载入口

实现方式建议：

- 在 `dependencies.py` 中新增 `get_template_service`
- `get_draft_service` 改为复用 `get_template_service`
- `draft.py` 的 GET 路由直接依赖 `get_template_service`

这样可以避免：

- `/draft` 和 `/draft/templates` 各自维护不同模板实例
- 后续模板扩展时出现行为漂移

## 7. 错误处理

`GET /draft/templates`：

- 正常情况下总返回 `200`
- 若模板目录损坏或文件不合法，维持现有服务异常路径，不在本阶段单独做容错降级

`GET /draft/templates/{template_type}`：

- 未命中模板时，将当前 `KeyError("unknown template_type: ...")` 映射为 `404`
- 不将“未知模板”混成 `500`

## 8. 测试设计

至少新增以下测试：

### 单元测试

- `FileTemplateService.list_templates()` 返回全部模板
- 返回顺序稳定

### 集成测试

- `GET /draft/templates` 返回 200 和 `templates` 列表
- `GET /draft/templates/{template_type}` 返回 200 和单模板结构
- 未知 `template_type` 返回 404

测试要求：

- 继续使用依赖覆盖隔离外部依赖
- 不依赖真实 LLM
- 不依赖真实检索链路

## 9. 文档更新

需要同步更新：

- `docs/frontend_api_contract.md`
- `docs/backend_mvp_runbook.md`（仅在需要补 smoke test 时）

前端文档中要明确：

- 模板列表接口与单模板详情接口的 URL
- 响应结构
- 适用用途：模板选择 + 动态表单渲染

## 10. 成功标准

完成后应满足：

- 前端不再需要手写三套模板字段配置
- 模板字段变更只需要维护后端模板 JSON
- `/draft` 与模板元数据接口读取同一份模板定义
- 未知模板类型不返回 `500`

## 11. 实施边界

这个接口的正确落点是“表单元数据 API”，不是“模板内容 API”。

如果后续前端确实需要：

- 模板正文预览
- 推荐法条预览
- 场景说明

应作为下一轮单独扩展，而不是在本轮一次性塞进接口，避免把最小可用方案扩大成新的接口设计项目。
