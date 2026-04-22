<script setup lang="ts">
import { computed, reactive, watch } from "vue";

type CronBuilderMode = "every_minutes" | "hourly" | "daily" | "weekly" | "monthly";

type CronPreset = {
  label: string;
  value: string;
};

const defaultPresets: CronPreset[] = [
  { label: "每 5 分钟", value: "*/5 * * * *" },
  { label: "每小时", value: "0 * * * *" },
  { label: "每天 9 点", value: "0 9 * * *" },
  { label: "工作日 9 点", value: "0 9 * * 1-5" },
];

const minuteOptions = Array.from({ length: 60 }, (_, value) => ({
  label: `${String(value).padStart(2, "0")} 分`,
  value,
}));

const hourOptions = Array.from({ length: 24 }, (_, value) => ({
  label: `${String(value).padStart(2, "0")} 点`,
  value,
}));

const weekDayOptions = [
  { label: "周日", value: 0 },
  { label: "周一", value: 1 },
  { label: "周二", value: 2 },
  { label: "周三", value: 3 },
  { label: "周四", value: 4 },
  { label: "周五", value: 5 },
  { label: "周六", value: 6 },
];

const monthDayOptions = Array.from({ length: 31 }, (_, index) => ({
  label: `${index + 1} 日`,
  value: index + 1,
}));

const props = withDefaults(
  defineProps<{
    modelValue: string;
    presets?: CronPreset[];
    showPresets?: boolean;
    showPreview?: boolean;
    previewLabel?: string;
    disabled?: boolean;
  }>(),
  {
    presets: undefined,
    showPresets: true,
    showPreview: true,
    previewLabel: "Cron",
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
  change: [value: string];
}>();

const cronBuilder = reactive({
  mode: "daily" as CronBuilderMode,
  everyMinutes: 5,
  minute: 0,
  hour: 9,
  weekDays: [1, 2, 3, 4, 5],
  monthDay: 1,
});

const activePresets = computed(() => (props.presets?.length ? props.presets : defaultPresets));
const previewValue = computed(() => (props.modelValue || buildCronExpression()).trim());

let syncingFromModel = false;

function clampNumber(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}

function parseCronNumber(value: string | undefined, min: number, max: number, fallback: number) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    return fallback;
  }
  return clampNumber(parsed, min, max);
}

function parseCronWeekDays(value: string | undefined) {
  if (!value || value === "*") {
    return [1, 2, 3, 4, 5];
  }
  const days = new Set<number>();
  for (const section of value.split(",")) {
    const [startText, endText] = section.split("-");
    const start = Number(startText);
    const end = endText === undefined ? start : Number(endText);
    if (!Number.isInteger(start) || !Number.isInteger(end)) {
      continue;
    }
    const from = Math.min(start, end);
    const to = Math.max(start, end);
    for (let day = from; day <= to; day += 1) {
      const normalized = day === 7 ? 0 : day;
      if (normalized >= 0 && normalized <= 6) {
        days.add(normalized);
      }
    }
  }
  return Array.from(days).sort((a, b) => a - b);
}

function formatCronWeekDays(value: number[]) {
  const days = Array.from(new Set(value.map((item) => (item === 7 ? 0 : item))))
    .filter((item) => item >= 0 && item <= 6)
    .sort((a, b) => a - b);
  if (days.length === 0) {
    return "1";
  }
  const sections: string[] = [];
  let start = days[0];
  let previous = days[0];
  for (let index = 1; index <= days.length; index += 1) {
    const current = days[index];
    if (current === previous + 1) {
      previous = current;
      continue;
    }
    sections.push(start === previous ? `${start}` : `${start}-${previous}`);
    start = current;
    previous = current;
  }
  return sections.join(",");
}

function buildCronExpression() {
  const minute = clampNumber(cronBuilder.minute, 0, 59);
  const hour = clampNumber(cronBuilder.hour, 0, 23);
  if (cronBuilder.mode === "every_minutes") {
    return `*/${clampNumber(cronBuilder.everyMinutes, 1, 59)} * * * *`;
  }
  if (cronBuilder.mode === "hourly") {
    return `${minute} * * * *`;
  }
  if (cronBuilder.mode === "weekly") {
    return `${minute} ${hour} * * ${formatCronWeekDays(cronBuilder.weekDays)}`;
  }
  if (cronBuilder.mode === "monthly") {
    return `${minute} ${hour} ${clampNumber(cronBuilder.monthDay, 1, 31)} * *`;
  }
  return `${minute} ${hour} * * *`;
}

function syncCronBuilderFromExpression(expression: string) {
  const [minute, hour, day, month, week] = expression.trim().split(/\s+/);
  if (!minute || !hour || !day || !month || !week) {
    cronBuilder.mode = "daily";
    cronBuilder.minute = 0;
    cronBuilder.hour = 9;
    return;
  }

  if (minute.startsWith("*/") && hour === "*" && day === "*" && month === "*" && week === "*") {
    cronBuilder.mode = "every_minutes";
    cronBuilder.everyMinutes = parseCronNumber(minute.slice(2), 1, 59, 5);
    return;
  }

  if (hour === "*" && day === "*" && month === "*" && week === "*") {
    cronBuilder.mode = "hourly";
    cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
    return;
  }

  if (day === "*" && month === "*" && week !== "*") {
    cronBuilder.mode = "weekly";
    cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
    cronBuilder.hour = parseCronNumber(hour, 0, 23, 9);
    cronBuilder.weekDays = parseCronWeekDays(week);
    return;
  }

  if (day !== "*" && month === "*" && week === "*") {
    cronBuilder.mode = "monthly";
    cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
    cronBuilder.hour = parseCronNumber(hour, 0, 23, 9);
    cronBuilder.monthDay = parseCronNumber(day, 1, 31, 1);
    return;
  }

  cronBuilder.mode = "daily";
  cronBuilder.minute = parseCronNumber(minute, 0, 59, 0);
  cronBuilder.hour = parseCronNumber(hour, 0, 23, 9);
}

function emitCronExpression(expression: string) {
  if (expression !== props.modelValue) {
    emit("update:modelValue", expression);
  }
  emit("change", expression);
}

function applyCronPreset(expression: string) {
  syncingFromModel = true;
  syncCronBuilderFromExpression(expression);
  syncingFromModel = false;
  emitCronExpression(expression);
}

watch(
  () => props.modelValue,
  (value) => {
    syncingFromModel = true;
    syncCronBuilderFromExpression(value || "");
    syncingFromModel = false;
  },
  { immediate: true, flush: "sync" },
);

watch(
  cronBuilder,
  () => {
    if (syncingFromModel) {
      return;
    }
    emitCronExpression(buildCronExpression());
  },
  { deep: true, flush: "sync" },
);
</script>

<template>
  <div class="cron-expression-config">
    <div v-if="showPresets" class="cron-preset-row">
      <el-button
        v-for="item in activePresets"
        :key="item.value"
        size="small"
        :type="previewValue === item.value ? 'primary' : 'default'"
        :disabled="disabled"
        plain
        @click="applyCronPreset(item.value)"
      >
        {{ item.label }}
      </el-button>
    </div>

    <div class="cron-builder">
      <el-radio-group v-model="cronBuilder.mode" size="small" class="cron-mode-group" :disabled="disabled">
        <el-radio-button label="every_minutes">每 N 分钟</el-radio-button>
        <el-radio-button label="hourly">每小时</el-radio-button>
        <el-radio-button label="daily">每天</el-radio-button>
        <el-radio-button label="weekly">每周</el-radio-button>
        <el-radio-button label="monthly">每月</el-radio-button>
      </el-radio-group>

      <div v-if="cronBuilder.mode === 'every_minutes'" class="cron-row">
        <span>每</span>
        <el-input-number
          v-model="cronBuilder.everyMinutes"
          :min="1"
          :max="59"
          size="small"
          controls-position="right"
          :disabled="disabled"
        />
        <span>分钟执行</span>
      </div>

      <div v-else-if="cronBuilder.mode === 'hourly'" class="cron-row">
        <span>每小时的</span>
        <el-select
          v-model="cronBuilder.minute"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <span>执行</span>
      </div>

      <div v-else-if="cronBuilder.mode === 'daily'" class="cron-row">
        <span>每天</span>
        <el-select
          v-model="cronBuilder.hour"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in hourOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="cronBuilder.minute"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <span>执行</span>
      </div>

      <div v-else-if="cronBuilder.mode === 'weekly'" class="cron-row">
        <span>每周</span>
        <el-select
          v-model="cronBuilder.weekDays"
          class="cron-select cron-select--wide"
          size="small"
          multiple
          collapse-tags
          collapse-tags-tooltip
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in weekDayOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="cronBuilder.hour"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in hourOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="cronBuilder.minute"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <span>执行</span>
      </div>

      <div v-else class="cron-row">
        <span>每月</span>
        <el-select
          v-model="cronBuilder.monthDay"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in monthDayOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="cronBuilder.hour"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in hourOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="cronBuilder.minute"
          class="cron-select"
          size="small"
          popper-class="compact-select-popper"
          :disabled="disabled"
        >
          <el-option v-for="item in minuteOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <span>执行</span>
      </div>

      <div v-if="showPreview" class="cron-preview">
        <span>{{ previewLabel }}</span>
        <code>{{ previewValue }}</code>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cron-expression-config {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  min-width: 0;
}

.cron-preset-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.cron-builder {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-width: 0;
  padding: 12px;
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #fbfdff;
}

.cron-mode-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.cron-builder :deep(.el-radio-button__inner) {
  min-width: 74px;
  padding: 7px 12px;
  font-size: 12px;
}

.cron-row {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  min-width: 0;
  color: #4e5969;
  font-size: 12px;
  overflow-x: auto;
}

.cron-row > span {
  flex: 0 0 auto;
  white-space: nowrap;
}

.cron-row :deep(.el-input-number) {
  flex: 0 0 120px;
  width: 120px !important;
  max-width: 120px;
}

.cron-row :deep(.el-input-number__decrease),
.cron-row :deep(.el-input-number__increase) {
  font-size: 12px;
}

.cron-select {
  flex: 0 0 104px;
  width: 104px !important;
}

.cron-select--wide {
  flex-basis: 210px;
  width: 210px !important;
}

.cron-preview {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  max-width: 100%;
  padding: 5px 10px;
  border-radius: 6px;
  background: #eef4ff;
  color: #64748b;
  font-size: 12px;
}

.cron-preview code {
  color: #1d4ed8;
  font-family: Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  font-weight: 700;
}
</style>
