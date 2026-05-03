# 投诉信（商品质量纠纷）模板

## 元信息

- 模板类型：`complaint_letter`
- 场景：`quality_dispute`
- 文档类型：`template`
- 主要用途：用于向商家、平台、12315 或其他主管部门提交正式书面投诉
- 整理来源：
  - `data/phase2/template_投诉信.md`
  - `data/phase2/投诉流程图解/*.jpg`
  - `data/phase1` 中的消保法相关法规

## 必填字段

- `consumer_name`
- `consumer_contact`
- `merchant_name`
- `merchant_contact_or_address`
- `platform_name`
- `product_name`
- `order_no`
- `purchase_channel`
- `purchase_time`
- `payment_amount`
- `issue_summary`
- `issue_details`
- `negotiation_history`
- `claim_items`
- `claim_deadline_days`
- `attachments_summary`
- `complaint_date`

## 可选字段

- `consumer_id_no`
- `merchant_unified_social_credit_code`
- `product_category`
- `receipt_or_invoice_no`
- `legal_basis`
- `regulator_name`
- `extra_losses`

## 推荐引用依据

- `《中华人民共和国消费者权益保护法》第二十四条`
- `《中华人民共和国消费者权益保护法》第二十五条`
- `《中华人民共和国消费者权益保护法》第三十九条`
- `《中华人民共和国消费者权益保护法》第五十五条`
- `《中华人民共和国消费者权益保护法实施条例》第十八条`
- `《中华人民共和国消费者权益保护法实施条例》第十九条`
- `《中华人民共和国消费者权益保护法实施条例》第二十六条`
- `《中华人民共和国消费者权益保护法实施条例》第四十六条`

## 模板正文

```text
投诉信

投诉人：{{consumer_name}}
联系方式：{{consumer_contact}}
{{consumer_id_block}}

被投诉人：{{merchant_name}}
联系方式/地址：{{merchant_contact_or_address}}
平台名称：{{platform_name}}
{{merchant_credit_code_block}}

投诉事项：{{product_name}} 商品质量纠纷

事实经过：
本人于 {{purchase_time}} 通过 {{purchase_channel}} 购买 {{product_name}}，订单号为 {{order_no}}，实付金额为人民币 {{payment_amount}} 元。收货/使用后发现：{{issue_summary}}。

具体情况如下：
{{issue_details}}

在问题发生后，本人已通过 {{negotiation_history}} 与商家/平台进行沟通，但截至目前仍未得到妥善处理。

依据说明：
{{legal_basis_or_default}}

本人现提出如下诉求：
{{claim_items}}

请于收到本投诉后 {{claim_deadline_days}} 日内予以处理并书面回复。若逾期未妥善解决，本人将继续通过 12315 投诉、请求行政调解、申请仲裁或向人民法院提起诉讼等方式依法维权。

附件清单：
{{attachments_summary}}

投诉人：{{consumer_name}}
日期：{{complaint_date}}
```

## 默认依据段建议

如果调用方未单独传入 `legal_basis`，可默认生成：

```text
依据《中华人民共和国消费者权益保护法》第二十四条、第二十五条以及《中华人民共和国消费者权益保护法实施条例》第十八条、第十九条等规定，经营者提供的商品不符合质量要求或者依法应当支持退货的，应当依法履行退货、更换、修理、退款等义务。
```

## 生成约束

- 事实经过必须保留时间、渠道、商品、金额、问题四要素。
- 诉求必须是明确动作，不要只写“给个说法”。
- 若 `claim_items` 中含赔偿请求，应优先要求说明损失构成。
- 若材料不足，不要编造订单号、法条编号或金额。

