<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  title: string;
  status: string;
  total: number;
  passed: number;
  failed: number;
  skipped?: number;
  duration?: number;
  startTime?: string | null;
  endTime?: string | null;
}>();

const skippedCount = computed(() => Number(props.skipped || 0));
const totalCount = computed(() => Math.max(0, Number(props.total || 0)));
const passedCount = computed(() => Math.max(0, Number(props.passed || 0)));
const failedCount = computed(() => Math.max(0, Number(props.failed || 0)));
const passRate = computed(() => (totalCount.value ? Math.round((passedCount.value / totalCount.value) * 100) : 0));
const failedRate = computed(() => (totalCount.value ? Math.round((failedCount.value / totalCount.value) * 100) : 0));
const skippedRate = computed(() => (totalCount.value ? Math.max(0, 100 - passRate.value - failedRate.value) : 0));
const chartStyle = computed(() => {
  const passDegree = (passRate.value / 100) * 360;
  const failedDegree = ((passRate.value + failedRate.value) / 100) * 360;
  const skippedDegree = ((passRate.value + failedRate.value + skippedRate.value) / 100) * 360;
  return {
    background: `conic-gradient(#16a34a 0deg ${passDegree}deg, #ef4444 ${passDegree}deg ${failedDegree}deg, #f59e0b ${failedDegree}deg ${skippedDegree}deg, #e5eaf3 ${skippedDegree}deg 360deg)`,
  };
});

const statusText = computed(() => {
  const map: Record<string, string> = {
    success: "SUCCESS",
    failed: "FAIL",
    running: "RUNNING",
    skipped: "SKIPPED",
    pending: "PENDING",
  };
  return map[props.status] || String(props.status || "UNKNOWN").toUpperCase();
});

const statusClass = computed(() => `status-${props.status || "pending"}`);

function formatDuration(value?: number) {
  const seconds = Number(value || 0);
  if (!seconds) {
    return "-";
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${(seconds % 60).toFixed(0)}s`;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }
  return String(value).replace("T", " ").slice(0, 19);
}

</script>

<template>
  <section class="report-summary">
    <div class="summary-main">
      <div class="summary-title-row">
        <h2>{{ title }}</h2>
        <span class="status-pill" :class="statusClass">{{ statusText }}</span>
        <div class="summary-title-actions">
          <slot name="actions" />
        </div>
      </div>
      <div class="summary-meta">
        <span>执行时间：{{ formatDate(startTime) }} - {{ formatDate(endTime) }}</span>
      </div>
      <div class="stat-grid">
        <div class="stat-item">
          <span>总用例</span>
          <strong>{{ totalCount }}</strong>
        </div>
        <div class="stat-item success">
          <span>成功</span>
          <strong>{{ passedCount }}</strong>
        </div>
        <div class="stat-item failed">
          <span>失败</span>
          <strong>{{ failedCount }}</strong>
        </div>
        <div class="stat-item skipped">
          <span>跳过</span>
          <strong>{{ skippedCount }}</strong>
        </div>
        <div class="stat-item">
          <span>耗时</span>
          <strong>{{ formatDuration(duration) }}</strong>
        </div>
      </div>
    </div>
    <div class="summary-chart">
      <div class="donut-chart" :style="chartStyle">
        <div class="donut-hole">
          <strong>{{ passRate }}%</strong>
          <span>通过率</span>
        </div>
      </div>
      <div class="chart-legend">
        <span><i class="legend-dot success"></i>成功 {{ passRate }}%</span>
        <span><i class="legend-dot failed"></i>失败 {{ failedRate }}%</span>
        <span><i class="legend-dot skipped"></i>跳过 {{ skippedRate }}%</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.report-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(31, 35, 41, 0.04);
}

.summary-main {
  min-width: 0;
}

.summary-title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.summary-title-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  margin-left: 2px;
}

.summary-title-row h2 {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: #111827;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 26px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 22px;
  padding: 0 11px;
}

.status-success {
  background: #e8f8ef;
  color: #168a4a;
}

.status-failed {
  background: #fff0f0;
  color: #d92d20;
}

.status-running {
  background: #eef6ff;
  color: #2563eb;
}

.status-skipped {
  background: #fff7e6;
  color: #b76e00;
}

.status-pending {
  background: #eef2f7;
  color: #64748b;
}

.summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}

.summary-meta span {
  max-width: none;
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(112px, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.stat-item {
  display: flex;
  min-height: 62px;
  min-width: 0;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #edf2f7;
  border-radius: 7px;
  background: #fbfdff;
  text-align: center;
}

.stat-item span {
  display: inline-flex;
  align-items: center;
  color: #64748b;
  font-size: 12px;
}

.stat-item strong {
  display: inline-flex;
  align-items: center;
  margin-top: 0;
  color: #111827;
  font-size: 20px;
  line-height: 26px;
}

.stat-item.success strong {
  color: #168a4a;
}

.stat-item.failed strong {
  color: #d92d20;
}

.stat-item.skipped strong {
  color: #b76e00;
}

.summary-chart {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.donut-chart {
  display: grid;
  width: 124px;
  height: 124px;
  place-items: center;
  border-radius: 50%;
}

.donut-hole {
  display: grid;
  width: 82px;
  height: 82px;
  place-items: center;
  border-radius: 50%;
  background: #fff;
  box-shadow: inset 0 0 0 1px #edf2f7;
}

.donut-hole strong {
  color: #111827;
  font-size: 22px;
  line-height: 24px;
}

.donut-hole span {
  color: #64748b;
  font-size: 12px;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px 10px;
  color: #64748b;
  font-size: 12px;
}

.legend-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 4px;
  border-radius: 999px;
}

.legend-dot.success {
  background: #16a34a;
}

.legend-dot.failed {
  background: #ef4444;
}

.legend-dot.skipped {
  background: #f59e0b;
}

@media (max-width: 1100px) {
  .report-summary {
    grid-template-columns: 1fr;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
