<script setup>
const filters = ["全部", "法律法规", "平台规则", "案例摘要"];

const results = [
  {
    title: "《消费者权益保护法》第24条",
    type: "法律法规",
    text: "经营者提供的商品或者服务不符合质量要求的，消费者可以依照国家规定、当事人约定退货或者要求经营者履行其他义务。",
  },
  {
    title: "网络交易平台售后规则摘要",
    type: "平台规则",
    text: "遇到商家拒绝处理时，应先提交订单记录、聊天记录、商品页面承诺截图和签收凭证。",
  },
  {
    title: "网购商品与宣传不符争议案例",
    type: "案例摘要",
    text: "在商品宣传内容足以影响消费者下单决定时，经营者应对宣传真实性承担相应义务。",
  },
];

const detailTags = ["退货退款", "宣传不符", "举证建议", "平台投诉"];
</script>

<template>
  <main class="page-shell">
    <section class="section-card library-hero">
      <div class="section-head narrow">
        <p class="eyebrow">法规案例</p>
        <h1 class="display-title">当你想自己先查依据时，这一页应该足够清楚。</h1>
        <p class="lead-copy">
          检索页服务的是“我先自己看明白”的需求，所以界面重点是分类、引用和对比阅读，不是密密麻麻的后台列表。
        </p>
      </div>

      <div class="search-shell">
        <label class="search-box">
          <span class="search-label">搜索法规、规则或案例</span>
          <input type="text" placeholder="例如：七天无理由退货、宣传不符、平台拒绝退款" />
        </label>

        <div class="chip-row">
          <button v-for="item in filters" :key="item" type="button" class="chip">
            {{ item }}
          </button>
        </div>
      </div>
    </section>

    <section class="library-layout">
      <section class="section-card">
        <div class="section-head">
          <p class="eyebrow">检索结果</p>
          <h2 class="section-title">结果列表按材料类型分层，方便快速判断该先看哪类依据。</h2>
        </div>

        <div class="result-list">
          <article v-for="item in results" :key="item.title" class="result-card">
            <div class="result-head">
              <h3>{{ item.title }}</h3>
              <span class="result-type">{{ item.type }}</span>
            </div>
            <p>{{ item.text }}</p>
            <button class="text-button" type="button">查看详情</button>
          </article>
        </div>
      </section>

      <aside class="section-card detail-card">
        <div class="section-head compact">
          <p class="eyebrow">详情阅读</p>
          <h2 class="section-title">《消费者权益保护法》第24条</h2>
        </div>

        <p class="detail-copy">
          当商品或服务不符合质量要求时，消费者可以依照国家规定、当事人约定退货，或者要求经营者履行更换、修理、重作、减少价款等义务。
        </p>

        <div class="tag-wrap">
          <span v-for="item in detailTags" :key="item" class="tag">{{ item }}</span>
        </div>

        <div class="detail-actions">
          <button class="button-primary" type="button">复制引用</button>
          <button class="button-secondary" type="button">加入咨询</button>
        </div>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.library-hero {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(244, 247, 251, 0.98)),
    radial-gradient(circle at top left, rgba(30, 64, 175, 0.08), transparent 24%);
}

.search-shell {
  display: grid;
  gap: 16px;
}

.search-box {
  display: grid;
  gap: 10px;
}

.search-label {
  color: var(--color-text);
  font-weight: 700;
}

.search-box input {
  width: 100%;
  min-height: 58px;
  padding: 0 18px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text);
  outline: none;
  transition:
    border-color 200ms ease,
    box-shadow 200ms ease;
}

.search-box input:focus {
  border-color: rgba(30, 58, 138, 0.28);
  box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.12);
}

.chip-row,
.tag-wrap,
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chip,
.tag {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text);
  font-weight: 700;
}

.chip:hover,
.chip:focus-visible {
  border-color: rgba(30, 58, 138, 0.22);
  background: rgba(30, 58, 138, 0.06);
}

.library-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: 18px;
}

.result-list {
  display: grid;
  gap: 14px;
}

.result-card {
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.result-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}

.result-head h3,
.result-card p {
  margin: 0;
}

.result-head h3 {
  font-size: 24px;
  font-family: var(--font-heading);
  font-weight: 600;
}

.result-type {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(30, 58, 138, 0.08);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
}

.result-card p {
  margin-top: 10px;
  color: var(--color-muted);
  line-height: 1.75;
}

.text-button {
  margin-top: 14px;
  padding: 0;
  color: var(--color-cta);
  font-weight: 700;
  background: transparent;
}

.detail-card {
  height: fit-content;
  background:
    linear-gradient(180deg, rgba(255, 251, 235, 0.88), rgba(255, 255, 255, 0.96)),
    radial-gradient(circle at top right, rgba(180, 83, 9, 0.08), transparent 30%);
}

.section-head.compact {
  margin-bottom: 18px;
}

.detail-copy {
  margin: 0 0 18px;
  color: var(--color-text);
  line-height: 1.85;
}

.detail-actions {
  margin-top: 18px;
}

@media (max-width: 980px) {
  .library-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .result-head {
    flex-direction: column;
  }

  .detail-actions {
    flex-direction: column;
  }
}
</style>
