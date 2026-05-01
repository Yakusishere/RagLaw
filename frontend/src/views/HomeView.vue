<script setup>
import { RouterLink } from "vue-router";

const scenarios = [
  {
    title: "网购退货纠纷",
    text: "商品与宣传不符、商家拒绝退款、平台处理拖延时，先梳理争议点，再给出建议步骤。",
  },
  {
    title: "虚假宣传维权",
    text: "针对夸大宣传、误导销售和承诺不兑现，帮助你整理可以主张的依据与证据方向。",
  },
  {
    title: "平台投诉准备",
    text: "在发起平台投诉、12315 投诉或正式函件前，先把诉求、事实和证据组织清楚。",
  },
];

const featureLinks = [
  {
    title: "智能咨询",
    text: "输入你的问题，获得分步骤建议、依据说明和风险提醒。",
    to: "/consult",
    cta: "去咨询",
  },
  {
    title: "文书生成",
    text: "从投诉函、催告函到起诉草稿，用结构化方式生成可审阅文本。",
    to: "/draft",
    cta: "去生成",
  },
  {
    title: "法规案例",
    text: "按主题检索相关法规、平台规则与案例摘要，先自己查清依据。",
    to: "/library",
    cta: "去检索",
  },
];

const trustPoints = [
  "回答会展示依据，不只给结论。",
  "文书生成以模板为基础，便于审阅和补充。",
  "适合消费维权场景，不承诺替代正式律师意见。",
];

const faqs = [
  {
    question: "适合处理哪些问题？",
    answer: "适合网购纠纷、售后争议、虚假宣传、平台投诉准备等消费维权问题。",
  },
  {
    question: "能直接帮我起诉吗？",
    answer: "可以辅助生成起诉草稿和前期材料，但正式提交前仍需要你结合事实和证据进行核对。",
  },
  {
    question: "我能自己查依据吗？",
    answer: "可以，法规案例页会把法规、规则和案例摘要分开呈现，便于你自行比对。",
  },
];
</script>

<template>
  <main class="page-shell">
    <section class="hero-card">
      <div class="hero-copy">
        <p class="eyebrow">消费维权辅助工具</p>
        <h1 class="display-title">
          先把问题讲清楚，再决定投诉、协商，还是起草文书。
        </h1>
        <p class="lead-copy">
          面向普通用户的消费维权辅助页面。你可以先咨询，再补充证据，再生成对应文书，不必一上来就面对复杂流程。
        </p>

        <div class="hero-actions">
          <RouterLink class="button-primary" to="/consult">开始咨询</RouterLink>
          <RouterLink class="button-secondary" to="/draft">生成文书</RouterLink>
        </div>

        <div class="hero-note">
          <strong>示例问题：</strong>
          商家宣传“七天无理由”，但收到货后以拆封为由拒绝退货，我下一步该怎么做？
        </div>
      </div>

      <div class="hero-side">
        <div class="hero-panel">
          <p class="panel-kicker">你会看到什么</p>
          <div class="flow-list">
            <article class="flow-item">
              <span class="flow-index">01</span>
              <div>
                <h2>建议步骤</h2>
                <p>先做什么、后做什么，一步一步说明，而不是只给模糊结论。</p>
              </div>
            </article>
            <article class="flow-item">
              <span class="flow-index">02</span>
              <div>
                <h2>依据说明</h2>
                <p>结合法规、规则或案例摘要，帮助你判断主张是否站得住。</p>
              </div>
            </article>
            <article class="flow-item">
              <span class="flow-index">03</span>
              <div>
                <h2>文书辅助</h2>
                <p>当你需要正式表达诉求时，可以继续生成投诉函、催告函或起诉草稿。</p>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <p class="eyebrow">常见场景</p>
        <h2 class="section-title">页面先从你最常遇到的消费纠纷出发。</h2>
      </div>

      <div class="three-grid">
        <article v-for="item in scenarios" :key="item.title" class="content-card">
          <h3>{{ item.title }}</h3>
          <p>{{ item.text }}</p>
        </article>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <p class="eyebrow">三大入口</p>
        <h2 class="section-title">先咨询、再生成、也可以先自己查。</h2>
      </div>

      <div class="three-grid">
        <RouterLink
          v-for="item in featureLinks"
          :key="item.to"
          :to="item.to"
          class="content-card content-link"
        >
          <p class="card-label">{{ item.cta }}</p>
          <h3>{{ item.title }}</h3>
          <p>{{ item.text }}</p>
          <span class="inline-link">{{ item.cta }}</span>
        </RouterLink>
      </div>
    </section>

    <section class="section-card trust-card">
      <div class="section-head narrow">
        <p class="eyebrow">可信承诺</p>
        <h2 class="section-title">这是给用户使用的工具，不是堆功能的说明页。</h2>
      </div>

      <div class="trust-list">
        <article v-for="point in trustPoints" :key="point" class="trust-item">
          <span class="trust-mark" aria-hidden="true"></span>
          <p>{{ point }}</p>
        </article>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head narrow">
        <p class="eyebrow">常见问题</p>
        <h2 class="section-title">先回答用户会担心的几个问题。</h2>
      </div>

      <div class="faq-list">
        <article v-for="item in faqs" :key="item.question" class="faq-item">
          <h3>{{ item.question }}</h3>
          <p>{{ item.answer }}</p>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 22px;
  align-items: stretch;
}

.hero-copy {
  padding: 36px;
  border-radius: 34px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.98)),
    radial-gradient(circle at top left, rgba(180, 83, 9, 0.08), transparent 34%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.lead-copy {
  max-width: 58ch;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

.hero-note {
  margin-top: 24px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(30, 58, 138, 0.05);
  color: var(--color-text);
  line-height: 1.7;
}

.hero-side {
  display: flex;
}

.hero-panel {
  width: 100%;
  padding: 28px;
  border-radius: 34px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.97), rgba(15, 23, 42, 0.9)),
    radial-gradient(circle at top right, rgba(180, 83, 9, 0.24), transparent 30%);
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.22);
}

.panel-kicker {
  margin: 0;
  color: rgba(226, 232, 240, 0.74);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.flow-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.flow-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(226, 232, 240, 0.08);
}

.flow-index {
  color: #f59e0b;
  font-family: var(--font-heading);
  font-size: 24px;
  line-height: 1;
}

.flow-item h2,
.flow-item p {
  margin: 0;
}

.flow-item h2 {
  color: #f8fafc;
  font-size: 22px;
  font-family: var(--font-heading);
  font-weight: 600;
}

.flow-item p {
  margin-top: 6px;
  color: rgba(226, 232, 240, 0.72);
  line-height: 1.7;
}

.section-head.narrow {
  max-width: 720px;
}

.card-label {
  margin: 0;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.content-link {
  transition:
    transform 200ms ease,
    box-shadow 200ms ease,
    border-color 200ms ease;
}

.content-link:hover,
.content-link:focus-visible {
  transform: translateY(-2px);
  border-color: rgba(30, 58, 138, 0.2);
  box-shadow: 0 20px 36px rgba(15, 23, 42, 0.08);
}

.inline-link {
  margin-top: 14px;
  color: var(--color-cta);
  font-weight: 700;
}

.trust-card {
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(255, 251, 235, 0.9)),
    radial-gradient(circle at top left, rgba(180, 83, 9, 0.08), transparent 26%);
}

.trust-list,
.faq-list {
  display: grid;
  gap: 14px;
}

.trust-item,
.faq-item {
  display: flex;
  gap: 14px;
  align-items: start;
  padding: 18px 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.trust-mark {
  flex: 0 0 12px;
  width: 12px;
  height: 12px;
  margin-top: 7px;
  border-radius: 999px;
  background: var(--color-cta);
  box-shadow: 0 0 0 6px rgba(180, 83, 9, 0.12);
}

.trust-item p,
.faq-item h3,
.faq-item p {
  margin: 0;
}

.faq-item {
  display: block;
}

.faq-item h3 {
  font-size: 22px;
  font-family: var(--font-heading);
  font-weight: 600;
}

.faq-item p {
  margin-top: 8px;
  color: var(--color-muted);
  line-height: 1.75;
}

@media (max-width: 980px) {
  .hero-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .hero-copy,
  .hero-panel {
    padding: 22px 18px;
    border-radius: 26px;
  }

  .hero-actions {
    flex-direction: column;
  }
}
</style>
