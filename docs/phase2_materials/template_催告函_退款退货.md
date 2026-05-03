# 催告函（退款退货）模板

## 元信息

- 模板类型：`demand_letter`
- 场景：`refund_return_dispute`
- 文档类型：`template`
- 主要用途：向商家或平台正式催告限期退款、退货、赔偿
- 整理来源：
  - `data/phase2/催告函.jpg` 的结构
  - `data/phase1` 中消保法与实施条例的退款退货规则

## 必填字段

- `sender_name`
- `sender_contact`
- `receiver_name`
- `receiver_address_or_contact`
- `platform_name`
- `product_name`
- `order_no`
- `transaction_time`
- `payment_amount`
- `issue_summary`
- `breach_summary`
- `negotiation_history`
- `demand_items`
- `deadline_days`
- `letter_date`

## 可选字段

- `sender_id_no`
- `receiver_credit_code`
- `refund_amount`
- `compensation_amount`
- `payment_account`
- `legal_basis`
- `attachments_summary`

## 推荐引用依据

- `《中华人民共和国消费者权益保护法》第二十四条`
- `《中华人民共和国消费者权益保护法》第二十五条`
- `《中华人民共和国消费者权益保护法》第五十五条`
- `《中华人民共和国消费者权益保护法实施条例》第十八条`
- `《中华人民共和国消费者权益保护法实施条例》第十九条`
- `《侵害消费者权益行为处罚办法》第八条`
- `《侵害消费者权益行为处罚办法》第九条`

## 模板正文

```text
催告函

致：{{receiver_name}}
联系方式/地址：{{receiver_address_or_contact}}
平台名称：{{platform_name}}

发函人：{{sender_name}}
联系方式：{{sender_contact}}
{{sender_id_block}}

鉴于本人于 {{transaction_time}} 购买 {{product_name}}，订单号为 {{order_no}}，实付金额为人民币 {{payment_amount}} 元。交易完成后出现如下问题：{{issue_summary}}。

截至本函出具之日，您方存在以下未妥善履行义务的情形：
{{breach_summary}}

本人此前已通过 {{negotiation_history}} 与您方沟通处理，但问题至今未解决。

依据说明：
{{legal_basis_or_default}}

现正式催告如下：
{{demand_items}}

请贵方于收到本函后 {{deadline_days}} 日内完成处理。{{payment_account_block}}

如逾期未履行，本人将依法继续采取投诉、举报、申请调解、提起诉讼等措施，并主张因此产生的合理维权成本。

{{attachments_block}}

发函人：{{sender_name}}
日期：{{letter_date}}
```

## 默认依据段建议

如果未传入 `legal_basis`，可默认生成：

```text
依据《中华人民共和国消费者权益保护法》第二十四条、第二十五条，《中华人民共和国消费者权益保护法实施条例》第十八条、第十九条以及《侵害消费者权益行为处罚办法》第八条、第九条等规定，经营者应依法履行退货、退款、更换、赔偿等义务，不得无理拒绝或者故意拖延。
```

## 生成约束

- 这是催告函，不是情绪化投诉文。
- 语言应克制、明确、可执行。
- `demand_items` 应拆成分点。
- 若要求赔偿，需有损失基础；没有损失细节时默认只主张退款、退货、运费等直接项目。

