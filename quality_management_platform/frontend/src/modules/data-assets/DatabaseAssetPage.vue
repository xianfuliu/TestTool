<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { Delete, Edit, RefreshRight, Search } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { fetchBusinessGroups, type BusinessGroupRecord } from "@/shared/api/businessManagement";
import AppPagination from "@/shared/components/AppPagination.vue";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  createDatabaseConnection,
  deleteDatabaseConnection,
  fetchDatabaseConnections,
  testDatabaseConnection,
  updateDatabaseConnection,
  type DatabaseConnectionPayload,
  type DatabaseConnectionRecord,
} from "./api";

type DatabaseForm = DatabaseConnectionPayload & {
  id: number | null;
};

const ALL_BUSINESS_VALUE = "all";

const context = useBusinessProjectContext();
const loading = ref(false);
const saving = ref(false);
const testingConnection = ref(false);
const keyword = ref("");
const selectedBusinessGroupId = ref<number | typeof ALL_BUSINESS_VALUE>(ALL_BUSINESS_VALUE);
const groups = ref<BusinessGroupRecord[]>([]);
const databases = ref<DatabaseConnectionRecord[]>([]);
const dialogVisible = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);
const pageSizeOptions = [10, 20, 50, 100];

const form = reactive<DatabaseForm>({
  id: null,
  business_group_id: null,
  name: "",
  db_type: "MySQL",
  host: "",
  port: 3306,
  database_name: "",
  username: "",
  password: "",
  charset: "utf8mb4",
  description: "",
  enabled: true,
});

const dbTypeOptions = ["MySQL", "PostgreSQL", "Oracle", "SQL Server", "SQLite", "Redis", "MongoDB"];

const paginatedDatabases = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return databases.value.slice(start, start + pageSize.value);
});

function getRowIndex(index: number) {
  return (currentPage.value - 1) * pageSize.value + index + 1;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }
  return String(value).replace("T", " ").replace(/\.\d+$/, "").replace(/Z$/, "");
}

function syncCurrentPage() {
  const maxPage = Math.max(1, Math.ceil(databases.value.length / pageSize.value));
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage;
  }
}

function resetForm() {
  form.id = null;
  form.business_group_id =
    selectedBusinessGroupId.value === ALL_BUSINESS_VALUE
      ? context.selectedGroupId.value ?? groups.value[0]?.id ?? null
      : selectedBusinessGroupId.value;
  form.name = "";
  form.db_type = "MySQL";
  form.host = "";
  form.port = 3306;
  form.database_name = "";
  form.username = "";
  form.password = "";
  form.charset = "utf8mb4";
  form.description = "";
  form.enabled = true;
}

async function loadGroups() {
  groups.value = await fetchBusinessGroups();
  if (selectedBusinessGroupId.value !== ALL_BUSINESS_VALUE && !selectedBusinessGroupId.value) {
    selectedBusinessGroupId.value = context.selectedGroupId.value ?? groups.value[0]?.id ?? null;
  }
}

async function loadDatabases() {
  loading.value = true;
  try {
    databases.value = await fetchDatabaseConnections({
      keyword: keyword.value.trim(),
      business_group_id:
        selectedBusinessGroupId.value === ALL_BUSINESS_VALUE ? null : selectedBusinessGroupId.value,
    });
    syncCurrentPage();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

function openCreateDialog() {
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(row: DatabaseConnectionRecord) {
  form.id = row.id;
  form.business_group_id = row.business_group_id;
  form.name = row.name;
  form.db_type = row.db_type || "MySQL";
  form.host = row.host;
  form.port = Number(row.port) || 3306;
  form.database_name = row.database_name;
  form.username = row.username;
  form.password = row.password;
  form.charset = row.charset || "utf8mb4";
  form.description = row.description || "";
  form.enabled = row.enabled !== false;
  dialogVisible.value = true;
}

function buildPayload(options: { validateIdentity?: boolean } = {}): DatabaseConnectionPayload | null {
  const validateIdentity = options.validateIdentity !== false;
  if (validateIdentity && !form.business_group_id) {
    ElMessage.warning("请选择所属业务");
    return null;
  }
  if (validateIdentity && !form.name.trim()) {
    ElMessage.warning("请输入数据库名称");
    return null;
  }
  if (!form.host.trim()) {
    ElMessage.warning("请输入主机地址");
    return null;
  }
  if (!Number.isFinite(Number(form.port)) || Number(form.port) <= 0 || Number(form.port) > 65535) {
    ElMessage.warning("端口范围应为 1-65535");
    return null;
  }

  return {
    business_group_id: form.business_group_id,
    name: form.name.trim(),
    db_type: form.db_type,
    host: form.host.trim(),
    port: Number(form.port),
    database_name: "",
    username: form.username.trim(),
    password: form.password,
    charset: "utf8mb4",
    description: form.description.trim(),
    enabled: form.enabled,
  };
}

async function testCurrentConnection() {
  const payload = buildPayload({ validateIdentity: false });
  if (!payload) {
    return;
  }
  testingConnection.value = true;
  try {
    const result = await testDatabaseConnection(payload);
    const durationText = result.duration_ms === undefined ? "" : `，耗时 ${result.duration_ms}ms`;
    if (result.connected) {
      ElMessage.success(`${result.message}${durationText}`);
      return;
    }
    ElMessage.error(result.message || "连接失败");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    testingConnection.value = false;
  }
}

async function saveDatabase() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }
  saving.value = true;
  try {
    if (form.id) {
      await updateDatabaseConnection(form.id, payload);
      ElMessage.success("数据库配置已更新");
    } else {
      await createDatabaseConnection(payload);
      ElMessage.success("数据库配置已新增");
    }
    dialogVisible.value = false;
    await loadDatabases();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    saving.value = false;
  }
}

async function removeDatabase(row: DatabaseConnectionRecord) {
  try {
    await ElMessageBox.confirm(`确定删除数据库「${row.name}」吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }

  try {
    await deleteDatabaseConnection(row.id);
    ElMessage.success("数据库配置已删除");
    await loadDatabases();
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function handleSearch() {
  if (!selectedBusinessGroupId.value) {
    selectedBusinessGroupId.value = ALL_BUSINESS_VALUE;
  }
  currentPage.value = 1;
  await loadDatabases();
}

async function resetFilters() {
  keyword.value = "";
  selectedBusinessGroupId.value = ALL_BUSINESS_VALUE;
  currentPage.value = 1;
  await loadDatabases();
}

function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
  syncCurrentPage();
}

function handlePageChange(page: number) {
  currentPage.value = page;
}

onMounted(async () => {
  await context.ensureLoaded();
  await loadGroups();
  await loadDatabases();
});
</script>

<template>
  <div class="database-asset-page" v-loading="loading">
    <section class="asset-toolbar">
      <div class="asset-toolbar-main">
        <div class="asset-search-group">
          <span class="filter-label">业务</span>
          <el-select
            v-model="selectedBusinessGroupId"
            class="business-filter"
            placeholder="选择业务"
            clearable
            popper-class="compact-select-popper"
            @change="handleSearch"
          >
            <el-option label="全部业务" :value="ALL_BUSINESS_VALUE" />
            <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <el-input
            v-model="keyword"
            class="asset-search"
            clearable
            placeholder="搜索名称 / Host / 用户名"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button size="small" :icon="RefreshRight" @click="handleSearch">刷新</el-button>
          <el-button size="small" @click="resetFilters">重置</el-button>
          <el-button size="small" type="primary" @click="openCreateDialog">新增</el-button>
        </div>
      </div>
    </section>

    <section class="database-list-section">
      <el-table
        :data="paginatedDatabases"
        class="database-table"
        height="100%"
        header-align="center"
        cell-class-name="database-table-cell"
        header-cell-class-name="database-table-header-cell"
      >
        <el-table-column label="序号" width="70" align="center" header-align="center">
          <template #default="{ $index }">
            {{ getRowIndex($index) }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="150" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="database-name-cell">
              <span class="db-type-badge">{{ row.db_type || "DB" }}</span>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="business_group_name" label="所属业务" min-width="120" align="center" header-align="center" show-overflow-tooltip />
        <el-table-column prop="host" label="Host" min-width="140" align="center" header-align="center" show-overflow-tooltip />
        <el-table-column prop="port" label="端口" width="78" align="center" header-align="center" />
        <el-table-column prop="username" label="用户名" min-width="110" align="center" header-align="center" show-overflow-tooltip />
        <el-table-column prop="enabled" label="状态" width="86" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" effect="light">
              {{ row.enabled ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="150" align="center" header-align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" header-align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" text type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeDatabase(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无数据库配置" />
        </template>
      </el-table>

      <AppPagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizeOptions"
        :total="databases.length"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑数据库' : '新增数据库'"
      width="720px"
      destroy-on-close
    >
      <el-form label-position="left" label-width="96px" size="small" class="database-form">
        <div class="form-grid">
          <el-form-item label="所属业务">
            <el-select
              v-model="form.business_group_id"
              placeholder="请选择业务"
              filterable
              popper-class="compact-select-popper"
            >
              <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="数据库类型">
            <el-select v-model="form.db_type" filterable allow-create popper-class="compact-select-popper">
              <el-option v-for="item in dbTypeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="数据库名称" class="database-name-item">
            <el-input v-model="form.name" placeholder="例如：中银消金-测试库" />
          </el-form-item>
          <el-form-item label="Host">
            <el-input v-model="form.host" placeholder="127.0.0.1" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number v-model="form.port" :min="1" :max="65535" controls-position="right" />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password placeholder="password" />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </div>
        <el-form-item label="备注" class="description-item">
          <el-input v-model="form.description" type="textarea" :rows="3" resize="none" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="database-dialog-footer">
          <el-button size="small" :loading="testingConnection" @click="testCurrentConnection">测试连接</el-button>
          <div class="database-dialog-actions">
            <el-button size="small" @click="dialogVisible = false">取消</el-button>
            <el-button size="small" type="primary" :loading="saving" @click="saveDatabase">确认</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.database-asset-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  font-size: 12px;
  overflow: hidden;
}

.database-asset-page :deep(.el-table),
.database-asset-page :deep(.el-button),
.database-asset-page :deep(.el-input__inner),
.database-asset-page :deep(.el-input-number__decrease),
.database-asset-page :deep(.el-input-number__increase),
.database-asset-page :deep(.el-select__placeholder),
.database-asset-page :deep(.el-select__selected-item),
.database-asset-page :deep(.el-form-item__label),
.database-asset-page :deep(.el-textarea__inner),
.database-asset-page :deep(.el-tag),
.database-asset-page :deep(.el-pagination) {
  font-size: 12px;
}

.database-asset-page :deep(.el-dialog__title) {
  font-size: 16px;
}

.asset-toolbar,
.database-list-section {
  border: 1px solid #e5edf6;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(31, 35, 41, 0.04);
}

.asset-toolbar {
  flex: 0 0 auto;
  padding: 14px 16px;
  min-width: 0;
}

.asset-toolbar-main {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  min-width: 0;
}

.asset-search-group {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  min-width: 0;
  flex: 0 1 auto;
}

.filter-label {
  flex: 0 0 auto;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  line-height: 28px;
}

.business-filter {
  width: 180px;
  flex: 0 0 180px;
}

.asset-search {
  width: min(420px, 38vw);
  min-width: 260px;
}

.database-list-section {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  padding: 16px;
  overflow: hidden;
}

.database-table {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  width: 100%;
  border: 1px solid #edf1f6;
  border-radius: 8px;
}

.database-table :deep(.el-table__cell) {
  padding: 7px 0;
}

.database-table :deep(.database-table-header-cell .cell),
.database-table :deep(.database-table-cell .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
}

.database-name-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 0;
  font-size: 12px;
  font-weight: 600;
}

.db-type-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #047857;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  white-space: nowrap;
}

.table-actions :deep(.el-button) {
  margin-left: 0;
  padding-left: 4px;
  padding-right: 4px;
}

.database-form {
  padding: 4px 2px 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 24px;
}

.database-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.database-form :deep(.el-form-item__label) {
  align-items: center;
  justify-content: flex-start;
  height: 32px;
  color: #4e5969;
  font-size: 12px;
  line-height: 32px;
}

.database-form :deep(.el-input-number),
.database-form :deep(.el-select),
.database-form :deep(.el-input) {
  width: 100%;
}

.database-name-item {
  grid-column: 1 / -1;
}

.database-name-item :deep(.el-input) {
  width: 450px;
  max-width: 100%;
}

.description-item {
  grid-column: 1 / -1;
}

.description-item :deep(.el-textarea) {
  width: min(100%, 734px);
}

.database-form :deep(.el-input__wrapper),
.database-form :deep(.el-select__wrapper) {
  min-height: 32px;
  border-radius: 6px;
}

.database-form :deep(.el-textarea__inner) {
  min-height: 80px !important;
  border-radius: 6px;
}

.database-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.database-dialog-footer :deep(.el-button) {
  min-width: 64px;
}

.database-dialog-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 1040px) {
  .asset-toolbar-main,
  .asset-search-group {
    align-items: stretch;
    flex-direction: column;
  }

  .business-filter,
  .asset-search {
    width: 100%;
    min-width: 0;
    flex: 0 0 auto;
  }
}

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
