<script setup lang="ts">
import { computed, onMounted } from "vue";

import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";

const props = withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string;
    compact?: boolean;
  }>(),
  {
    title: "业务组 / 项目上下文",
    subtitle: "统一使用全局主数据，供需求协同、测试中心和自动化模块复用。",
    compact: false,
  },
);

const context = useBusinessProjectContext();
const groups = context.groups;
const projectsOfSelectedGroup = context.projectsOfSelectedGroup;
const loading = context.loading;
const selectedGroupId = context.selectedGroupId;
const selectedProjectId = context.selectedProjectId;

const currentGroupLabel = computed(() => context.selectedGroup.value?.name ?? "未选择业务组");
const currentProjectLabel = computed(() => context.selectedProject.value?.name ?? "未选择项目");

onMounted(() => {
  void context.ensureLoaded();
});
</script>

<template>
  <el-card class="surface-card business-context-card" shadow="never" :class="{ 'business-context-card--compact': compact }">
    <div class="business-context-card__header">
      <div>
        <p class="section-title">{{ title }}</p>
        <p class="section-caption">{{ subtitle }}</p>
      </div>
      <el-button :loading="loading" @click="context.refresh()">刷新上下文</el-button>
    </div>

    <div class="business-context-card__body">
      <div class="business-context-card__selectors">
        <el-select
          :model-value="selectedGroupId"
          clearable
          class="business-context-card__select"
          placeholder="选择业务组"
          @change="context.setGroup"
        >
          <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>

        <el-select
          :model-value="selectedProjectId"
          clearable
          class="business-context-card__select"
          placeholder="选择项目"
          @change="context.setProject"
        >
          <el-option
            v-for="item in projectsOfSelectedGroup"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </div>

      <div class="business-context-card__summary">
        <div class="business-context-card__pill">
          <span>当前业务组</span>
          <strong>{{ currentGroupLabel }}</strong>
        </div>
        <div class="business-context-card__pill">
          <span>当前项目</span>
          <strong>{{ currentProjectLabel }}</strong>
        </div>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.business-context-card {
  margin-bottom: 16px;
}

.business-context-card--compact {
  margin-bottom: 12px;
}

.business-context-card__header,
.business-context-card__body,
.business-context-card__selectors,
.business-context-card__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.business-context-card__body {
  margin-top: 12px;
}

.business-context-card__selectors,
.business-context-card__summary {
  flex: 1;
}

.business-context-card__select {
  width: 100%;
}

.business-context-card__pill {
  min-width: 0;
  flex: 1;
  padding: 12px 14px;
  border: 1px solid #e9edf3;
  border-radius: 12px;
  background: #fafcff;
}

.business-context-card__pill span {
  display: block;
  color: var(--qm-text-secondary);
  font-size: 12px;
}

.business-context-card__pill strong {
  display: block;
  margin-top: 8px;
  color: var(--qm-title);
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

@media (max-width: 960px) {
  .business-context-card__header,
  .business-context-card__body,
  .business-context-card__selectors,
  .business-context-card__summary {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
