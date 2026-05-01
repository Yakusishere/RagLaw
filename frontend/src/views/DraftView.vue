<script setup>
const templates = [
  {
    name: "投诉函",
    note: "适合先向平台或商家正式表达诉求。",
  },
  {
    name: "催告函",
    note: "适合要求限期退款、补发、赔偿或整改。",
  },
  {
    name: "起诉草稿",
    note: "适合准备进一步维权时整理诉讼请求和事实经过。",
  },
];

const fields = [
  "交易时间与订单信息",
  "商品或服务描述",
  "争议经过与已沟通情况",
  "当前诉求",
  "已有证据",
];

const missingFields = [
  "缺少平台工单编号",
  "缺少商品页面承诺截图",
  "缺少退款被拒绝的明确时间点",
];

const citedLaws = [
  "《消费者权益保护法》第24条",
  "《电子商务法》消费者权益相关条款",
  "平台售后处理规则摘要",
];
</script>

<template>
  <main class="page-shell">
    <section class="section-card draft-hero">
      <div class="section-head narrow">
        <p class="eyebrow">文书生成</p>
        <h1 class="display-title">先选模板，再补事实，最后拿到可审阅的草稿。</h1>
        <p class="lead-copy">
          文书页不追求一键生成“最终版本”，而是帮助你把诉求写得清晰，把证据缺口提前暴露出来。
        </p>
      </div>

      <div class="three-grid">
        <article v-for="item in templates" :key="item.name" class="content-card template-card">
          <p class="card-label">模板类型</p>
          <h2>{{ item.name }}</h2>
          <p>{{ item.note }}</p>
        </article>
      </div>
    </section>

    <section class="draft-layout">
      <section class="section-card">
        <div class="section-head">
          <p class="eyebrow">结构化填写</p>
          <h2 class="section-title">页面先引导你补齐关键事实，再进入草稿预览。</h2>
        </div>

        <div class="form-grid">
          <label v-for="item in fields" :key="item" class="mock-field">
            <span>{{ item }}</span>
            <textarea rows="4" :placeholder="`请填写${item}`"></textarea>
          </label>
        </div>
      </section>

      <aside class="draft-side">
        <section class="section-card side-card">
          <p class="eyebrow">缺失提示</p>
          <div class="bullet-list">
            <article v-for="item in missingFields" :key="item" class="bullet-item">
              <span class="bullet-mark" aria-hidden="true"></span>
              <p>{{ item }}</p>
            </article>
          </div>
        </section>

        <section class="section-card side-card">
          <p class="eyebrow">草稿将引用</p>
          <div class="tag-wrap">
            <span v-for="item in citedLaws" :key="item" class="tag">{{ item }}</span>
          </div>
        </section>
      </aside>
    </section>

    <section class="section-card preview-card">
      <div class="section-head">
        <p class="eyebrow">草稿预览</p>
        <h2 class="section-title">结果区域强调可读性和可修改性，而不是像后台日志一样堆文本。</h2>
      </div>

      <div class="draft-preview">
        <div class="paper-sheet">
          <h3>投诉函（示例）</h3>
          <p>
            本人于 2026 年 4 月 3 日通过某平台购买涉案商品。商家在商品页面中明确承诺“七天无理由退货”，但本人签收并拆封核验后发现商品存在与宣传不符的情况。本人随后向商家提出退货退款请求，商家以“已拆封”为由拒绝处理。
          </p>
          <p>
            现本人请求贵方在合理期限内完成退款处理，并对前述宣传与售后承诺不一致的问题作出解释。如逾期仍未妥善处理，本人将继续通过平台投诉、行政投诉及其他合法途径维护自身权益。
          </p>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.draft-hero {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 251, 235, 0.88)),
    radial-gradient(circle at top left, rgba(180, 83, 9, 0.08), transparent 28%);
}

.template-card h2 {
  margin: 14px 0 10px;
  font-size: 28px;
  font-family: var(--font-heading);
  font-weight: 600;
}

.draft-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 18px;
}

.form-grid {
  display: grid;
  gap: 14px;
}

.mock-field {
  display: grid;
  gap: 10px;
}

.mock-field span {
  color: var(--color-text);
  font-weight: 700;
}

.mock-field textarea {
  width: 100%;
  resize: vertical;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text);
  outline: none;
  transition:
    border-color 200ms ease,
    box-shadow 200ms ease;
}

.mock-field textarea:focus {
  border-color: rgba(30, 58, 138, 0.32);
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.12);
}

.draft-side {
  display: grid;
  gap: 18px;
}

.side-card {
  height: fit-content;
}

.bullet-list {
  display: grid;
  gap: 12px;
}

.bullet-item {
  display: flex;
  gap: 12px;
  align-items: start;
}

.bullet-mark {
  flex: 0 0 10px;
  width: 10px;
  height: 10px;
  margin-top: 9px;
  border-radius: 999px;
  background: var(--color-primary);
}

.bullet-item p {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(30, 58, 138, 0.07);
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 700;
}

.preview-card {
  background:
    linear-gradient(180deg, rgba(244, 247, 251, 0.96), rgba(255, 255, 255, 0.96)),
    radial-gradient(circle at top right, rgba(30, 64, 175, 0.08), transparent 28%);
}

.paper-sheet {
  padding: 28px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.06);
}

.paper-sheet h3,
.paper-sheet p {
  margin: 0;
}

.paper-sheet h3 {
  font-size: 32px;
  font-family: var(--font-heading);
  font-weight: 600;
}

.paper-sheet p {
  margin-top: 16px;
  color: var(--color-text);
  line-height: 1.9;
}

@media (max-width: 980px) {
  .draft-layout {
    grid-template-columns: 1fr;
  }
}
</style>
