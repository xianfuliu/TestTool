<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import ModuleHeader from "@/shared/components/ModuleHeader.vue";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import {
  createBusinessGroup,
  createProject,
  deleteBusinessGroup,
  deleteProject,
  fetchBusinessGroups,
  fetchBusinessGroupStats,
  fetchProjects,
  fetchProjectStats,
  updateBusinessGroup,
  updateProject,
  type BusinessGroupRecord,
  type BusinessGroupStats,
  type ProjectRecord,
  type ProjectStats,
} from "@/shared/api/businessManagement";

type TreeNode = {
  key: string;
  label: string;
  meta: string;
  type: "group" | "project" | "virtual";
  group_id: number | null;
  project_id: number | null;
  payload: BusinessGroupRecord | ProjectRecord | null;
  children: TreeNode[];
};

const loading = ref(false);
const detailLoading = ref(false);
const groups = ref<BusinessGroupRecord[]>([]);
const projects = ref<ProjectRecord[]>([]);
const sharedContext = useBusinessProjectContext();

const selectedGroupId = ref<number | null>(null);
const selectedProjectId = ref<number | null>(null);
const currentTreeKey = ref("");
const businessPickerId = ref<number | null>(null);
const activeDetailTab = ref("basic");

const groupStatsCache = ref<Record<number, BusinessGroupStats>>({});
const projectStatsCache = ref<Record<number, ProjectStats>>({});

const groupDialog = reactive({
  visible: false,
  id: null as number | null,
  name: "",
  description: "",
});

const projectDialog = reactive({
  visible: false,
  id: null as number | null,
  business_group_id: null as number | null,
  name: "",
  description: "",
});

const selectedGroup = computed(() => {
  const rows = groups.value as BusinessGroupRecord[];
  for (const item of rows) {
    if (item.id === selectedGroupId.value) {
      return item;
    }
  }
  return null;
});

const selectedProject = computed(() => {
  const rows = projects.value as ProjectRecord[];
  for (const item of rows) {
    if (item.id === selectedProjectId.value) {
      return item;
    }
  }
  return null;
});

const activeGroup = computed(() => {
  const project = selectedProject.value;
  if (project?.business_group_id) {
    const rows = groups.value as BusinessGroupRecord[];
    for (const item of rows) {
      if (item.id === project.business_group_id) {
        return item;
      }
    }
  }
  return selectedGroup.value;
});

const summary = computed(() => {
  let ungroupedProjects = 0;
  const rows = projects.value as ProjectRecord[];
  for (const item of rows) {
    if (!item.business_group_id) {
      ungroupedProjects += 1;
    }
  }

  return {
    groupCount: groups.value.length,
    projectCount: projects.value.length,
    ungroupedProjects,
  };
});

const activeStats = computed(() => {
  if (selectedProjectId.value) {
    return projectStatsCache.value[selectedProjectId.value] ?? null;
  }
  if (selectedGroupId.value) {
    return groupStatsCache.value[selectedGroupId.value] ?? null;
  }
  return null;
});

const detailTitle = computed(() => {
  if (selectedProject.value) {
    return selectedProject.value.name;
  }
  if (selectedGroup.value) {
    return selectedGroup.value.name;
  }
  return "请选择业务组或项目";
});

const detailSubtitle = computed(() => {
  if (selectedProject.value) {
    return "项目是跨功能测试、测试平台、需求协同共同复用的全局主数据。";
  }
  if (selectedGroup.value) {
    return "业务组用于统一组织项目归属，后续会被多个模块复用。";
  }
  return "左侧选择业务组或项目后，这里显示基础信息和统计信息。";
});

const detailStatProjectCount = computed(() => {
  if (selectedProject.value) {
    return "-";
  }
  const stats = activeStats.value as BusinessGroupStats | null;
  return String(stats?.project_count ?? 0);
});

const detailStatApiCount = computed(() => {
  const stats = activeStats.value as BusinessGroupStats | ProjectStats | null;
  return String(stats?.api_count ?? 0);
});

const detailStatCaseCount = computed(() => {
  const stats = activeStats.value as BusinessGroupStats | ProjectStats | null;
  return String(stats?.case_count ?? 0);
});

const groupProjectRows = computed<ProjectRecord[]>(() => {
  if (!activeGroup.value?.id) {
    return [];
  }
  const next: ProjectRecord[] = [];
  const rows = projects.value as ProjectRecord[];
  for (const item of rows) {
    if (item.business_group_id === activeGroup.value.id) {
      next.push(item);
    }
  }
  return next;
});

const treeData = computed<TreeNode[]>(() => {
  const groupMap = new Map<number, TreeNode>();
  const result: TreeNode[] = [];
  const groupRows = groups.value as BusinessGroupRecord[];
  for (const item of groupRows) {
    const node: TreeNode = {
      key: `group-${item.id}`,
      label: item.name,
      meta: "业务组",
      type: "group",
      group_id: item.id,
      project_id: null,
      payload: item,
      children: [],
    };
    groupMap.set(item.id, node);
    result.push(node);
  }

  const ungroupedNode: TreeNode = {
    key: "virtual-ungrouped",
    label: "未分组项目",
    meta: "仅展示历史未归组项目",
    type: "virtual",
    group_id: null,
    project_id: null,
    payload: null,
    children: [],
  };

  const projectRows = projects.value as ProjectRecord[];
  for (const item of projectRows) {
    const node: TreeNode = {
      key: `project-${item.id}`,
      label: item.name,
      meta: item.group_name || "项目",
      type: "project",
      group_id: item.business_group_id,
      project_id: item.id,
      payload: item,
      children: [],
    };

    if (item.business_group_id && groupMap.has(item.business_group_id)) {
      const target = groupMap.get(item.business_group_id);
      if (target) {
        target.children.push(node);
      }
    } else {
      ungroupedNode.children.push(node);
    }
  }

  if (ungroupedNode.children.length) {
    result.push(ungroupedNode);
  }
  return result;
});

function resetSelection() {
  selectedGroupId.value = null;
  selectedProjectId.value = null;
  currentTreeKey.value = "";
  businessPickerId.value = null;
}

function hasGroupNameConflict(name: string, currentId?: number | null) {
  const target = name.trim().toLowerCase();
  const rows = groups.value as BusinessGroupRecord[];
  for (const item of rows) {
    if (item.id !== currentId && item.name.trim().toLowerCase() === target) {
      return true;
    }
  }
  return false;
}

function hasProjectNameConflict(name: string, groupId: number | null, currentId?: number | null) {
  const target = name.trim().toLowerCase();
  const rows = projects.value as ProjectRecord[];
  for (const item of rows) {
    if (
      item.id !== currentId &&
      item.business_group_id === groupId &&
      item.name.trim().toLowerCase() === target
    ) {
      return true;
    }
  }
  return false;
}

async function ensureGroupStats(groupId: number) {
  if (groupStatsCache.value[groupId]) {
    return;
  }
  detailLoading.value = true;
  try {
    const payload = await fetchBusinessGroupStats(groupId);
    groupStatsCache.value = {
      ...groupStatsCache.value,
      [groupId]: payload,
    };
  } finally {
    detailLoading.value = false;
  }
}

async function ensureProjectStats(projectId: number) {
  if (projectStatsCache.value[projectId]) {
    return;
  }
  detailLoading.value = true;
  try {
    const payload = await fetchProjectStats(projectId);
    projectStatsCache.value = {
      ...projectStatsCache.value,
      [projectId]: payload,
    };
  } finally {
    detailLoading.value = false;
  }
}

function selectGroup(groupId: number | null) {
  if (!groupId) {
    resetSelection();
    sharedContext.setGroup(null);
    return;
  }
  selectedGroupId.value = groupId;
  selectedProjectId.value = null;
  currentTreeKey.value = `group-${groupId}`;
  businessPickerId.value = groupId;
  activeDetailTab.value = "basic";
  sharedContext.setGroup(groupId);
  void ensureGroupStats(groupId);
}

function selectProject(projectId: number | null) {
  if (!projectId) {
    resetSelection();
    sharedContext.setProject(null);
    return;
  }

  const rows = projects.value as ProjectRecord[];
  let target: ProjectRecord | null = null;
  for (const item of rows) {
    if (item.id === projectId) {
      target = item;
      break;
    }
  }
  if (!target) {
    resetSelection();
    return;
  }

  selectedProjectId.value = target.id;
  selectedGroupId.value = target.business_group_id;
  currentTreeKey.value = `project-${target.id}`;
  businessPickerId.value = target.business_group_id;
  activeDetailTab.value = "basic";
  sharedContext.setProject(target.id);
  void ensureProjectStats(target.id);
}

function handleTreeNodeClick(node: TreeNode) {
  if (node.type === "group") {
    selectGroup(node.group_id);
    return;
  }
  if (node.type === "project") {
    selectProject(node.project_id);
    return;
  }
  resetSelection();
}

function handleBusinessPickerChange(value: number | null) {
  if (!value) {
    resetSelection();
    return;
  }
  selectGroup(value);
}

function openGroupDialog(row?: BusinessGroupRecord) {
  groupDialog.visible = true;
  groupDialog.id = row?.id ?? null;
  groupDialog.name = row?.name ?? "";
  groupDialog.description = row?.description ?? "";
}

function openProjectDialog(groupId?: number | null, row?: ProjectRecord) {
  projectDialog.visible = true;
  projectDialog.id = row?.id ?? null;
  projectDialog.business_group_id = row?.business_group_id ?? groupId ?? activeGroup.value?.id ?? null;
  projectDialog.name = row?.name ?? "";
  projectDialog.description = row?.description ?? "";
}

function handleEditNode(node: TreeNode) {
  if (node.type === "group" && node.payload) {
    openGroupDialog(node.payload as BusinessGroupRecord);
    return;
  }
  if (node.type === "project" && node.payload) {
    openProjectDialog(undefined, node.payload as ProjectRecord);
  }
}

async function handleDeleteNode(node: TreeNode) {
  if (node.type === "group" && node.payload) {
    await removeGroup(node.payload as BusinessGroupRecord);
    return;
  }
  if (node.type === "project" && node.payload) {
    await removeProject(node.payload as ProjectRecord);
  }
}

async function loadData(preserveSelection = true) {
  loading.value = true;
  try {
    const [groupRows, projectRows] = await Promise.all([fetchBusinessGroups(), fetchProjects()]);
    groups.value = groupRows;
    projects.value = projectRows;

    if (!preserveSelection) {
      resetSelection();
    }

    if (selectedProjectId.value && !projectRows.some((item) => item.id === selectedProjectId.value)) {
      selectedProjectId.value = null;
      currentTreeKey.value = "";
    }
    if (selectedGroupId.value && !groupRows.some((item) => item.id === selectedGroupId.value)) {
      selectedGroupId.value = null;
      currentTreeKey.value = "";
    }

    const preferredProjectId = preserveSelection ? selectedProjectId.value ?? sharedContext.selectedProjectId.value : selectedProjectId.value;
    const preferredGroupId = preserveSelection ? selectedGroupId.value ?? sharedContext.selectedGroupId.value : selectedGroupId.value;

    if (preferredProjectId) {
      selectProject(preferredProjectId);
      return;
    }
    if (preferredGroupId) {
      selectGroup(preferredGroupId);
      return;
    }
    if (selectedProjectId.value) {
      selectProject(selectedProjectId.value);
      return;
    }
    if (selectedGroupId.value) {
      selectGroup(selectedGroupId.value);
      return;
    }
    if (groupRows.length) {
      selectGroup(groupRows[0].id);
    } else {
      resetSelection();
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function saveGroup() {
  const name = groupDialog.name.trim();
  if (!name) {
    ElMessage.warning("请输入业务组名称");
    return;
  }
  if (hasGroupNameConflict(name, groupDialog.id)) {
    ElMessage.warning("业务组名称已存在，请更换后再保存");
    return;
  }

  try {
    let nextId = groupDialog.id;
    if (groupDialog.id) {
      await updateBusinessGroup(groupDialog.id, {
        name,
        description: groupDialog.description.trim(),
      });
    } else {
      const payload = await createBusinessGroup({
        name,
        description: groupDialog.description.trim(),
      });
      nextId = payload.group_id;
    }
    groupDialog.visible = false;
    await loadData(false);
    selectGroup(nextId ?? null);
    await sharedContext.refresh();
    ElMessage.success("业务组已保存");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function saveProject() {
  const groupId = projectDialog.business_group_id;
  const name = projectDialog.name.trim();
  if (!groupId) {
    ElMessage.warning("请选择所属业务组");
    return;
  }
  if (!name) {
    ElMessage.warning("请输入项目名称");
    return;
  }
  if (hasProjectNameConflict(name, groupId, projectDialog.id)) {
    ElMessage.warning("当前业务组下已存在同名项目");
    return;
  }

  try {
    let nextId = projectDialog.id;
    if (projectDialog.id) {
      await updateProject(projectDialog.id, {
        business_group_id: groupId,
        name,
        description: projectDialog.description.trim(),
      });
    } else {
      const payload = await createProject({
        business_group_id: groupId,
        name,
        description: projectDialog.description.trim(),
      });
      nextId = payload.project_id;
    }
    projectDialog.visible = false;
    await loadData(false);
    selectProject(nextId ?? null);
    await sharedContext.refresh();
    ElMessage.success("项目已保存");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function removeGroup(row: BusinessGroupRecord) {
  try {
    await ElMessageBox.confirm(
      `确定删除业务组“${row.name}”吗？如果业务组下仍有关联项目，需要先处理项目归属。`,
      "删除业务组",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
    await deleteBusinessGroup(row.id);
    await loadData(false);
    await sharedContext.refresh();
    ElMessage.success("业务组已删除");
  } catch (error) {
    if (error instanceof Error && error.message && error.message !== "cancel") {
      ElMessage.error(error.message);
    }
  }
}

async function removeProject(row: ProjectRecord) {
  try {
    await ElMessageBox.confirm(
      `确定删除项目“${row.name}”吗？如果项目下仍有关联资产，需要先清理后再删除。`,
      "删除项目",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
    await deleteProject(row.id);
    await loadData(false);
    await sharedContext.refresh();
    ElMessage.success("项目已删除");
  } catch (error) {
    if (error instanceof Error && error.message && error.message !== "cancel") {
      ElMessage.error(error.message);
    }
  }
}

void loadData();
</script>

<template>
  <div class="page-shell business-page">
    <ModuleHeader
      title="业务管理"
      subtitle="把旧接口自动化里的业务管理迁成质量管理平台的全局主数据，供需求协同、功能测试和测试平台共同复用。"
    />

    <div class="business-summary">
      <div class="business-summary__item">
        <span>业务组</span>
        <strong>{{ summary.groupCount }}</strong>
      </div>
      <div class="business-summary__item">
        <span>项目</span>
        <strong>{{ summary.projectCount }}</strong>
      </div>
      <div class="business-summary__item">
        <span>未分组项目</span>
        <strong>{{ summary.ungroupedProjects }}</strong>
      </div>
      <div class="business-summary__item">
        <span>当前上下文</span>
        <strong>{{ detailTitle }}</strong>
      </div>
    </div>

    <div class="business-layout">
      <el-card v-loading="loading" class="surface-card" shadow="never">
        <template #header>
          <div>
            <p class="section-title">业务组与项目树</p>
            <p class="section-caption">延续旧版左树右详情的使用方式，先选业务组，再在组下维护项目。</p>
          </div>
        </template>

        <div class="business-toolbar">
          <el-select
            :model-value="businessPickerId"
            clearable
            class="business-toolbar__picker"
            placeholder="快速切换业务组"
            @change="handleBusinessPickerChange"
          >
            <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
          <div class="business-toolbar__actions">
            <el-button size="small" @click="openGroupDialog()">新建业务组</el-button>
            <el-button size="small" type="primary" :disabled="!activeGroup?.id" @click="openProjectDialog(activeGroup?.id)">
              新建项目
            </el-button>
          </div>
        </div>

        <el-tree
          :data="treeData"
          node-key="key"
          default-expand-all
          :expand-on-click-node="false"
          :current-node-key="currentTreeKey || undefined"
          class="business-tree"
          @node-click="handleTreeNodeClick"
        >
          <template #default="{ data }">
            <div class="business-tree-node" :class="{ 'business-tree-node--virtual': data.type === 'virtual' }">
              <div class="business-tree-node__main">
                <strong>{{ data.label }}</strong>
                <span>{{ data.meta }}</span>
              </div>
              <div v-if="data.type !== 'virtual'" class="business-tree-node__actions">
                <el-button
                  v-if="data.type === 'group'"
                  link
                  size="small"
                  type="primary"
                  @click.stop="openProjectDialog(data.group_id)"
                >
                  新建项目
                </el-button>
                <el-button link size="small" type="primary" @click.stop="handleEditNode(data)">编辑</el-button>
                <el-button link size="small" type="danger" @click.stop="handleDeleteNode(data)">删除</el-button>
              </div>
            </div>
          </template>
        </el-tree>
      </el-card>

      <el-card v-loading="detailLoading" class="surface-card" shadow="never">
        <template #header>
          <div class="business-detail__header">
            <div>
              <p class="section-title">{{ detailTitle }}</p>
              <p class="section-caption">{{ detailSubtitle }}</p>
            </div>
          </div>
        </template>

        <template v-if="selectedGroup || selectedProject">
          <el-tabs v-model="activeDetailTab">
            <el-tab-pane label="基础信息" name="basic">
              <div class="detail-grid">
                <div class="detail-field">
                  <span>对象类型</span>
                  <strong>{{ selectedProject ? "项目" : "业务组" }}</strong>
                </div>
                <div class="detail-field">
                  <span>名称</span>
                  <strong>{{ detailTitle }}</strong>
                </div>
                <div class="detail-field">
                  <span>所属业务组</span>
                  <strong>{{ selectedProject ? (activeGroup?.name || "未分组") : "当前业务组" }}</strong>
                </div>
                <div class="detail-field">
                  <span>创建时间</span>
                  <strong>{{ (selectedProject || selectedGroup)?.created_at || "-" }}</strong>
                </div>
                <div class="detail-field">
                  <span>更新时间</span>
                  <strong>{{ (selectedProject || selectedGroup)?.updated_at || "-" }}</strong>
                </div>
                <div class="detail-field detail-field--full">
                  <span>说明</span>
                  <strong>{{ (selectedProject || selectedGroup)?.description || "暂无说明" }}</strong>
                </div>
              </div>

              <div v-if="activeGroup" class="related-panel">
                <div class="related-panel__header">
                  <strong>当前业务组下的项目</strong>
                  <span>{{ groupProjectRows.length }} 个项目</span>
                </div>
                <el-table :data="groupProjectRows" max-height="260" row-key="id">
                  <el-table-column prop="name" label="项目名称" min-width="180" />
                  <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
                </el-table>
              </div>
            </el-tab-pane>

            <el-tab-pane label="统计信息" name="stats">
              <div class="business-stats">
                <div class="business-stats__item">
                  <span>项目数</span>
                  <strong>{{ detailStatProjectCount }}</strong>
                </div>
                <div class="business-stats__item">
                  <span>接口模板数</span>
                  <strong>{{ detailStatApiCount }}</strong>
                </div>
                <div class="business-stats__item">
                  <span>测试用例数</span>
                  <strong>{{ detailStatCaseCount }}</strong>
                </div>
              </div>

              <div class="business-note">
                <strong>说明</strong>
                <p>这里先沿用旧版业务管理的统计口径，展示项目、接口模板和测试用例数量，后续再扩展到更多全局模块。</p>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <div v-else class="business-empty">
          <el-empty description="先在左侧选择业务组或项目" />
        </div>
      </el-card>
    </div>

    <el-dialog v-model="groupDialog.visible" :title="groupDialog.id ? '编辑业务组' : '新建业务组'" width="520px">
      <el-form label-position="top">
        <el-form-item label="业务组名称">
          <el-input v-model="groupDialog.name" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="groupDialog.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="groupDialog.visible = false">取消</el-button>
        <el-button size="small" type="primary" @click="saveGroup">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="projectDialog.visible" :title="projectDialog.id ? '编辑项目' : '新建项目'" width="520px">
      <el-form label-position="top">
        <el-form-item label="所属业务组">
          <el-select v-model="projectDialog.business_group_id" class="business-dialog__full" placeholder="请选择业务组">
            <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="projectDialog.name" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="projectDialog.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="projectDialog.visible = false">取消</el-button>
        <el-button size="small" type="primary" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.business-page {
  min-height: calc(100vh - 56px);
  gap: 10px;
}

.business-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.business-summary__item,
.business-stats__item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-height: 34px;
  padding: 7px 10px;
  border: 1px solid #e9edf3;
  border-radius: 8px;
  background: #ffffff;
}

.business-summary__item span,
.business-stats__item span,
.detail-field span,
.business-tree-node__main span,
.related-panel__header span {
  display: inline;
  color: var(--qm-text-secondary);
  font-size: 12px;
}

.business-summary__item strong,
.business-stats__item strong,
.detail-field strong {
  display: inline;
  margin-top: 0;
  color: var(--qm-title);
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.business-summary__item strong,
.business-stats__item strong {
  padding: 1px 8px;
  border-radius: 999px;
  background: #eef6ff;
  color: #1d4ed8;
  font-weight: 700;
}

.business-layout {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.business-layout > .surface-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.business-layout > .surface-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.business-toolbar,
.business-detail__header,
.business-tree-node,
.related-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.business-toolbar {
  margin-bottom: 8px;
}

.business-toolbar__picker {
  width: 190px;
}

.business-toolbar__actions,
.business-detail__actions,
.business-tree-node__actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.business-tree {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 2px 0;
}

.business-tree-node {
  width: 100%;
  min-height: 30px;
}

.business-tree-node__main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.business-tree-node__main strong {
  display: inline;
  color: var(--qm-title);
  font-size: 13px;
  line-height: 1.35;
}

.business-tree-node__actions {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.business-tree-node:hover .business-tree-node__actions,
:deep(.el-tree-node.is-current) .business-tree-node__actions {
  opacity: 1;
}

.business-tree-node--virtual .business-tree-node__main strong {
  color: var(--qm-text-secondary);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.detail-field {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  min-height: 34px;
  padding: 7px 10px;
  border: 1px solid #e9edf3;
  border-radius: 8px;
  background: #ffffff;
}

.detail-field--full {
  grid-column: 1 / -1;
}

.related-panel {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #e9edf3;
  border-radius: 8px;
  background: #ffffff;
}

.related-panel__header {
  margin-bottom: 8px;
}

.related-panel__header strong {
  color: var(--qm-title);
  font-size: 14px;
}

.business-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.business-note {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #f6f9fc;
  color: var(--qm-text-secondary);
  line-height: 1.6;
}

.business-note strong {
  color: var(--qm-title);
}

.business-note p {
  margin: 4px 0 0;
}

.business-empty {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.business-dialog__full {
  width: 100%;
}

.page-shell :deep(.el-button) {
  min-height: 26px;
  padding: 5px 10px;
  font-size: 12px;
}

.page-shell :deep(.el-button.is-link) {
  min-height: auto;
  padding: 0 2px;
}

.page-shell :deep(.el-card__header) {
  padding: 10px 12px;
}

.page-shell :deep(.el-card__body) {
  padding: 10px 12px;
}

.page-shell :deep(.el-input__wrapper),
.page-shell :deep(.el-select__wrapper) {
  min-height: 28px;
  font-size: 12px;
}

.page-shell :deep(.el-tree-node__content) {
  min-height: 32px;
}

.page-shell :deep(.el-tabs__header) {
  margin-bottom: 10px;
}

@media (max-width: 1360px) {
  .business-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .business-summary,
  .detail-grid,
  .business-stats {
    grid-template-columns: 1fr;
  }

  .business-toolbar,
  .business-detail__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .business-toolbar__picker {
    width: 100%;
  }
}
</style>
