<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Edit, Plus, RefreshRight, Search } from "@element-plus/icons-vue";

import {
  createEnvironment,
  deleteEnvironment,
  fetchEnvironments,
  updateEnvironment,
} from "./environmentApi";
import type { EnvironmentPayload, EnvironmentRecord } from "./environmentTypes";

const loading = ref(false);
const saving = ref(false);
const keyword = ref("");
const dialogVisible = ref(false);
const dialogTitle = ref("");
const environments = ref<EnvironmentRecord[]>([]);

const form = reactive({
  id: null as number | null,
  name: "",
  base_url: "",
});

const filteredEnvironments = computed(() => {
  const text = keyword.value.trim().toLowerCase();
  if (!text) {
    return environments.value;
  }
  return environments.value.filter((item) =>
    `${item.name} ${item.base_url ?? ""}`.toLowerCase().includes(text),
  );
});

function resetForm() {
  form.id = null;
  form.name = "";
  form.base_url = "";
}

function fillForm(environment: EnvironmentRecord) {
  form.id = environment.id;
  form.name = environment.name;
  form.base_url = environment.base_url ?? "";
}

function buildPayload(): EnvironmentPayload | null {
  const name = form.name.trim();
  if (!name) {
    ElMessage.warning("请输入环境名称");
    return null;
  }
  return {
    name,
    base_url: form.base_url.trim(),
    description: "",
  };
}

async function loadData() {
  loading.value = true;
  try {
    const rows = await fetchEnvironments();
    environments.value = Array.isArray(rows) ? rows : [];
  } finally {
    loading.value = false;
  }
}

function openCreateDialog() {
  resetForm();
  dialogTitle.value = "新增环境";
  dialogVisible.value = true;
}

function openEditDialog(environment: EnvironmentRecord) {
  resetForm();
  fillForm(environment);
  dialogTitle.value = "编辑环境";
  dialogVisible.value = true;
}

async function saveEnvironment() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }
  saving.value = true;
  try {
    if (form.id) {
      await updateEnvironment(form.id, payload);
      ElMessage.success("环境已更新");
    } else {
      await createEnvironment(payload);
      ElMessage.success("环境已创建");
    }
    dialogVisible.value = false;
    await loadData();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

async function removeEnvironment(environment: EnvironmentRecord) {
  try {
    await ElMessageBox.confirm(`确认删除环境“${environment.name}”吗？`, "删除环境", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await deleteEnvironment(environment.id);
    ElMessage.success("环境已删除");
    await loadData();
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error((error as Error).message);
    }
  }
}

onMounted(async () => {
  await loadData();
});
</script>

<template>
  <div class="global-tool-page" v-loading="loading">
    <section class="scheduler-toolbar">
      <div class="filter-row">
        <el-input
          v-model="keyword"
          clearable
          class="keyword-input"
          placeholder="搜索环境名称"
          :prefix-icon="Search"
        />

        <el-button size="small" :icon="RefreshRight" :loading="loading" @click="loadData">刷新</el-button>
        <el-button size="small" type="primary" :icon="Plus" @click="openCreateDialog">新增环境</el-button>
      </div>
    </section>

    <section class="task-list-section">
      <el-table
        :data="filteredEnvironments"
        class="task-table"
        height="100%"
        cell-class-name="task-table-cell"
        header-cell-class-name="task-table-header-cell"
      >
        <el-table-column label="序号" width="76" align="center" header-align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column
          label="环境名称"
          min-width="220"
          class-name="text-column"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="name-cell" :title="row.name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="域名"
          min-width="340"
          class-name="text-column"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="value-cell" :title="row.base_url">{{ row.base_url || "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">{{ row.updated_at || row.created_at || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" header-align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" text type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeEnvironment(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无环境配置" />
        </template>
      </el-table>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="860px"
      destroy-on-close
      class="global-tool-dialog"
    >
      <el-form label-width="74px" class="global-tool-form" @submit.prevent>
        <div class="basic-grid">
          <el-form-item label="环境名称" required>
            <el-input v-model="form.name" clearable maxlength="100" placeholder="请输入环境名称" />
          </el-form-item>
          <el-form-item label="域名">
            <el-input v-model="form.base_url" clearable placeholder="请输入环境域名" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveEnvironment">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.global-tool-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  font-size: 12px;
}

.global-tool-page :deep(.el-table),
.global-tool-page :deep(.el-button),
.global-tool-page :deep(.el-input__inner),
.global-tool-page :deep(.el-select__placeholder),
.global-tool-page :deep(.el-select__selected-item),
.global-tool-page :deep(.el-form-item__label),
.global-tool-page :deep(.el-textarea__inner),
.global-tool-page :deep(.el-tag) {
  font-size: 12px;
}

.scheduler-toolbar,
.task-list-section {
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(31, 35, 41, 0.04);
}

.scheduler-toolbar {
  flex: 0 0 auto;
  padding: 14px 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.keyword-input {
  width: min(360px, 26vw);
  min-width: 220px;
}

.task-list-section {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 16px;
  overflow: hidden;
}

.task-table {
  flex: 1 1 0;
  width: 100%;
  min-width: 0;
  min-height: 0;
  border: 1px solid #edf1f6;
  border-radius: 8px;
}

.task-table :deep(.el-table__cell) {
  padding: 7px 0;
}

.task-table :deep(.task-table-header-cell .cell),
.task-table :deep(.task-table-cell .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  white-space: nowrap;
}

.task-table :deep(.text-column .cell) {
  justify-content: flex-start;
  padding-left: 14px;
  padding-right: 14px;
}

.name-cell,
.value-cell {
  display: inline-flex;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name-cell {
  color: #1f2937;
  font-weight: 600;
}

.value-cell {
  color: #475569;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.table-actions :deep(.el-button) {
  margin-left: 0;
  padding-left: 3px;
  padding-right: 3px;
}

.basic-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(340px, 1.1fr);
  gap: 0 12px;
}
</style>
