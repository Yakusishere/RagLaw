<script setup>
import { RouterLink } from "vue-router";

const navItems = [
  { label: "首页", to: "/" },
  { label: "智能咨询", to: "/consult" },
  { label: "文书生成", to: "/draft" },
  { label: "法规案例", to: "/library" },
];
</script>

<template>
  <header class="header-wrap">
    <div class="site-shell header-card">
      <RouterLink class="brand" to="/">
        <span class="brand-mark" aria-hidden="true">LH</span>
        <span>
          <strong class="brand-title">Law Helper</strong>
          <span class="brand-subtitle">消费维权辅助工具</span>
        </span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          exact-active-class="active"
          active-class="active"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <RouterLink class="button-primary header-cta" to="/consult">
        开始咨询
      </RouterLink>
    </div>
  </header>
</template>

<style scoped>
.header-wrap {
  position: sticky;
  top: 14px;
  z-index: 20;
  padding: 16px 0 0;
}

.header-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 78px;
  padding: 14px 18px;
  border-radius: 24px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.22);
  backdrop-filter: blur(18px);
  box-shadow: 0 20px 42px rgba(15, 23, 42, 0.08);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: linear-gradient(145deg, var(--color-primary), #102b68);
  color: #f8fafc;
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.brand-title,
.brand-subtitle {
  display: block;
}

.brand-title {
  color: var(--color-text);
  font-size: 15px;
}

.brand-subtitle {
  margin-top: 2px;
  color: var(--color-muted);
  font-size: 12px;
}

.nav {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 999px;
  color: var(--color-text);
  font-weight: 600;
  transition:
    color 200ms ease,
    background-color 200ms ease,
    border-color 200ms ease;
}

.nav-link:hover,
.nav-link:focus-visible,
.nav-link.active {
  background: rgba(30, 58, 138, 0.08);
  color: var(--color-primary);
}

.header-cta {
  min-width: 124px;
}

@media (max-width: 900px) {
  .header-card {
    flex-wrap: wrap;
    justify-content: center;
  }

  .nav {
    order: 3;
    width: 100%;
  }
}

@media (max-width: 560px) {
  .header-card {
    padding: 14px;
    border-radius: 20px;
  }

  .brand {
    width: 100%;
    justify-content: center;
  }

  .header-cta,
  .nav-link {
    width: 100%;
  }
}
</style>
