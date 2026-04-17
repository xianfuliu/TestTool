<script setup lang="ts">
import { computed, ref } from "vue";

const props = withDefaults(
  defineProps<{
    value: unknown;
    level?: number;
    nodeKey?: string;
    initiallyExpanded?: boolean;
  }>(),
  {
    level: 0,
    nodeKey: "",
    initiallyExpanded: true,
  },
);

const expanded = ref(props.initiallyExpanded);

const isArrayValue = computed(() => Array.isArray(props.value));
const isObjectValue = computed(
  () => props.value !== null && typeof props.value === "object" && !Array.isArray(props.value),
);
const isContainer = computed(() => isArrayValue.value || isObjectValue.value);

const entries = computed(() => {
  if (isArrayValue.value) {
    return (props.value as unknown[]).map((item, index) => ({
      key: String(index),
      value: item,
    }));
  }
  if (isObjectValue.value) {
    return Object.entries(props.value as Record<string, unknown>).map(([key, value]) => ({ key, value }));
  }
  return [];
});

const collapsedSummary = computed(() => {
  if (isArrayValue.value) {
    return `Array(${entries.value.length})[...]`;
  }
  if (isObjectValue.value) {
    return "Object{...}";
  }
  return "";
});

const primitiveClass = computed(() => {
  if (typeof props.value === "string") {
    return "json-value string";
  }
  if (typeof props.value === "number") {
    return "json-value number";
  }
  if (typeof props.value === "boolean") {
    return "json-value boolean";
  }
  if (props.value === null) {
    return "json-value null";
  }
  return "json-value";
});

const primitiveText = computed(() => {
  if (typeof props.value === "string") {
    return `"${props.value}"`;
  }
  if (props.value === null) {
    return "null";
  }
  return String(props.value);
});

function toggle() {
  if (!isContainer.value) {
    return;
  }
  expanded.value = !expanded.value;
}
</script>

<template>
  <div class="json-tree-node" :style="{ '--json-level': String(level) }">
    <template v-if="isContainer">
      <div class="json-tree-line">
        <button class="json-toggle" :class="{ expanded }" type="button" @click="toggle">
          <span class="json-toggle-icon" :class="{ expanded }"></span>
        </button>
        <span v-if="nodeKey" class="json-key">"{{ nodeKey }}"</span>
        <span v-if="nodeKey" class="json-colon">:</span>
        <template v-if="expanded">
          <span class="json-brace">{{ isArrayValue ? "[" : "{" }}</span>
        </template>
        <template v-else>
          <span class="json-summary">{{ collapsedSummary }}</span>
          <span class="json-comma">,</span>
        </template>
      </div>

      <template v-if="expanded">
        <div class="json-tree-children">
          <JsonTreeViewer
            v-for="(entry, index) in entries"
            :key="`${entry.key}-${index}`"
            :value="entry.value"
            :node-key="entry.key"
            :level="level + 1"
            :initially-expanded="level < 1"
          />
        </div>
        <div class="json-tree-line">
          <span class="json-indent"></span>
          <span class="json-brace">{{ isArrayValue ? "]" : "}" }}</span>
        </div>
      </template>
    </template>

    <div v-else class="json-tree-line">
      <span class="json-leaf-spacer"></span>
      <span v-if="nodeKey" class="json-key">"{{ nodeKey }}"</span>
      <span v-if="nodeKey" class="json-colon">:</span>
      <span :class="primitiveClass">{{ primitiveText }}</span>
      <span class="json-comma">,</span>
    </div>
  </div>
</template>

<style scoped>
.json-tree-node {
  margin-left: calc(var(--json-level) * 22px);
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.8;
}

.json-tree-line {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  white-space: nowrap;
}

.json-tree-children {
  margin-top: 1px;
}

.json-toggle {
  width: 16px;
  height: 16px;
  margin-top: 3px;
  border: 1px solid #ff6b6b;
  border-radius: 5px;
  background: #fff;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.json-toggle:not(.expanded) {
  border-color: #16c7ef;
}

.json-toggle-icon {
  position: relative;
  display: block;
  width: 8px;
  height: 8px;
}

.json-toggle-icon::before,
.json-toggle-icon::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  background: #16c7ef;
  transform: translate(-50%, -50%);
  border-radius: 999px;
}

.json-toggle.expanded .json-toggle-icon::before,
.json-toggle.expanded .json-toggle-icon::after {
  background: #ff6b6b;
}

.json-toggle-icon::before {
  width: 7px;
  height: 1px;
}

.json-toggle-icon::after {
  width: 1px;
  height: 7px;
}

.json-toggle-icon.expanded::after {
  display: none;
}

.json-key {
  color: #a626a4;
  font-weight: 600;
}

.json-colon,
.json-brace,
.json-comma,
.json-summary {
  color: #5c6572;
}

.json-value {
  color: #2fb355;
  font-weight: 600;
}

.json-value.null {
  color: #7c8798;
}

.json-indent,
.json-leaf-spacer {
  display: inline-block;
  width: 16px;
  flex: 0 0 16px;
}
</style>
