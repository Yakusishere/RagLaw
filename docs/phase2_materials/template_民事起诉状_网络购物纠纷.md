# 民事起诉状（网络购物纠纷）模板

## 元信息

- 模板类型：`lawsuit_draft`
- 场景：`ecommerce_lawsuit`
- 文档类型：`template`
- 主要用途：用于网络购物质量、退款、平台责任等纠纷的一审民事起诉状草稿
- 整理来源：
  - `data/phase2/民事起诉状.md`
  - `data/phase2/中华人民共和国民事诉讼法_20230901.docx`
  - `data/phase2/网上立案流程图解/*.jpg`
  - `data/phase2/起诉需要材料.jpg`

## 必填字段

- `court_name`
- `plaintiff_name`
- `plaintiff_gender`
- `plaintiff_birth_date`
- `plaintiff_ethnicity`
- `plaintiff_address`
- `plaintiff_contact`
- `defendant_name`
- `defendant_type`
- `defendant_address`
- `cause_of_action`
- `claims`
- `facts_and_reasons`
- `evidence_list`
- `filing_date`

## 可选字段

- `plaintiff_work_info`
- `plaintiff_id_no`
- `legal_representative_block`
- `litigation_agent_block`
- `co_defendant_block`
- `jurisdiction_reason`
- `platform_liability_block`
- `loss_amount_block`
- `attachments_count`

## 推荐引用依据

- `《中华人民共和国民事诉讼法》第二十四条`
- `《中华人民共和国民事诉讼法》第二十九条`
- `《中华人民共和国民事诉讼法》第三十五条`
- `《中华人民共和国民事诉讼法》第三十六条`
- `《中华人民共和国民事诉讼法》第一百二十二条`
- `《中华人民共和国民事诉讼法》第一百二十四条`
- `《中华人民共和国消费者权益保护法》第二十四条`
- `《中华人民共和国消费者权益保护法》第四十四条`
- `《中华人民共和国电子商务法》第三十八条`

## 模板正文

```text
民事起诉状

原告：{{plaintiff_name}}，{{plaintiff_gender}}，{{plaintiff_birth_date}} 生，{{plaintiff_ethnicity}}，{{plaintiff_work_info}}，住 {{plaintiff_address}}，联系方式：{{plaintiff_contact}}。
{{legal_representative_block}}
{{litigation_agent_block}}

被告：{{defendant_name}}（{{defendant_type}}），住/住所地：{{defendant_address}}。
{{co_defendant_block}}

诉讼请求：
{{claims}}

事实与理由：
{{facts_and_reasons}}

{{jurisdiction_reason_block}}
{{platform_liability_block}}

证据和证据来源，证人姓名和住所：
{{evidence_list}}

此致
{{court_name}}

附：
1. 本起诉状副本 {{attachments_count_or_default}} 份；
2. 身份材料、证据材料及其他起诉材料若干。

起诉人：{{plaintiff_name}}
{{filing_date}}
```

## 生成约束

- `claims` 必须分点。
- `facts_and_reasons` 至少写清交易、问题、协商、损失、被告责任。
- 若起诉平台，必须明确平台责任基础，不能空泛写“平台也有责任”。
- `cause_of_action` 应与事实一致，常见可写：
  - `网络购物合同纠纷`
  - `信息网络买卖合同纠纷`
  - `产品责任纠纷`

