<script setup lang="ts">
defineProps<{
  title: string;
  subtitle: string;
}>();
</script>

<template>
  <div class="module-header">
    <div class="module-copy">
      <h1>{{ title }}</h1>
      <p class="subtitle">{{ subtitle }}</p>
    </div>
    <div class="header-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.module-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 4px 4px;
}

.module-copy {
  min-width: 0;
}

h1 {
  margin: 0;
  color: var(--qm-title);
  font-size: 26px;
  font-weight: 600;
}

.subtitle {
  margin: 6px 0 0;
  color: var(--qm-text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .module-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
