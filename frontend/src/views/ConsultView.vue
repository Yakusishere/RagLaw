<script setup>
import { RouterLink } from "vue-router";

const suggestions = [
  "商家拒绝退货退款，我应该先和平台沟通还是直接投诉？",
  "直播间承诺赠品未发，我可以要求补发或赔偿吗？",
  "平台判定商家胜诉，但我还有聊天记录和商品截图，下一步怎么办？",
];

const answerSections = [
  {
    title: "初步判断",
    text: "如果商品宣传、质量或售后承诺与实际不一致，通常可以先主张退货、补发、修理、更换或赔偿。",
  },
  {
    title: "建议步骤",
    text: "先固定商品页面、下单记录、聊天记录和物流信息，再明确诉求，之后走平台协商或投诉流程。",
  },
  {
    title: "证据建议",
    text: "保留承诺截图、开箱视频、签收记录、平台工单与沟通录音，避免只有口头陈述没有材料支撑。",
  },
  {
    title: "风险提醒",
    text: "如果事实仍不完整，结论只能做初步判断。正式投诉或起诉前应再次核对证据和时间线。",
  },
];

const references = [
  "《消费者权益保护法》第24条",
  "平台售后争议处理规则",
  "网络购物退货争议案例摘要",
];
</script>

<template>
  <main class="page-shell">
    <section class="section-card consult-hero">
      <div class="section-head narrow">
        <p class="eyebrow">智能咨询</p>
        <h1 class="display-title">先把问题输入进来，再给你一个可执行的处理思路。</h1>
        <p class="lead-copy">
          这个页面面向普通用户，重点不是展示模型能力，而是帮你快速理清诉求、依据和下一步动作。
        </p>
      </div>

      <div class="consult-grid">
        <section class="composer-panel dark-panel">
          <p class="panel-kicker">描述你的问题</p>
          <label class="field">
            <span>问题描述</span>
            <textarea
              rows="8"
              placeholder="例如：我在平台购买了空气净化器，宣传页写的是全新未拆封，收到后发现机器有使用痕迹，商家拒绝退货。"
            />
          </label>

          <div class="action-row">
            <button class="button-primary" type="button">开始分析</button>
            <button class="button-secondary light-button" type="button">清空内容</button>
          </div>
        </section>

        <section class="section-card suggestion-panel nested-card">
          <p class="eyebrow">你也可以直接用这些问题开始</p>
          <div class="suggestion-list">
            <button
              v-for="item in suggestions"
              :key="item"
              type="button"
              class="suggestion-item"
            >
              {{ item }}
            </button>
          </div>
        </section>
      </div>
    </section>

    <section class="section-card">
      <div class="section-head">
        <p class="eyebrow">回答预览</p>
        <h2 class="section-title">咨询页的重点是让人读得懂、照着做，而不是只看一段长文本。</h2>
      </div>

      <div class="answer-layout">
        <section class="answer-panel">
          <article v-for="item in answerSections" :key="item.title" class="answer-card">
            <h3>{{ item.title }}</h3>
            <p>{{ item.text }}</p>
          </article>
        </section>

        <aside class="reference-panel">
          <div class="reference-card">
            <p class="eyebrow">依据说明</p>
            <ul>
              <li v-for="item in references" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="reference-card warm">
            <p class="eyebrow">下一步推荐</p>
            <p>如果你已经准备投诉平台或向商家正式发函，可以继续进入文书生成页。</p>
            <RouterLink class="button-primary jump-button" to="/draft">
              去生成文书
            </RouterLink>
          </div>
        </aside>
      </div>
    </section>
  </main>
</template>

<style scoped>
.consult-hero {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(244, 247, 251, 0.98)),
    radial-gradient(circle at top right, rgba(30, 64, 175, 0.08), transparent 28%);
}

.consult-grid,
.answer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 18px;
}

.dark-panel {
  padding: 24px;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.97), rgba(23, 37, 84, 0.92)),
    radial-gradient(circle at top left, rgba(180, 83, 9, 0.22), transparent 32%);
}

.panel-kicker {
  margin: 0 0 16px;
  color: rgba(226, 232, 240, 0.74);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.field {
  display: grid;
  gap: 10px;
}

.field span {
  color: #f8fafc;
  font-weight: 700;
}

.field textarea {
  width: 100%;
  resize: vertical;
  min-height: 180px;
  padding: 16px 18px;
  border: 1px solid rgba(226, 232, 240, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  outline: none;
  transition:
    border-color 200ms ease,
    box-shadow 200ms ease;
}

.field textarea::placeholder {
  color: rgba(226, 232, 240, 0.48);
}

.field textarea:focus {
  border-color: rgba(245, 158, 11, 0.42);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.12);
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

.light-button {
  color: #f8fafc;
  border-color: rgba(226, 232, 240, 0.18);
  background: rgba(255, 255, 255, 0.06);
}

.nested-card {
  padding: 24px;
  margin: 0;
}

.suggestion-list {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}

.suggestion-item {
  padding: 16px 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-text);
  text-align: left;
  transition:
    transform 200ms ease,
    box-shadow 200ms ease,
    border-color 200ms ease;
}

.suggestion-item:hover,
.suggestion-item:focus-visible {
  transform: translateY(-1px);
  border-color: rgba(30, 58, 138, 0.22);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.07);
}

.answer-panel {
  display: grid;
  gap: 14px;
}

.answer-card,
.reference-card {
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.answer-card h3,
.reference-card p,
.reference-card ul,
.reference-card li {
  margin: 0;
}

.answer-card h3 {
  font-size: 24px;
  font-family: var(--font-heading);
  font-weight: 600;
}

.answer-card p,
.reference-card p,
.reference-card li {
  margin-top: 8px;
  color: var(--color-muted);
  line-height: 1.75;
}

.reference-panel {
  display: grid;
  gap: 14px;
}

.reference-card ul {
  padding-left: 18px;
}

.warm {
  background:
    linear-gradient(180deg, rgba(255, 251, 235, 0.92), rgba(255, 255, 255, 0.96)),
    radial-gradient(circle at top right, rgba(180, 83, 9, 0.08), transparent 30%);
}

.jump-button {
  margin-top: 14px;
  width: fit-content;
}

@media (max-width: 980px) {
  .consult-grid,
  .answer-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .dark-panel,
  .nested-card {
    padding: 18px;
  }

  .action-row {
    flex-direction: column;
  }
}
</style>
