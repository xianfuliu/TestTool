<script setup lang="ts">
import { computed, ref } from "vue";

import JsonTreeViewer from "@/shared/components/JsonTreeViewer.vue";

type LogRecord = Record<string, unknown>;

const props = defineProps<{
  log?: LogRecord | null;
  fallbackLines?: string[];
}>();

const expandedStepKeys = ref<string[]>([]);

const hasStructuredLog = computed(() => Array.isArray((props.log as LogRecord | null)?.steps));
const steps = computed<LogRecord[]>(() => ((props.log?.steps as LogRecord[] | undefined) ?? []));
const globalSetup = computed<LogRecord>(() => (props.log?.global_setup as LogRecord | undefined) ?? {});
const fallbackText = computed(() => (props.fallbackLines ?? []).join("\n") || "暂无执行日志");

function stepKey(step: LogRecord, index: number) {
  return String(step.step_id ?? `${step.step_order ?? index}-${step.step_name ?? index}`);
}

function isExpanded(step: LogRecord, index: number) {
  return expandedStepKeys.value.includes(stepKey(step, index));
}

function toggleStep(step: LogRecord, index: number) {
  const key = stepKey(step, index);
  expandedStepKeys.value = expandedStepKeys.value.includes(key)
    ? expandedStepKeys.value.filter((item) => item !== key)
    : [...expandedStepKeys.value, key];
}

function statusText(status: unknown) {
  if (status === "success") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  if (status === "skipped") {
    return "跳过";
  }
  return String(status || "待执行");
}

function statusClass(status: unknown) {
  return {
    success: status === "success",
    failed: status === "failed",
    skipped: status === "skipped",
  };
}

function asArray(value: unknown): LogRecord[] {
  return Array.isArray(value) ? (value as LogRecord[]) : [];
}

function asLines(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function getRecordValue(value: unknown, key: string) {
  return value && typeof value === "object" ? (value as LogRecord)[key] : undefined;
}

function hasValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return false;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === "object") {
    return Object.keys(value as LogRecord).length > 0;
  }
  return true;
}
</script>

<template>
  <div class="execution-log-viewer">
    <template v-if="hasStructuredLog">
      <section v-if="!steps.length && (hasValue(globalSetup.logs) || hasValue(globalSetup.variable_changes))" class="case-log-section">
        <div class="case-log-title">全局配置</div>
        <ul v-if="asLines(globalSetup.logs).length" class="log-lines">
          <li v-for="(line, index) in asLines(globalSetup.logs)" :key="`global-log-${index}`">{{ line }}</li>
        </ul>
        <div v-if="hasValue(globalSetup.variable_changes)" class="json-block">
          <div class="json-block-title">变量池变更</div>
          <JsonTreeViewer :value="globalSetup.variable_changes" />
        </div>
        <div v-if="hasValue(globalSetup.login_request)" class="json-block">
          <div class="json-block-title">登录态获取</div>
          <JsonTreeViewer :value="globalSetup.login_request" />
        </div>
      </section>

      <div class="step-log-list">
        <article v-for="(step, index) in steps" :key="stepKey(step, index)" class="step-log-item">
          <button class="step-log-row" type="button" @click="toggleStep(step, index)">
            <span class="step-toggle" :class="{ expanded: isExpanded(step, index) }">›</span>
            <span class="step-name">{{ step.step_name || `步骤 ${step.step_order || index + 1}` }}</span>
            <span class="step-order">#{{ step.step_order || index + 1 }}</span>
            <span class="step-status" :class="statusClass(step.status)">{{ statusText(step.status) }}</span>
            <span class="step-summary">{{ step.summary || step.error_message || "点击查看执行详情" }}</span>
          </button>

          <div v-if="isExpanded(step, index)" class="step-log-detail">
            <section v-if="asLines(step.logs).length" class="detail-section">
              <div class="detail-title">处理日志（按执行顺序）</div>
              <ul class="log-lines">
                <li v-for="(line, lineIndex) in asLines(step.logs)" :key="`step-log-${lineIndex}`">{{ line }}</li>
              </ul>
            </section>

            <section v-if="hasValue(step.global_setup)" class="detail-section">
              <div class="detail-title">全局请求头-登录态获取</div>
              <ul v-if="asLines(getRecordValue(step.global_setup, 'logs')).length" class="log-lines">
                <li v-for="(line, lineIndex) in asLines(getRecordValue(step.global_setup, 'logs'))" :key="`global-line-${lineIndex}`">{{ line }}</li>
              </ul>
              <div v-if="hasValue(getRecordValue(step.global_setup, 'login_request'))" class="json-block">
                <div class="json-block-title">登录请求与提取结果</div>
                <JsonTreeViewer :value="getRecordValue(step.global_setup, 'login_request')" />
              </div>
              <div v-if="hasValue(getRecordValue(step.global_setup, 'variable_pool'))" class="json-block">
                <div class="json-block-title">登录后变量池（包含全局变量）</div>
                <JsonTreeViewer :value="getRecordValue(step.global_setup, 'variable_pool')" />
              </div>
            </section>

            <section v-if="asArray(step.variable_changes).length" class="detail-section">
              <div class="detail-title">变量池变更</div>
              <div v-for="(item, itemIndex) in asArray(step.variable_changes)" :key="`var-${itemIndex}`" class="json-block">
                <div class="json-block-title">{{ item.stage || `变更 ${itemIndex + 1}` }}</div>
                <JsonTreeViewer :value="item.changes" />
                <div v-if="hasValue(item.variable_pool)" class="nested-json-block">
                  <div class="json-block-title">当前变量池（包含全局变量）</div>
                  <JsonTreeViewer :value="item.variable_pool" />
                </div>
              </div>
            </section>

            <section v-if="asArray(step.pre_processing).length" class="detail-section">
              <div class="detail-title">前置工具</div>
              <div v-for="(tool, toolIndex) in asArray(step.pre_processing)" :key="`pre-${toolIndex}`" class="tool-log-card">
                <div class="tool-log-title">
                  <span>{{ tool.name || tool.tool_type || `工具 ${toolIndex + 1}` }}</span>
                  <span class="step-status" :class="statusClass(tool.status)">{{ statusText(tool.status) }}</span>
                </div>
                <ul v-if="asLines(tool.logs).length" class="log-lines compact">
                  <li v-for="(line, lineIndex) in asLines(tool.logs)" :key="`pre-line-${lineIndex}`">{{ line }}</li>
                </ul>
                <div v-if="hasValue(tool.request)" class="json-block">
                  <div class="json-block-title">请求信息</div>
                  <JsonTreeViewer :value="tool.request" />
                </div>
                <div v-if="hasValue(tool.response)" class="json-block">
                  <div class="json-block-title">响应信息</div>
                  <JsonTreeViewer :value="tool.response" />
                </div>
                <div v-if="hasValue(tool.extractions)" class="json-block">
                  <div class="json-block-title">参数提取</div>
                  <JsonTreeViewer :value="tool.extractions" />
                </div>
              </div>
            </section>

            <section v-if="hasValue(step.main_request)" class="detail-section">
              <div class="detail-title">步骤接口请求</div>
              <div v-if="hasValue(getRecordValue(step.main_request, 'encryption'))" class="json-block">
                <div class="json-block-title">全局加解密配置</div>
                <JsonTreeViewer :value="getRecordValue(step.main_request, 'encryption')" />
              </div>
              <div v-if="hasValue(getRecordValue(step.main_request, 'global_headers'))" class="json-block">
                <div class="json-block-title">全局请求头变量替换</div>
                <JsonTreeViewer :value="getRecordValue(step.main_request, 'global_headers')" />
              </div>
              <div class="json-grid">
                <div class="json-block">
                  <div class="json-block-title">变量替换前</div>
                  <JsonTreeViewer :value="getRecordValue(step.main_request, 'before_replace')" />
                </div>
                <div class="json-block">
                  <div class="json-block-title">变量替换后</div>
                  <JsonTreeViewer :value="getRecordValue(step.main_request, 'after_replace')" />
                </div>
              </div>
              <div class="json-block">
                <div class="json-block-title">响应信息</div>
                <JsonTreeViewer :value="getRecordValue(step.main_request, 'response')" />
              </div>
            </section>

            <section v-if="asArray(step.assertions).length" class="detail-section">
              <div class="detail-title">断言结果</div>
              <div v-for="(tool, toolIndex) in asArray(step.assertions)" :key="`assert-${toolIndex}`" class="tool-log-card">
                <div class="tool-log-title">
                  <span>{{ tool.name || "断言" }}</span>
                  <span class="step-status" :class="statusClass(tool.status)">{{ statusText(tool.status) }}</span>
                </div>
                <div v-if="hasValue(tool.assertions)" class="json-block">
                  <div class="json-block-title">断言字段与结果</div>
                  <JsonTreeViewer :value="tool.assertions" />
                </div>
              </div>
            </section>

            <section v-if="asArray(step.post_processing).length" class="detail-section">
              <div class="detail-title">后置工具</div>
              <div v-for="(tool, toolIndex) in asArray(step.post_processing)" :key="`post-${toolIndex}`" class="tool-log-card">
                <div class="tool-log-title">
                  <span>{{ tool.name || tool.tool_type || `工具 ${toolIndex + 1}` }}</span>
                  <span class="step-status" :class="statusClass(tool.status)">{{ statusText(tool.status) }}</span>
                </div>
                <ul v-if="asLines(tool.logs).length" class="log-lines compact">
                  <li v-for="(line, lineIndex) in asLines(tool.logs)" :key="`post-line-${lineIndex}`">{{ line }}</li>
                </ul>
                <div v-if="hasValue(tool.extractions)" class="json-block">
                  <div class="json-block-title">参数提取</div>
                  <JsonTreeViewer :value="tool.extractions" />
                </div>
                <div v-if="hasValue(tool.variable_changes)" class="json-block">
                  <div class="json-block-title">提取后变量池变更</div>
                  <JsonTreeViewer :value="tool.variable_changes" />
                </div>
                <div v-if="hasValue(tool.response)" class="json-block">
                  <div class="json-block-title">响应信息</div>
                  <JsonTreeViewer :value="tool.response" />
                </div>
              </div>
            </section>
          </div>
        </article>
      </div>

      <section class="case-log-section output-section">
        <div class="case-log-title">用例输出变量</div>
        <JsonTreeViewer :value="props.log?.case_outputs || {}" />
      </section>
    </template>

    <pre v-else class="legacy-log">{{ fallbackText }}</pre>
  </div>
</template>

<style scoped>
.execution-log-viewer {
  max-height: 68vh;
  overflow: auto;
  padding: 2px;
  color: #1f2f46;
}

.case-log-section,
.step-log-item {
  border: 1px solid #e4ebf5;
  border-radius: 10px;
  background: #fff;
}

.case-log-section {
  padding: 12px;
  margin-bottom: 10px;
}

.case-log-title,
.detail-title {
  font-weight: 700;
  color: #1f2f46;
}

.case-log-title {
  margin-bottom: 8px;
}

.step-log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-log-row {
  width: 100%;
  border: none;
  background: #f8fbff;
  min-height: 42px;
  display: grid;
  grid-template-columns: 20px minmax(150px, 1fr) 52px 58px minmax(180px, 1.5fr);
  gap: 8px;
  align-items: center;
  padding: 9px 12px;
  text-align: left;
  cursor: pointer;
}

.step-toggle {
  color: #7b8da8;
  font-size: 18px;
  transform: rotate(0deg);
  transition: transform 0.16s ease;
}

.step-toggle.expanded {
  transform: rotate(90deg);
}

.step-name {
  font-weight: 700;
  color: #18263b;
}

.step-order,
.step-summary {
  color: #66758c;
  font-size: 13px;
}

.step-status {
  justify-self: start;
  border-radius: 999px;
  padding: 2px 9px;
  font-size: 12px;
  color: #607086;
  background: #eef3f8;
}

.step-status.success {
  color: #1d8b53;
  background: #e8f8ef;
}

.step-status.failed {
  color: #c63b3b;
  background: #fff0f0;
}

.step-status.skipped {
  color: #9a6a00;
  background: #fff7e6;
}

.step-log-detail {
  padding: 12px;
  border-top: 1px solid #e8eef7;
}

.detail-section + .detail-section {
  margin-top: 12px;
}

.detail-title {
  margin-bottom: 8px;
}

.log-lines {
  margin: 0;
  padding-left: 18px;
  color: #41516a;
  line-height: 1.75;
  font-size: 13px;
}

.log-lines.compact {
  line-height: 1.6;
}

.json-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
}

.json-block {
  margin-top: 8px;
  border: 1px solid #e7edf6;
  border-radius: 8px;
  background: #fbfdff;
  padding: 8px 10px;
}

.nested-json-block {
  margin-top: 8px;
  border-top: 1px dashed #d9e3f2;
  padding-top: 8px;
}

.json-block-title {
  margin-bottom: 6px;
  color: #607086;
  font-size: 12px;
  font-weight: 700;
}

.tool-log-card {
  border: 1px solid #e7edf6;
  border-radius: 8px;
  padding: 10px;
  background: #fcfdff;
}

.tool-log-card + .tool-log-card {
  margin-top: 8px;
}

.tool-log-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 700;
}

.output-section {
  margin-top: 10px;
}

.legacy-log {
  margin: 0;
  min-height: 280px;
  padding: 12px;
  border: 1px solid #e4ebf5;
  border-radius: 10px;
  background: #0f172a;
  color: #d7e1f1;
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .step-log-row,
  .json-grid {
    grid-template-columns: 1fr;
  }
}
</style>
