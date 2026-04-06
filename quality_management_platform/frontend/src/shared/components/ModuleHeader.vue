<script setup lang="ts">
import { computed, useSlots } from "vue";

defineProps<{
  title?: string;
  subtitle?: string;
}>();

const slots = useSlots();
const hasActions = computed(() => Boolean(slots.default));
</script>

<template>
  <div v-if="hasActions" class="module-header">
    <div class="header-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.module-header {
  display: flex;
  justify-content: flex-end;
  padding: 2px 4px 10px;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
