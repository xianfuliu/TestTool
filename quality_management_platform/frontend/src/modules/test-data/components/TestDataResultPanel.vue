<script setup lang="ts">
import type { ResultSection } from "../types";

withDefaults(
  defineProps<{
    title: string;
    description?: string;
    sections: ResultSection[];
    loading: boolean;
    generateLabel?: string;
    showEchoAll?: boolean;
    showClear?: boolean;
    showFooter?: boolean;
    showSectionHeader?: boolean;
    inlineRows?: boolean;
  }>(),
  {
    generateLabel: "生成数据",
    showEchoAll: true,
    showClear: true,
    showFooter: true,
    showSectionHeader: true,
    inlineRows: false,
  },
);

const emit = defineEmits<{
  refresh: [field: string];
  copy: [field: string];
  backfill: [field: string];
  generate: [];
  copyAll: [];
  echoAll: [];
  clear: [];
}>();
</script>

<template>
  <section class="work-panel" :class="{ 'work-panel--inline-rows': inlineRows }">
    <div class="panel-head">
      <div class="panel-title-group">
        <h2>{{ title }}</h2>
        <span v-if="description" class="panel-meta">{{ description }}</span>
      </div>
    </div>

    <el-scrollbar class="panel-scroll">
      <div class="panel-body">
        <section v-for="section in sections" :key="section.title" class="result-group">
          <div v-if="showSectionHeader" class="group-head">
            <h3>{{ section.title }}</h3>
            <span>{{ section.rows.length }} 项</span>
          </div>

          <div class="group-card">
            <div v-for="row in section.rows" :key="row.key" class="result-row">
              <div class="row-main">
                <span class="row-label">{{ row.label }}</span>
                <span class="row-value">{{ row.value || "--" }}</span>
              </div>

              <div class="row-actions">
                <el-button
                  v-if="row.canRefresh !== false"
                  size="small"
                  link
                  :disabled="loading || !row.value"
                  @click="emit('refresh', row.key)"
                >
                  刷新
                </el-button>
                <el-button
                  v-if="row.canCopy !== false"
                  size="small"
                  link
                  :disabled="!row.value"
                  @click="emit('copy', row.key)"
                >
                  复制
                </el-button>
                <el-button
                  v-if="row.canBackfill !== false"
                  size="small"
                  link
                  :disabled="!row.value"
                  @click="emit('backfill', row.key)"
                >
                  回填
                </el-button>
              </div>
            </div>
          </div>
        </section>
        <slot name="append" />
      </div>
    </el-scrollbar>

    <div v-if="showFooter" class="panel-footer">
      <el-button type="primary" size="small" :loading="loading" @click="emit('generate')">
        {{ generateLabel }}
      </el-button>
      <el-button size="small" @click="emit('copyAll')">复制</el-button>
      <el-button v-if="showEchoAll" size="small" @click="emit('echoAll')">回显</el-button>
      <el-button v-if="showClear" size="small" plain @click="emit('clear')">清空</el-button>
    </div>
  </section>
</template>

<style scoped>
.work-panel {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e6ebf0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
}

.panel-head {
  display: flex;
  min-height: 50px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #edf1f6;
  background: linear-gradient(180deg, #fafcff 0%, #ffffff 100%);
}

.panel-head h2 {
  margin: 0;
  color: var(--qm-title);
  font-size: 15px;
  font-weight: 600;
}

.panel-meta {
  color: #8a94a6;
  font-size: 12px;
  line-height: 1.5;
}

.panel-scroll {
  flex: 1;
}

.panel-body {
  display: grid;
  gap: 16px;
  padding: 16px 18px;
}

.result-group {
  display: grid;
  gap: 10px;
}

.group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.group-head h3 {
  margin: 0;
  color: var(--qm-title);
  font-size: 13px;
  font-weight: 600;
}

.group-head span {
  color: #8a94a6;
  font-size: 12px;
}

.group-card {
  border: 1px solid #ebeff5;
  border-radius: 14px;
  background: linear-gradient(180deg, #fafbfd 0%, #ffffff 100%);
  padding: 2px 14px;
}

.result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 0;
  border-bottom: 1px dashed #e9eef5;
  transition: background-color 0.2s ease;
}

.result-row:last-child {
  border-bottom: 0;
}

.result-row:hover {
  background: linear-gradient(90deg, rgba(22, 119, 255, 0.04) 0%, rgba(22, 119, 255, 0) 100%);
}

.row-main {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.work-panel--inline-rows .row-main {
  grid-template-columns: minmax(78px, auto) minmax(0, 1fr);
  align-items: center;
  column-gap: 12px;
  row-gap: 0;
}

.work-panel--inline-rows .row-label {
  white-space: nowrap;
}

.work-panel--inline-rows .row-value {
  line-height: 1.45;
}

.row-label {
  color: #5b6472;
  font-size: 12px;
  line-height: 1.4;
}

.row-value {
  min-width: 0;
  color: var(--qm-title);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
  word-break: break-all;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 76px;
  flex-shrink: 0;
}

.row-actions :deep(.el-button) {
  opacity: 0.78;
  transition: opacity 0.2s ease, color 0.2s ease;
}

.result-row:hover .row-actions :deep(.el-button) {
  opacity: 1;
}

.panel-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px 16px;
  border-top: 1px solid #edf1f6;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
}

.panel-footer :deep(.el-button) {
  margin: 0;
  min-height: 28px;
  padding: 6px 12px;
  font-size: 12px;
  width: auto;
}

@media (max-width: 1440px) {
  .work-panel {
    min-height: auto;
  }
}

@media (max-width: 640px) {
  .result-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-footer {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
