<template>
  <footer class="footer-wrap">
    <div class="site-shell footer-card">
      <div>
        <p class="footer-title">Law Helper</p>
        <p class="footer-copy">
          用于消费维权咨询、依据查找和文书辅助。回答与草稿仅供参考，正式维权前仍应结合完整证据材料审阅。
        </p>
      </div>

      <div class="footer-meta">
        <span>消费纠纷咨询</span>
        <span>文书辅助</span>
        <span>法规案例检索</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer-wrap {
  padding: 0 0 28px;
}

.footer-card {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.05);
}

.footer-title,
.footer-copy {
  margin: 0;
}

.footer-title {
  font-family: var(--font-heading);
  font-size: 24px;
  font-weight: 600;
}

.footer-copy {
  max-width: 58ch;
  margin-top: 8px;
  color: var(--color-muted);
  line-height: 1.7;
}

.footer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: end;
}

.footer-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(30, 58, 138, 0.06);
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 700;
}

@media (max-width: 780px) {
  .footer-card {
    flex-direction: column;
    align-items: start;
  }

  .footer-meta {
    justify-content: start;
  }
}
</style>
