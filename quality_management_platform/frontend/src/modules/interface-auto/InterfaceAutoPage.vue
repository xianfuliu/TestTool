<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { get } from "@/shared/api/client";
import ModuleHeader from "@/shared/components/ModuleHeader.vue";

type OverviewItem = Record<string, unknown>;

type OverviewPayload = {
  business_groups: OverviewItem[];
  projects: OverviewItem[];
  global_tools: OverviewItem[];
  global_variables: OverviewItem[];
  environments: OverviewItem[];
  reports: OverviewItem[];
};

const overview = ref<OverviewPayload | null>(null);
const loading = ref(false);

const latestReport = computed(() => overview.value?.reports?.[0] ?? null);

function formatStatusType(status: unknown) {
  const text = String(status ?? "").toLowerCase();
  if (["success", "passed", "done", "completed"].includes(text)) {
    return "success";
  }
  if (["failed", "error", "stopped"].includes(text)) {
    return "danger";
  }
  if (["running", "pending"].includes(text)) {
    return "warning";
  }
  return "info";
}

function formatStatusLabel(status: unknown) {
  return status ? String(status) : "未执行";
}

function enabledLabel(value: unknown) {
  return value ? "启用" : "停用";
}

function toolStatusType(value: unknown) {
  return value ? "success" : "info";
}

async function loadOverview() {
  loading.value = true;
  try {
    overview.value = await get<OverviewPayload>("/api/interface-auto/overview/");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

onMounted(loadOverview);
</script>

<template>
  <div class="page-shell">
    <ModuleHeader
      title="接口自动化中心"
      subtitle="统一查看业务组、项目、环境、全局变量、工具以及最近执行报告，让自动化资产拥有标准后台式的总览入口。"
    >
      <el-button :loading="loading" @click="loadOverview">刷新概览</el-button>
    </ModuleHeader>

    <div class="grid-two">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div>
            <p class="section-title">运行概况</p>
            <p class="section-caption">从资源沉淀、环境配置和工具治理角度快速评估自动化体系。</p>
          </div>
        </template>

        <div class="summary-list">
          <div class="summary-item">
            <div>
              <strong>项目与环境映射</strong>
              <p>当前共维护 {{ overview?.projects.length ?? 0 }} 个项目，配置 {{ overview?.environments.length ?? 0 }} 套环境。</p>
            </div>
            <el-tag type="primary" effect="plain">{{ overview?.environments.length ?? 0 }} 个环境</el-tag>
          </div>
          <div class="summary-item">
            <div>
              <strong>全局变量与工具</strong>
              <p>全局变量用于沉淀跨项目配置，工具可用于统一封装加解密、脚本调用和通用能力。</p>
            </div>
            <div class="status-row">
              <el-tag type="success" effect="plain">{{ overview?.global_variables.length ?? 0 }} 个变量</el-tag>
              <el-tag type="info" effect="plain">{{ overview?.global_tools.length ?? 0 }} 个工具</el-tag>
            </div>
          </div>
          <div class="summary-item">
            <div>
              <strong>执行报告反馈</strong>
              <p>最近执行结果用于追踪回归质量，后续可继续补齐更完整的执行链路与报告详情。</p>
            </div>
            <el-tag :type="latestReport ? formatStatusType(latestReport.status) : 'info'" effect="light">
              {{ latestReport ? formatStatusLabel(latestReport.status) : "暂无报告" }}
            </el-tag>
          </div>
        </div>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div>
            <p class="section-title">最新执行反馈</p>
            <p class="section-caption">让报告状态在总览页就能被快速识别，而不是埋在原始 JSON 里。</p>
          </div>
        </template>

        <div v-if="latestReport" class="report-panel">
          <div class="report-head">
            <div>
              <strong>{{ latestReport.report_name || "最近一次执行" }}</strong>
              <p>创建时间：{{ latestReport.created_at || "-" }}</p>
            </div>
            <el-tag :type="formatStatusType(latestReport.status)" effect="dark">
              {{ formatStatusLabel(latestReport.status) }}
            </el-tag>
          </div>

          <div class="report-meta">
            <div class="soft-panel">
              <span>关联项目</span>
              <strong>{{ latestReport.project_name || "未关联" }}</strong>
            </div>
            <div class="soft-panel">
              <span>触发方式</span>
              <strong>{{ latestReport.trigger_type || "手动" }}</strong>
            </div>
            <div class="soft-panel">
              <span>执行人</span>
              <strong>{{ latestReport.created_by || "系统" }}</strong>
            </div>
          </div>

          <pre class="json-box">{{ JSON.stringify(latestReport, null, 2) }}</pre>
        </div>

        <div v-else class="empty-block">
          <el-empty description="暂无执行报告" />
        </div>
      </el-card>
    </div>

    <div class="grid-three">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">业务组</p>
              <p class="section-caption">用于隔离不同业务线。</p>
            </div>
            <span class="muted-text">共 {{ overview?.business_groups.length ?? 0 }} 条</span>
          </div>
        </template>
        <el-table :data="overview?.business_groups ?? []" height="280">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">项目</p>
              <p class="section-caption">承接接口模板、用例与执行计划。</p>
            </div>
            <span class="muted-text">共 {{ overview?.projects.length ?? 0 }} 条</span>
          </div>
        </template>
        <el-table :data="overview?.projects ?? []" height="280">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="group_name" label="业务组" min-width="120" />
        </el-table>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">环境配置</p>
              <p class="section-caption">统一管理不同环境的目标地址。</p>
            </div>
            <span class="muted-text">共 {{ overview?.environments.length ?? 0 }} 条</span>
          </div>
        </template>
        <el-table :data="overview?.environments ?? []" height="280">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="name" label="环境" min-width="120" />
          <el-table-column prop="base_url" label="Base URL" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-card>
    </div>

    <div class="grid-three">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">全局工具</p>
              <p class="section-caption">沉淀可被复用的外部工具和脚本能力。</p>
            </div>
            <span class="muted-text">共 {{ overview?.global_tools.length ?? 0 }} 条</span>
          </div>
        </template>
        <el-table :data="overview?.global_tools ?? []" height="280">
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="tool_type" label="类型" min-width="120" />
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="toolStatusType(row.enabled)" effect="plain">
                {{ enabledLabel(row.enabled) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">全局变量</p>
              <p class="section-caption">用于跨项目共享公共配置项。</p>
            </div>
            <span class="muted-text">共 {{ overview?.global_variables.length ?? 0 }} 条</span>
          </div>
        </template>
        <el-table :data="overview?.global_variables ?? []" height="280">
          <el-table-column prop="name" label="变量名" min-width="140" />
          <el-table-column prop="variable_type" label="类型" min-width="120" />
          <el-table-column prop="value" label="值" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">执行报告</p>
              <p class="section-caption">快速查看最近报告状态和时间。</p>
            </div>
            <span class="muted-text">共 {{ overview?.reports.length ?? 0 }} 条</span>
          </div>
        </template>
        <el-table :data="overview?.reports ?? []" height="280">
          <el-table-column prop="report_name" label="报告" min-width="160" show-overflow-tooltip />
          <el-table-column label="状态" min-width="110">
            <template #default="{ row }">
              <el-tag :type="formatStatusType(row.status)" effect="light">
                {{ formatStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.report-panel {
  display: grid;
  gap: 16px;
}

.report-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.report-head strong {
  color: var(--qm-title);
  font-size: 18px;
}

.report-head p {
  margin: 6px 0 0;
  color: var(--qm-text-secondary);
  font-size: 13px;
}

.report-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.soft-panel span {
  display: block;
  color: var(--qm-text-secondary);
  font-size: 12px;
}

.soft-panel strong {
  display: block;
  margin-top: 8px;
  font-size: 15px;
}

@media (max-width: 960px) {
  .report-head {
    flex-direction: column;
  }

  .report-meta {
    grid-template-columns: 1fr;
  }
}
</style>
