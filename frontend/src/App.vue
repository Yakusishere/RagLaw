<script setup>
import { RouterView } from "vue-router";
import AppFooter from "./components/AppFooter.vue";
import AppHeader from "./components/AppHeader.vue";
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <RouterView />
    <AppFooter />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}
</style>
