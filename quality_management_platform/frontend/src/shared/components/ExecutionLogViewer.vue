<script setup lang="ts">
import { computed, ref, watch } from "vue";

type LogRecord = Record<string, unknown>;

type NormalizedLogLine = {
  time: string;
  level: string;
  scope: string;
  subScope: string;
  icon: string;
  message: string;
};

type NormalizedLogGroup = {
  key: string;
  time: string;
  level: string;
  scope: string;
  icon: string;
  title: string;
  summary: string;
  status: string;
  lines: NormalizedLogLine[];
};

const props = defineProps<{
  log?: LogRecord | null;
  fallbackLines?: string[];
}>();

const INTERNAL_RUNTIME_VARIABLE_KEYS = new Set(["current_step_name", "current_step_order"]);
const expandedGroupKeys = ref<string[]>([]);

const logGroups = computed<NormalizedLogGroup[]>(() => {
  const log = props.log;
  const steps = asArray(log?.steps);
  if (log && steps.length) {
    return buildStructuredGroups(log, steps);
  }

  const structuredLines = refineLogTimes(asArray(log?.lines).map((line) => normalizeLine(asRecord(line))));
  if (structuredLines.length) {
    return [
      createGroup({
        key: "all",
        title: "执行日志",
        scope: "全局",
        status: text(log?.status, ""),
        summary: text(log?.message, "全部日志"),
        lines: structuredLines,
      }),
    ];
  }

  const fallback = refineLogTimes(
    (props.fallbackLines ?? [])
      .filter((line) => line !== "")
      .map((line) =>
        normalizeLine({
          time: formatDateTime(),
          level: inferLevel(line),
          scope: "全局",
          icon: "info",
          message: line,
        }),
      ),
  );
  return fallback.length
    ? [
        createGroup({
          key: "fallback",
          title: "执行日志",
          scope: "全局",
          summary: "基础执行结果",
          lines: fallback,
        }),
      ]
    : [];
});

watch(
  logGroups,
  (groups) => {
    const keys = new Set(groups.map((group) => group.key));
    expandedGroupKeys.value = expandedGroupKeys.value.filter((key) => keys.has(key));
  },
  { immediate: true },
);

function isExpanded(group: NormalizedLogGroup) {
  return expandedGroupKeys.value.includes(group.key);
}

function toggleGroup(group: NormalizedLogGroup) {
  expandedGroupKeys.value = isExpanded(group)
    ? expandedGroupKeys.value.filter((key) => key !== group.key)
    : [...expandedGroupKeys.value, group.key];
}

function formatCopyLine(line: NormalizedLogLine) {
  const subScope = line.subScope ? ` [${line.subScope}]` : "";
  return `[${line.time}] [${line.level}] [${line.scope}]${subScope} ${line.message}`;
}

function formatCopyGroup(group: NormalizedLogGroup) {
  return `${group.title} ${group.lines.length} 条日志 ${statusText(group.status)}`;
}

function handleCopy(event: ClipboardEvent) {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
    return;
  }
  const range = selection.getRangeAt(0);
  const root = event.currentTarget as HTMLElement;
  const selectedLines = Array.from(root.querySelectorAll<HTMLElement>("[data-copy-text]"))
    .filter((element) => {
      try {
        return range.intersectsNode(element);
      } catch {
        return false;
      }
    })
    .map((element) => element.dataset.copyText || "")
    .filter(Boolean);

  if (!selectedLines.length) {
    return;
  }
  event.preventDefault();
  event.clipboardData?.setData("text/plain", selectedLines.join("\n"));
}

function selectWholeLogLineOnTripleClick(event: MouseEvent) {
  if (event.detail !== 3) {
    return;
  }
  const row = (event.currentTarget as HTMLElement | null);
  if (!row) {
    return;
  }
  const selection = window.getSelection();
  if (!selection) {
    return;
  }
  const range = document.createRange();
  range.selectNodeContents(row);
  selection.removeAllRanges();
  selection.addRange(range);
  event.preventDefault();
}

function asRecord(value: unknown): LogRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as LogRecord) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
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

function text(value: unknown, fallback = "") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function parseDateTime(value?: unknown) {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  const raw = text(value);
  if (!raw) {
    return null;
  }
  const date = new Date(raw.replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDateTime(value?: unknown): string {
  const raw = text(value);
  const date = parseDateTime(value) ?? new Date();
  if (Number.isNaN(date.getTime())) {
    return (raw.length > 19 ? raw.slice(0, 23) : raw.slice(0, 19)) || formatDateTime();
  }
  const pad = (item: number) => String(item).padStart(2, "0");
  const milliseconds = String(date.getMilliseconds()).padStart(3, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${milliseconds}`;
}

function refineLogTimes(lines: NormalizedLogLine[]) {
  let previous: Date | null = null;
  return lines.map((line) => {
    let current = parseDateTime(line.time) ?? new Date();
    if (previous && current.getTime() <= previous.getTime()) {
      current = new Date(previous.getTime() + 1);
    }
    previous = current;
    return { ...line, time: formatDateTime(current) };
  });
}

function compactValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return "";
    }
    try {
      return JSON.stringify(JSON.parse(trimmed));
    } catch {
      return trimmed.replace(/\s+/g, " ");
    }
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function inferLevel(value: unknown) {
  const lower = text(value).toLowerCase();
  if (/(error|失败|异常|错误|超时)/i.test(lower)) {
    return "ERROR";
  }
  if (/(warn|warning|跳过|未匹配)/i.test(lower)) {
    return "WARN";
  }
  if (/debug/i.test(lower)) {
    return "DEBUG";
  }
  return "INFO";
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
  return text(status, "待执行");
}

function statusLevel(status: unknown) {
  if (status === "failed") {
    return "ERROR";
  }
  if (status === "skipped") {
    return "WARN";
  }
  return "INFO";
}

function statusIcon(status: unknown) {
  if (status === "failed") {
    return "error";
  }
  if (status === "skipped") {
    return "warning";
  }
  return "success";
}

function normalizeLine(line: LogRecord): NormalizedLogLine {
  const level = text(line.level, "INFO").toUpperCase();
  return {
    time: formatDateTime(line.time ?? line.timestamp ?? line.created_at),
    level,
    scope: text(line.scope ?? line.owner ?? line.category, "全局"),
    subScope: text(line.sub_scope ?? line.subScope ?? line.subcategory, ""),
    icon: text(line.icon, level === "ERROR" ? "error" : level === "WARN" ? "warning" : "info"),
    message: text(line.message ?? line.description ?? line.content, ""),
  };
}

function pushLine(
  target: NormalizedLogLine[],
  message: unknown,
  options: Partial<Omit<NormalizedLogLine, "message">> = {},
) {
  if (!hasValue(message)) {
    return;
  }
  target.push(
    normalizeLine({
      time: options.time || formatDateTime(),
      level: options.level || inferLevel(message),
      scope: options.scope || "全局",
      sub_scope: options.subScope || "",
      icon: options.icon || "info",
      message,
    }),
  );
}

function pushRawLines(
  target: NormalizedLogLine[],
  lines: unknown,
  options: Partial<Omit<NormalizedLogLine, "message">>,
) {
  asArray(lines).forEach((line) => pushLine(target, line, { ...options, level: inferLevel(line) }));
}

function pushExchangeLines(
  target: NormalizedLogLine[],
  requestData: unknown,
  responseData: unknown,
  options: Partial<Omit<NormalizedLogLine, "message">>,
) {
  const request = asRecord(requestData);
  const response = asRecord(responseData);
  const method = text(request.method).toUpperCase();
  const url = text(request.url);
  if (method || url) {
    pushLine(target, `请求: ${method || "-"} ${url || "-"}`, { ...options, level: "INFO", icon: "request" });
  }
  if (hasValue(request.headers)) {
    pushLine(target, `请求头: ${compactValue(request.headers)}`, { ...options, level: "INFO", icon: "header" });
  }
  if (hasValue(request.params)) {
    pushLine(target, `请求参数: ${compactValue(request.params)}`, { ...options, level: "INFO", icon: "request" });
  }
  if (hasValue(request.body)) {
    pushLine(target, `请求体: ${compactValue(request.body)}`, { ...options, level: "INFO", icon: "request" });
  }
  if (hasValue(response.status_code)) {
    const statusCode = Number(response.status_code);
    pushLine(target, `响应状态: ${response.status_code}，耗时 ${text(response.duration_ms, "0")}ms`, {
      ...options,
      level: statusCode >= 400 ? "ERROR" : "INFO",
      icon: "response",
    });
  }
  const responseBody = hasValue(response.decrypted_body)
    ? response.decrypted_body
    : hasValue(response.body)
      ? response.body
      : response.raw_body;
  if (hasValue(responseBody)) {
    pushLine(target, `响应体: ${compactValue(responseBody)}`, { ...options, level: "INFO", icon: "response" });
  }
}

function pushVariableChanges(
  target: NormalizedLogLine[],
  changes: unknown,
  options: Partial<Omit<NormalizedLogLine, "message">> = {},
) {
  const changeMap = asRecord(changes);
  Object.entries(asRecord(changeMap.added)).forEach(([key, value]) =>
    INTERNAL_RUNTIME_VARIABLE_KEYS.has(key)
      ? undefined
      : pushLine(target, `新增变量 ${key} = ${compactValue(value)}`, { ...options, scope: "变量池", level: "INFO", icon: "variable" }),
  );
  Object.entries(asRecord(changeMap.changed)).forEach(([key, value]) => {
    if (INTERNAL_RUNTIME_VARIABLE_KEYS.has(key)) {
      return;
    }
    const row = asRecord(value);
    pushLine(target, `更新变量 ${key}: ${compactValue(row.before)} -> ${compactValue(row.after)}`, {
      ...options,
      scope: "变量池",
      level: "INFO",
      icon: "variable",
    });
  });
  Object.entries(asRecord(changeMap.removed)).forEach(([key, value]) =>
    INTERNAL_RUNTIME_VARIABLE_KEYS.has(key)
      ? undefined
      : pushLine(target, `移除变量 ${key}，原值 ${compactValue(value)}`, { ...options, scope: "变量池", level: "WARN", icon: "variable" }),
  );
}

function pushToolLines(
  target: NormalizedLogLine[],
  toolItem: unknown,
  scope: string,
  time: string,
) {
  const tool = asRecord(toolItem);
  const toolName = text(tool.name ?? tool.tool_type, "工具");
  const subScope = scope === "断言" ? "" : toolName;
  const level = tool.status === "failed" ? "ERROR" : "INFO";
  pushLine(target, scope === "断言" ? `执行断言: ${toolName}` : `开始执行${scope}工具: ${toolName}`, {
    time,
    scope,
    subScope,
    level,
    icon: scope === "断言" ? "assert" : "tool",
  });
  pushRawLines(target, tool.logs, { time, scope, subScope, icon: scope === "断言" ? "assert" : "tool" });
  pushExchangeLines(target, tool.request, tool.response, { time, scope, subScope });
  if (hasValue(tool.extractions)) {
    pushLine(target, `提取结果: ${compactValue(tool.extractions)}`, { time, scope, subScope, level: "INFO", icon: "variable" });
  }
  if (hasValue(tool.assertions)) {
    pushLine(target, `断言结果: ${compactValue(tool.assertions)}`, { time, scope, subScope, level, icon: "assert" });
  }
  pushVariableChanges(target, tool.variable_changes, { time, scope: "变量池", icon: "variable" });
  if (hasValue(tool.error_message)) {
    pushLine(target, tool.error_message, { time, scope, subScope, level: "ERROR", icon: "error" });
  }
}

function createGroup(input: {
  key: string;
  title: string;
  scope: string;
  lines: NormalizedLogLine[];
  status?: string;
  summary?: string;
  level?: string;
  icon?: string;
}): NormalizedLogGroup {
  const lines = refineLogTimes(input.lines);
  const status = input.status || "";
  return {
    key: input.key,
    time: lines[0]?.time || formatDateTime(),
    level: input.level || statusLevel(status),
    scope: input.scope,
    icon: input.icon || statusIcon(status),
    title: input.title,
    summary: input.summary || statusText(status),
    status,
    lines,
  };
}

function buildStructuredGroups(log: LogRecord, steps: unknown[]) {
  const groups: NormalizedLogGroup[] = [];
  const startedAt = formatDateTime(log.started_at ?? log.start_time ?? formatDateTime());
  const endedAt = formatDateTime(log.ended_at ?? log.end_time ?? startedAt);
  const globalLines = buildGlobalLines(log, startedAt, endedAt);
  let globalLinesAttached = false;

  steps.forEach((stepItem, index) => {
    const step = asRecord(stepItem);
    const stepOrder = text(step.step_order, String(index + 1));
    const stepName = text(step.step_name, "未命名步骤");
    const stepStatus = text(step.status, "");
    const stepSummary = text(step.summary ?? step.error_message, statusText(stepStatus));
    if (stepStatus === "skipped" && stepSummary.includes("前序步骤失败")) {
      return;
    }
    const stepLines = buildStepLines(step, startedAt);
    const lines = globalLinesAttached ? stepLines : [...globalLines, ...stepLines];
    globalLinesAttached = true;
    groups.push(
      createGroup({
        key: `step-${text(step.step_id ?? step.step_order, String(index))}`,
        title: `步骤 ${stepOrder}: ${stepName}`,
        scope: "步骤",
        status: stepStatus,
        summary: stepSummary,
        lines,
        level: statusLevel(stepStatus),
        icon: statusIcon(stepStatus),
      }),
    );
  });

  return groups;
}

function buildGlobalLines(log: LogRecord, startedAt: string, endedAt: string) {
  const target: NormalizedLogLine[] = [];
  pushLine(target, `开始执行用例: ${text(log.case_name, "未命名用例")}`, {
    time: startedAt,
    scope: "全局",
    level: "INFO",
    icon: "start",
  });

  const globalSetup = asRecord(log.global_setup);
  const context = asRecord(globalSetup.context);
  const encryption = asRecord(context.encryption);
  if (hasValue(encryption)) {
    pushLine(
      target,
      `加解密配置: ${encryption.enabled ? "启用" : "未启用"}，加密URL=${text(encryption.encrypt_url, "-")}，解密URL=${text(encryption.decrypt_url, "-")}`,
      { time: startedAt, scope: "全局", subScope: "加解密", level: "INFO", icon: encryption.enabled ? "lock" : "unlock" },
    );
  }
  const headerConfig = asRecord(context.header_config);
  if (headerConfig.enabled || hasValue(headerConfig.after_replace)) {
    pushLine(target, `全局请求头: ${compactValue(headerConfig.after_replace || headerConfig.before_replace)}`, {
      time: startedAt,
      scope: "全局",
      subScope: "全局请求头",
      level: "INFO",
      icon: "header",
    });
  }

  const loginRequest = asRecord(globalSetup.login_request);
  if (hasValue(loginRequest)) {
    pushLine(target, "开始获取登录态", {
      time: startedAt,
      scope: "全局",
      subScope: "登录态获取",
      level: "INFO",
      icon: "start",
    });
    pushExchangeLines(target, loginRequest.request, loginRequest, {
      time: startedAt,
      scope: "全局",
      subScope: "登录态获取",
    });
    if (hasValue(loginRequest.extracted_variables)) {
      pushLine(target, `登录态变量: ${compactValue(loginRequest.extracted_variables)}`, {
        time: startedAt,
        scope: "全局",
        subScope: "登录态获取",
        level: "INFO",
        icon: "variable",
      });
    }
  }

  pushRawLines(target, globalSetup.logs, {
    time: startedAt,
    scope: "全局",
    subScope: hasValue(loginRequest) ? "登录态获取" : "",
    icon: "info",
  });
  pushVariableChanges(target, globalSetup.variable_changes, { time: startedAt, scope: "变量池", icon: "variable" });
  if (hasValue(globalSetup.error)) {
    pushLine(target, `全局配置执行失败: ${globalSetup.error}`, {
      time: endedAt,
      scope: "全局",
      level: "ERROR",
      icon: "error",
    });
  }
  if (hasValue(log.case_outputs)) {
    pushLine(target, `用例出参: ${compactValue(log.case_outputs)}`, {
      time: endedAt,
      scope: "全局",
      subScope: "用例出参",
      level: "INFO",
      icon: "output",
    });
  }
  pushLine(target, text(log.message, "执行完成"), {
    time: endedAt,
    scope: "全局",
    level: log.status === "failed" ? "ERROR" : "INFO",
    icon: "finish",
  });
  return target;
}

function buildStepLines(step: LogRecord, defaultStartedAt: string) {
  const target: NormalizedLogLine[] = [];
  const stepTime = formatDateTime(step.started_at ?? defaultStartedAt);
  const endedAt = formatDateTime(step.ended_at ?? stepTime);
  const stepOrder = text(step.step_order, "-");
  const stepStatus = text(step.status, "");
  pushLine(target, `开始执行步骤 ${stepOrder}: ${text(step.step_name, "未命名步骤")}`, {
    time: stepTime,
    scope: "步骤",
    level: "INFO",
    icon: "start",
  });

  asArray(step.variable_changes).forEach((item) => {
    const detail = asRecord(item);
    if (!text(detail.stage).startsWith("步骤变量初始化")) {
      return;
    }
    pushVariableChanges(target, detail.changes, { time: stepTime, scope: "变量池", icon: "variable" });
  });

  asArray(step.pre_processing).forEach((tool) => pushToolLines(target, tool, "前置", stepTime));

  const mainRequest = asRecord(step.main_request);
  if (hasValue(mainRequest)) {
    const encryption = asRecord(mainRequest.encryption);
    if (hasValue(encryption)) {
      pushLine(target, `步骤加解密: ${encryption.enabled ? "启用" : "未启用"}`, {
        time: stepTime,
        scope: "全局",
        subScope: "加解密",
        level: "INFO",
        icon: encryption.enabled ? "lock" : "unlock",
      });
    }
    const globalHeaders = asRecord(mainRequest.global_headers);
    if (globalHeaders.enabled || hasValue(globalHeaders.after_replace)) {
      pushLine(target, `步骤全局请求头: ${compactValue(globalHeaders.after_replace || globalHeaders.before_replace)}`, {
        time: stepTime,
        scope: "全局",
        subScope: "全局请求头",
        level: "INFO",
        icon: "header",
      });
    }
    pushExchangeLines(target, mainRequest.after_replace, mainRequest.response, {
      time: stepTime,
      scope: "步骤",
    });
  }

  asArray(step.assertions).forEach((tool) => pushToolLines(target, tool, "断言", stepTime));
  asArray(step.post_processing).forEach((tool) => pushToolLines(target, tool, "后置", stepTime));

  pushLine(target, `步骤 ${stepOrder}执行${stepStatus === "failed" ? "失败" : stepStatus === "skipped" ? "跳过" : "成功"}: ${text(step.summary)}`, {
    time: endedAt,
    scope: "步骤",
    level: statusLevel(stepStatus),
    icon: statusIcon(stepStatus),
  });
  return target;
}
</script>

<template>
  <div class="execution-log-viewer" @copy="handleCopy">
    <div v-if="logGroups.length" class="step-log-list">
      <section v-for="group in logGroups" :key="group.key" class="step-log-group">
        <button
          class="step-log-row"
          :class="`level-${group.level.toLowerCase()}`"
          type="button"
          :data-copy-text="formatCopyGroup(group)"
          @click="toggleGroup(group)"
        >
          <span class="step-toggle" :class="{ expanded: isExpanded(group) }" aria-hidden="true"></span>
          <span class="group-title">{{ group.title }}</span>
          <span class="group-meta">{{ group.lines.length }} 条日志</span>
          <span class="group-status" :class="`status-${group.status || 'pending'}`">{{ statusText(group.status) }}</span>
        </button>

        <div v-if="isExpanded(group)" class="step-log-detail">
          <div
            v-for="(line, index) in group.lines"
            :key="index"
            class="log-line"
            :class="`level-${line.level.toLowerCase()}`"
            :data-copy-text="formatCopyLine(line)"
            @click="selectWholeLogLineOnTripleClick"
          >
            <span class="log-token time">[{{ line.time }}]</span>
            <span class="log-token level" :class="`level-${line.level.toLowerCase()}`">[{{ line.level }}]</span>
            <span class="log-token scope">[{{ line.scope }}]</span>
            <span v-if="line.subScope" class="log-token sub-scope">[{{ line.subScope }}]</span>
            <span class="line-icon" :class="`icon-${line.icon}`"></span>
            <span class="log-message">{{ line.message }}</span>
          </div>
        </div>
      </section>
    </div>
    <div v-else class="empty-log">暂无执行日志</div>
  </div>
</template>

<style scoped>
.execution-log-viewer {
  max-height: 68vh;
  overflow: auto;
  padding: 10px 12px;
  border: 1px solid #dce5f0;
  border-radius: 6px;
  background: #f8fafc;
  color: #1f2937;
  font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
  font-size: 13px;
  line-height: 1.5;
}

.step-log-list {
  min-width: 720px;
}

.step-log-group + .step-log-group {
  margin-top: 8px;
}

.log-line {
  display: flex;
  width: max-content;
  min-width: 100%;
  min-height: 24px;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
}

.step-log-row {
  display: grid;
  width: 100%;
  min-height: 42px;
  grid-template-columns: 20px minmax(260px, 1fr) auto auto;
  align-items: center;
  column-gap: 8px;
  border: 1px solid #e1e9f4;
  border-radius: 7px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  padding: 7px 10px;
  text-align: left;
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease;
}

.step-log-row:hover {
  border-color: #bfdbfe;
  background: #fbfdff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
}

.step-log-row.level-error {
  border-left: 4px solid #ef4444;
  background: #fff;
}

.step-log-row.level-error:hover {
  background: #fffafa;
}

.step-log-row.level-warn {
  border-left: 4px solid #f59e0b;
}

.step-log-row.level-info {
  border-left: 4px solid #22c55e;
}

.step-toggle {
  position: relative;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #eef6ff;
  color: #64748b;
  transition:
    background 0.16s ease,
    color 0.16s ease;
}

.step-toggle::before {
  position: absolute;
  top: 50%;
  left: 50%;
  box-sizing: border-box;
  width: 6px;
  height: 6px;
  border-right: 1.8px solid currentColor;
  border-bottom: 1.8px solid currentColor;
  content: "";
  transform: translate(-58%, -50%) rotate(-45deg);
  transform-origin: center;
  transition: transform 0.16s ease;
}

.step-log-row:hover .step-toggle {
  background: #dbeafe;
  color: #2563eb;
}

.step-toggle.expanded {
  transform: none;
}

.step-toggle.expanded::before {
  transform: translate(-50%, -58%) rotate(45deg);
}

.step-log-detail {
  margin: 2px 0 6px 20px;
  padding: 4px 0 4px 10px;
  border-left: 2px solid #dbe7f6;
  font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.65;
  user-select: text;
}

.log-token {
  flex: 0 0 auto;
}

.log-token.time {
  color: #6b7280;
}

.log-token.scope,
.log-token.sub-scope {
  color: #475569;
  font-weight: 600;
}

.log-token.level {
  min-width: 58px;
  font-weight: 800;
}

.log-token.level-info {
  color: #0f5ea8;
}

.log-token.level-warn {
  color: #c27803;
}

.log-token.level-error {
  color: #d92d20;
}

.log-token.level-debug {
  color: #64748b;
}

.group-title {
  min-width: 0;
  overflow: hidden;
  color: #172033;
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-meta {
  flex: 0 0 auto;
  border-radius: 999px;
  background: #f1f5f9;
  color: #667085;
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
  padding: 0 7px;
}

.group-status {
  flex: 0 0 auto;
  min-width: 36px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 18px;
  padding: 0 7px;
  text-align: center;
  font-weight: 650;
}

.status-success {
  color: #168a4a;
  background: #e8f8ef;
}

.status-failed {
  color: #d92d20;
  background: #fff0f0;
}

.status-skipped {
  color: #b76e00;
  background: #fff7e6;
}

.status-pending {
  color: #64748b;
  background: #eef2f7;
}

.log-message {
  flex: 0 0 auto;
  color: #111827;
}

.log-line.level-warn .log-message {
  color: #b76e00;
}

.log-line.level-error .log-message {
  color: #d92d20;
  font-weight: 700;
}

.line-icon {
  position: relative;
  flex: 0 0 auto;
  width: 10px;
  height: 10px;
  background: #2f88ff;
}

.icon-info,
.icon-tool,
.icon-request,
.icon-header,
.icon-start,
.icon-output,
.icon-finish {
  border-radius: 2px;
}

.icon-response,
.icon-variable,
.icon-success {
  border-radius: 50%;
}

.icon-header {
  background: #3f7ea8;
}

.icon-tool {
  background: #5865f2;
}

.icon-response {
  background: #2970ff;
}

.icon-variable {
  background: #168a4a;
}

.icon-start,
.icon-success,
.icon-finish {
  background: #16a34a;
}

.icon-lock {
  border-radius: 2px;
  background: #805ad5;
}

.icon-unlock {
  border: 1px solid #805ad5;
  border-radius: 2px;
  background: transparent;
}

.icon-assert {
  border-radius: 50%;
  background: #f59e0b;
}

.icon-warning {
  width: 0;
  height: 0;
  border-right: 6px solid transparent;
  border-bottom: 11px solid #f59e0b;
  border-left: 6px solid transparent;
  background: transparent;
}

.icon-error {
  background: transparent;
}

.icon-error::before,
.icon-error::after {
  position: absolute;
  top: -1px;
  left: 4px;
  width: 2px;
  height: 12px;
  border-radius: 999px;
  background: #d92d20;
  content: "";
}

.icon-error::before {
  transform: rotate(45deg);
}

.icon-error::after {
  transform: rotate(-45deg);
}

.empty-log {
  min-height: 240px;
  display: grid;
  place-items: center;
  color: #7b8794;
}
</style>
