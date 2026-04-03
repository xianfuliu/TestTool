<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";

import { get, post } from "@/shared/api/client";
import ModuleHeader from "@/shared/components/ModuleHeader.vue";

type QueryConfig = {
  input_fields: Record<string, { label: string; placeholder: string }>;
  sql_queries: Record<
    string,
    {
      display_name: string;
      required_params: string[];
    }
  >;
};

const config = ref<QueryConfig | null>(null);
const selectedQuery = ref("");
const variables = ref<Record<string, string>>({});
const resultRows = ref<Record<string, unknown>[]>([]);
const resultSql = ref("");
const loading = ref(false);

const activeFields = computed(() => {
  const currentConfig = config.value;
  if (!currentConfig || !selectedQuery.value) {
    return [];
  }
  const requiredParams = currentConfig.sql_queries[selectedQuery.value]?.required_params ?? [];
  return requiredParams.map((field) => ({
    key: field,
    ...currentConfig.input_fields[field],
  }));
});

const queryOptions = computed(() =>
  Object.entries(config.value?.sql_queries ?? {}).map(([key, value]) => ({
    key,
    displayName: value.display_name,
  })),
);

const resultColumns = computed(() => Object.keys(resultRows.value[0] ?? {}));

watch(selectedQuery, () => {
  variables.value = {};
  resultRows.value = [];
  resultSql.value = "";
});

async function loadConfig() {
  try {
    config.value = await get<QueryConfig>("/api/data-query/config/");
    selectedQuery.value = Object.keys(config.value.sql_queries)[0] ?? "";
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function executeQuery() {
  loading.value = true;
  try {
    const data = await post<{ rows: Record<string, unknown>[]; sql: string }>("/api/data-query/execute/", {
      query_name: selectedQuery.value,
      variables: variables.value,
    });
    resultRows.value = data.rows;
    resultSql.value = data.sql;
    ElMessage.success("查询执行完成");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

onMounted(loadConfig);
</script>

<template>
  <div class="page-shell">
    <ModuleHeader
      title="数据查询模块"
      subtitle="延续配置驱动的查询方式，把模板、参数、执行 SQL 和结果表格整理成更标准的后台查询台。"
    >
      <el-button type="primary" :loading="loading" @click="executeQuery">执行查询</el-button>
    </ModuleHeader>

    <div class="grid-two">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">查询条件</p>
              <p class="section-caption">先选模板，再填写模板要求的参数。</p>
            </div>
            <span class="muted-text">
              当前模板：{{ queryOptions.find((item) => item.key === selectedQuery)?.displayName || "未选择" }}
            </span>
          </div>
        </template>

        <el-form label-position="top">
          <el-form-item label="查询模板">
            <el-select v-model="selectedQuery" placeholder="请选择查询模板" filterable>
              <el-option
                v-for="item in queryOptions"
                :key="item.key"
                :label="item.displayName"
                :value="item.key"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-for="field in activeFields"
            :key="field.key"
            :label="field.label"
          >
            <el-input
              v-model="variables[field.key]"
              :placeholder="field.placeholder"
            />
          </el-form-item>

          <div class="soft-panel query-note">
            <strong>使用说明</strong>
            <p>所有参数字段都由后端配置返回，前端只负责渲染与提交，不在页面内硬编码业务 SQL。</p>
          </div>
        </el-form>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div>
            <p class="section-title">执行 SQL</p>
            <p class="section-caption">保留可核查的 SQL 展示，方便确认模板替换结果。</p>
          </div>
        </template>
        <pre class="json-box">{{ resultSql || "-- 等待执行后显示 SQL --" }}</pre>
      </el-card>
    </div>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <div>
            <p class="section-title">查询结果</p>
            <p class="section-caption">以标准后台表格方式展示返回数据。</p>
          </div>
          <span class="muted-text">共 {{ resultRows.length }} 行</span>
        </div>
      </template>

      <el-table v-if="resultRows.length" :data="resultRows" height="420">
        <el-table-column
          v-for="column in resultColumns"
          :key="column"
          :prop="column"
          :label="column"
          min-width="140"
          show-overflow-tooltip
        />
      </el-table>

      <div v-else class="empty-block">
        <el-empty description="执行查询后展示结果" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.query-note {
  margin-top: 8px;
}

.query-note p {
  margin: 8px 0 0;
  color: var(--qm-text-secondary);
  font-size: 13px;
  line-height: 1.8;
}
</style>
