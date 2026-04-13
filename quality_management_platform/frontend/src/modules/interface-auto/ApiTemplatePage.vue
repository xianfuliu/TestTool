<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Folder, FolderAdd, MagicStick, Search } from "@element-plus/icons-vue";

import { del, get, post, put } from "@/shared/api/client";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import type { ApiFolder, ApiTemplate, CascaderOption, JsonMap, KeyValueRow, TreeNode, WorkspacePayload } from "./types";

const context = useBusinessProjectContext();
const loading = ref(false);
const saving = ref(false);
const searchText = ref("");
const projectPath = ref<number[]>([]);
const selectedFolderId = ref<number | null>(null);
const selectedTemplateId = ref<number | null>(null);
const selectedNodeType = ref<"folder" | "template" | null>(null);
const activeEditorTab = ref("body");
const activeTabKey = ref("");
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  node: null as TreeNode | null,
});
const tabContextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  tabKey: "",
});
const modifiedTabs = reactive<Record<string, boolean>>({});
const openedTabs = ref<ApiTemplate[]>([]);
const folders = ref<ApiFolder[]>([]);
const templates = ref<ApiTemplate[]>([]);
const headerRows = ref<KeyValueRow[]>([]);
const paramRows = ref<KeyValueRow[]>([]);
const bodyText = ref("{}");
const responseText = ref("调试响应将显示在这里...");

const form = reactive<ApiTemplate>(emptyTemplate(0, null));
let resetting = false;

const currentProjectId = computed(() => context.selectedProject.value?.id ?? null);
const currentFolder = computed(() => folders.value.find((item) => item.id === selectedFolderId.value) ?? null);
const projectOptions = computed<CascaderOption[]>(() =>
  context.groups.value.map((group) => {
    const children = context.projects.value
      .filter((project) => project.business_group_id === group.id)
      .map((project) => ({
        value: project.id,
        label: project.name,
      }));
    return {
      value: group.id,
      label: group.name,
      disabled: !children.length,
      children,
    };
  }),
);
const cascaderProps = {
  expandTrigger: "hover" as const,
  emitPath: true,
  checkStrictly: false,
};
const currentProjectTemplates = computed(() =>
  searchText.value.trim()
    ? templates.value.filter((item) => {
        const keyword = searchText.value.trim().toLowerCase();
        return item.name.toLowerCase().includes(keyword) || item.url_path.toLowerCase().includes(keyword);
      })
    : templates.value,
);

const treeData = computed<TreeNode[]>(() => {
  const childrenMap = new Map<number | null, ApiFolder[]>();
  folders.value.forEach((folder) => {
    const children = childrenMap.get(folder.parent_id ?? null) ?? [];
    children.push(folder);
    childrenMap.set(folder.parent_id ?? null, children);
  });

  const buildFolder = (folder: ApiFolder): TreeNode => {
    const childFolders = (childrenMap.get(folder.id) ?? []).map(buildFolder);
    const childTemplates = currentProjectTemplates.value
      .filter((item) => item.folder_id === folder.id)
      .map(templateNode);
    return {
      id: `folder-${folder.id}`,
      rawId: folder.id,
      label: folder.name,
      type: "folder",
      folderId: folder.id,
      parentFolderId: folder.parent_id ?? null,
      children: [...childFolders, ...childTemplates],
    };
  };

  const rootTemplates = currentProjectTemplates.value.filter((item) => item.folder_id === null).map(templateNode);
  return [...(childrenMap.get(null) ?? []).map(buildFolder), ...rootTemplates];
});

function templateNode(template: ApiTemplate): TreeNode {
  return {
    id: `template-${template.id}`,
    rawId: template.id ?? null,
    label: template.name,
    type: "template",
    folderId: template.folder_id ?? null,
    parentFolderId: template.folder_id ?? null,
    template,
    method: template.method,
  };
}

function emptyTemplate(projectId: number, folderId: number | null): ApiTemplate {
  return {
    tabKey: `new-${Date.now()}`,
    project_id: projectId,
    folder_id: folderId,
    name: "",
    method: "GET",
    url_path: "",
    headers: { "Content-Type": "application/json" },
    params: {},
    body: {},
    description: "",
    timeout: 30,
    retry_enabled: false,
    retry_count: 3,
    sort_order: 0,
  };
}

function rowId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function mapToRows(value: JsonMap | undefined) {
  return Object.entries(value ?? {}).map(([key, rowValue]) => ({ id: rowId(), key, value: String(rowValue) }));
}

function rowsToMap(rows: KeyValueRow[]) {
  return rows.reduce<JsonMap>((result, row) => {
    const key = row.key.trim();
    if (key) {
      result[key] = row.value;
    }
    return result;
  }, {});
}

function stringifyBody(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "{}";
  }
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function resetForm(template?: ApiTemplate) {
  resetting = true;
  const next = template ?? emptyTemplate(currentProjectId.value ?? 0, selectedFolderId.value);
  Object.assign(form, {
    ...next,
    headers: next.headers ?? {},
    params: next.params ?? {},
    body: next.body ?? {},
    timeout: next.timeout ?? 30,
    retry_enabled: Boolean(next.retry_enabled),
    retry_count: next.retry_count ?? 3,
  });
  headerRows.value = mapToRows(form.headers);
  paramRows.value = mapToRows(form.params);
  if (!headerRows.value.length) {
    addHeaderRow();
  }
  if (!paramRows.value.length) {
    addParamRow();
  }
  bodyText.value = stringifyBody(form.body);
  nextTick(() => {
    resetting = false;
  });
}

async function loadWorkspace() {
  if (!currentProjectId.value) {
    folders.value = [];
    templates.value = [];
    openedTabs.value = [];
    resetForm(emptyTemplate(0, null));
    return;
  }
  loading.value = true;
  try {
    const payload = await get<WorkspacePayload>("/api/interface-auto/api-template-workspace/", {
      project_id: currentProjectId.value,
    });
    folders.value = payload.folders;
    templates.value = payload.templates;
    const latest = selectedTemplateId.value ? templates.value.find((item) => item.id === selectedTemplateId.value) : null;
    if (latest) {
      const activeIndex = activeTabKey.value ? openedTabs.value.findIndex((item) => getTabKey(item) === activeTabKey.value) : -1;
      if (activeIndex !== -1) {
        openedTabs.value[activeIndex] = { ...latest, tabKey: activeTabKey.value };
        resetForm(latest);
      } else {
        openTemplate(latest);
      }
    } else {
      syncOpenedTabs();
      if (!openedTabs.value.length) {
        selectedTemplateId.value = null;
        activeTabKey.value = "";
        resetForm(undefined);
      }
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

function onTreeClick(node: TreeNode) {
  hideContextMenu();
  selectedNodeType.value = node.type;
  selectedFolderId.value = node.folderId;
  if (node.type === "template" && node.template) {
    openTemplateFromTree(node.template);
    return;
  }
  selectedTemplateId.value = null;
  resetForm(emptyTemplate(currentProjectId.value ?? 0, node.folderId));
}

function openTemplateFromTree(template: ApiTemplate) {
  const key = getTabKey(template);
  const existing = openedTabs.value.find((item) => getTabKey(item) === key || (item.id && item.id === template.id));
  if (existing) {
    openTemplate({ ...template, tabKey: existing.tabKey });
    return;
  }
  openTemplate(template);
}

function openTemplate(template: ApiTemplate) {
  selectedTemplateId.value = template.id ?? null;
  selectedNodeType.value = "template";
  selectedFolderId.value = template.folder_id ?? null;
  const key = getTabKey(template);
  const existingIndex = openedTabs.value.findIndex((item) => getTabKey(item) === key);
  if (existingIndex === -1) {
    openedTabs.value.push({ ...template, tabKey: key });
  } else {
    openedTabs.value[existingIndex] = { ...template, tabKey: key };
  }
  activeTabKey.value = key;
  resetForm(template);
}

function getTabKey(template: ApiTemplate) {
  return template.tabKey || (template.id ? `template-${template.id}` : "new-template");
}

function syncOpenedTabs() {
  openedTabs.value = openedTabs.value
    .map((tab) => {
      const latest = tab.id ? templates.value.find((item) => item.id === tab.id) : null;
      return latest ? { ...latest, tabKey: tab.tabKey } : tab;
    })
    .filter((item): item is ApiTemplate => Boolean(item))
    .map((item) => ({ ...item, tabKey: getTabKey(item) }));
}

function closeOpenedTab(tabName: string) {
  void closeTabsWithConfirm([tabName]);
}

function getTabTitle(tabKey: string) {
  const tab = openedTabs.value.find((item) => getTabKey(item) === tabKey);
  if (!tab) {
    return "接口";
  }
  const title = tab.id ? tab.name : "新增接口";
  return modifiedTabs[tabKey] ? `*${title}` : title;
}

function changeOpenedTab(name: string | number) {
  const next = openedTabs.value.find((item) => getTabKey(item) === String(name));
  if (next) {
    openTemplate(next);
  }
}

async function createFolder(parentId: number | null = null) {
  if (!currentProjectId.value) {
    ElMessage.warning("请先选择项目");
    return;
  }
  const { value } = await ElMessageBox.prompt("请输入目录名称", "新建接口目录", {
    inputPlaceholder: "例如：登录模块",
    confirmButtonText: "创建",
    cancelButtonText: "取消",
    inputValidator: (value) => Boolean(value.trim()) || "目录名称不能为空",
  });
  await post("/api/interface-auto/api-folders/", {
    project_id: currentProjectId.value,
    parent_id: parentId,
    name: value.trim(),
  });
  ElMessage.success("目录已创建");
  await loadWorkspace();
}

async function createChildFolder() {
  if (!contextMenu.node || contextMenu.node.type !== "folder") {
    return;
  }
  await createFolder(contextMenu.node.folderId);
  hideContextMenu();
}

function createTemplate() {
  selectedTemplateId.value = null;
  selectedNodeType.value = "template";
  const next = emptyTemplate(currentProjectId.value ?? 0, selectedFolderId.value);
  openedTabs.value.push(next);
  activeTabKey.value = getTabKey(next);
  resetForm(next);
  nextTick(() => {
    document.querySelector<HTMLInputElement>(".template-name-input input")?.focus();
  });
}

function addHeaderRow() {
  headerRows.value.push({ id: rowId(), key: "", value: "" });
}

function addParamRow() {
  paramRows.value.push({ id: rowId(), key: "", value: "" });
}

function removeHeaderRow(rowId: string) {
  headerRows.value = headerRows.value.filter((item) => item.id !== rowId);
  if (!headerRows.value.length) {
    addHeaderRow();
  }
}

function removeParamRow(rowId: string) {
  paramRows.value = paramRows.value.filter((item) => item.id !== rowId);
  if (!paramRows.value.length) {
    addParamRow();
  }
}

function parseBody() {
  const text = bodyText.value.trim();
  if (!text) {
    return {};
  }
  return JSON.parse(text);
}

function buildPayload() {
  return {
    ...form,
    project_id: currentProjectId.value,
    folder_id: selectedFolderId.value,
    headers: rowsToMap(headerRows.value),
    params: rowsToMap(paramRows.value),
    body: parseBody(),
  };
}

function snapshotActiveTab() {
  if (!activeTabKey.value) {
    return;
  }
  const index = openedTabs.value.findIndex((item) => getTabKey(item) === activeTabKey.value);
  if (index === -1) {
    return;
  }
  openedTabs.value[index] = {
    ...openedTabs.value[index],
    ...form,
    project_id: currentProjectId.value ?? form.project_id,
    folder_id: selectedFolderId.value,
    headers: rowsToMap(headerRows.value),
    params: rowsToMap(paramRows.value),
    body: bodyText.value,
    tabKey: activeTabKey.value,
  } as ApiTemplate;
}

async function saveTemplate(showSuccess = true) {
  if (!currentProjectId.value) {
    ElMessage.warning("请先选择项目");
    return false;
  }
  if (!form.name.trim()) {
    ElMessage.warning("请输入接口名称");
    return false;
  }
  if (!form.url_path.trim()) {
    ElMessage.warning("请输入URL路径");
    return false;
  }
  try {
    parseBody();
  } catch (error) {
    activeEditorTab.value = "body";
    ElMessage.error(`请求体 JSON 格式不正确：${(error as Error).message}`);
    return false;
  }
  saving.value = true;
  try {
    const payload = buildPayload();
    const result = form.id
      ? await put<{ template: ApiTemplate }>(`/api/interface-auto/api-templates/${form.id}/`, payload)
      : await post<{ template: ApiTemplate }>("/api/interface-auto/api-templates/", payload);
    selectedTemplateId.value = result.template.id ?? null;
    delete modifiedTabs[activeTabKey.value];
    const currentKey = activeTabKey.value || getTabKey(result.template);
    const tabIndex = openedTabs.value.findIndex((item) => getTabKey(item) === currentKey);
    if (tabIndex === -1) {
      openedTabs.value.push({ ...result.template, tabKey: currentKey });
    } else {
      openedTabs.value[tabIndex] = { ...result.template, tabKey: currentKey };
    }
    activeTabKey.value = currentKey;
    delete modifiedTabs[activeTabKey.value];
    if (showSuccess) {
      ElMessage.success("接口模板已保存");
    }
    await loadWorkspace();
    return true;
  } catch (error) {
    ElMessage.error((error as Error).message);
    modifiedTabs[activeTabKey.value] = true;
    return false;
  } finally {
    saving.value = false;
  }
}

async function deleteTemplate() {
  if (!form.id) {
    createTemplate();
    return;
  }
  await ElMessageBox.confirm(`确定删除接口模板「${form.name}」吗？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
  });
  await del(`/api/interface-auto/api-templates/${form.id}/`);
  ElMessage.success("模板已删除");
  openedTabs.value = openedTabs.value.filter((item) => item.id !== form.id);
  selectedTemplateId.value = null;
  await loadWorkspace();
}

async function deleteFolder(folderId = selectedFolderId.value) {
  const folder = folders.value.find((item) => item.id === folderId) ?? null;
  if (folderId === null || !folder) {
    ElMessage.warning("请先选择目录");
    return;
  }
  await ElMessageBox.confirm(`确定删除目录「${folder.name}」及其下所有模板吗？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
  });
  await del(`/api/interface-auto/api-folders/${folderId}/`);
  ElMessage.success("目录已删除");
  selectedFolderId.value = null;
  selectedTemplateId.value = null;
  selectedNodeType.value = null;
  await loadWorkspace();
}

async function deleteTopFolder() {
  const folder = currentFolder.value;
  if (!folder) {
    ElMessage.warning("请先选择目录");
    return;
  }
  await deleteFolder(folder.id);
}

async function renameFolder() {
  if (!contextMenu.node || contextMenu.node.type !== "folder" || contextMenu.node.folderId === null) {
    return;
  }
  const folder = folders.value.find((item) => item.id === contextMenu.node?.folderId);
  if (!folder) {
    return;
  }
  const { value } = await ElMessageBox.prompt("请输入新的目录名称", "重命名目录", {
    inputValue: folder.name,
    confirmButtonText: "保存",
    cancelButtonText: "取消",
    inputValidator: (value) => Boolean(value.trim()) || "目录名称不能为空",
  });
  await put(`/api/interface-auto/api-folders/${folder.id}/`, {
    ...folder,
    name: value.trim(),
  });
  ElMessage.success("目录已重命名");
  hideContextMenu();
  await loadWorkspace();
}

async function copyTemplate(template?: ApiTemplate) {
  const source = template ?? form;
  if (!currentProjectId.value || !source.id) {
    return;
  }
  const payload = {
    ...source,
    id: undefined,
    name: `${source.name} - 副本`,
    project_id: currentProjectId.value,
  };
  const result = await post<{ template: ApiTemplate }>("/api/interface-auto/api-templates/", payload);
  ElMessage.success("模板已复制");
  hideContextMenu();
  await loadWorkspace();
  openTemplate(result.template);
}

function createTemplateInContextFolder() {
  if (contextMenu.node?.type === "folder") {
    selectedNodeType.value = "folder";
    selectedFolderId.value = contextMenu.node.folderId;
  }
  createTemplate();
  hideContextMenu();
}

function showContextMenu(event: MouseEvent, node: TreeNode) {
  event.preventDefault();
  contextMenu.visible = true;
  contextMenu.x = event.clientX;
  contextMenu.y = event.clientY;
  contextMenu.node = node;
}

function showTabContextMenu(event: MouseEvent, tabKey: string) {
  event.preventDefault();
  tabContextMenu.visible = true;
  tabContextMenu.x = event.clientX;
  tabContextMenu.y = event.clientY;
  tabContextMenu.tabKey = tabKey;
}

function hideContextMenu() {
  contextMenu.visible = false;
  contextMenu.node = null;
  tabContextMenu.visible = false;
  tabContextMenu.tabKey = "";
}

function findTreeNodeById(nodes: TreeNode[], id: string): TreeNode | null {
  for (const node of nodes) {
    if (node.id === id) {
      return node;
    }
    const found = node.children ? findTreeNodeById(node.children, id) : null;
    if (found) {
      return found;
    }
  }
  return null;
}

function canDropTreeNode(draggingNode: { data: TreeNode }, dropNode: { data: TreeNode }, dropType: "prev" | "inner" | "next") {
  if (draggingNode.data.type !== "template") {
    return false;
  }
  if (dropType === "inner") {
    return dropNode.data.type === "folder";
  }
  return true;
}

async function onTreeDrop(draggingNode: { data: TreeNode }, dropNode: { data: TreeNode }, dropType: "before" | "after" | "inner") {
  const dragged = draggingNode.data.template;
  if (!dragged?.id) {
    await loadWorkspace();
    return;
  }

  let targetFolderId: number | null = null;
  let insertIndex = 0;
  if (dropType === "inner") {
    targetFolderId = dropNode.data.folderId;
    insertIndex = templates.value.filter((item) => item.folder_id === targetFolderId).length;
  } else {
    targetFolderId = dropNode.data.type === "folder" ? dropNode.data.parentFolderId : dropNode.data.folderId;
    const siblings = templates.value
      .filter((item) => item.folder_id === targetFolderId && item.id !== dragged.id)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    const targetTemplateId =
      dropNode.data.type === "template"
        ? dropNode.data.template?.id
        : findTreeNodeById(treeData.value, dropNode.data.id)?.children?.find((item) => item.type === "template")?.template?.id;
    const targetIndex = siblings.findIndex((item) => item.id === targetTemplateId);
    insertIndex = targetIndex === -1 ? siblings.length : targetIndex + (dropType === "after" ? 1 : 0);
  }

  const duplicate = templates.value.some(
    (item) => item.id !== dragged.id && item.folder_id === targetFolderId && item.name.trim() === dragged.name.trim(),
  );
  if (duplicate) {
    ElMessage.warning("目标同级目录下已存在同名接口模板");
    await loadWorkspace();
    return;
  }

  const ordered = templates.value
    .filter((item) => item.folder_id === targetFolderId && item.id !== dragged.id)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  ordered.splice(Math.max(0, insertIndex), 0, { ...dragged, folder_id: targetFolderId });

  try {
    await Promise.all(
      ordered.map((item, index) =>
        put(`/api/interface-auto/api-templates/${item.id}/`, {
          ...item,
          folder_id: targetFolderId,
          sort_order: (index + 1) * 100,
        }),
      ),
    );
    selectedFolderId.value = targetFolderId;
    ElMessage.success("接口顺序已更新");
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    await loadWorkspace();
  }
}

async function deleteContextNode() {
  if (!contextMenu.node) {
    return;
  }
  if (contextMenu.node.type === "folder" && contextMenu.node.folderId !== null) {
    const folderId = contextMenu.node.folderId;
    hideContextMenu();
    await deleteFolder(folderId);
    return;
  }
  if (contextMenu.node.type === "template" && contextMenu.node.template) {
    openTemplate(contextMenu.node.template);
    hideContextMenu();
    await deleteTemplate();
  }
}

async function confirmUnsavedTab(tabKey: string) {
  if (!modifiedTabs[tabKey]) {
    return "ignore" as const;
  }
  return ElMessageBox.confirm(`标签页「${getTabTitle(tabKey)}」有未保存的修改，请选择操作。`, "保存确认", {
    distinguishCancelAndClose: true,
    confirmButtonText: "保存",
    cancelButtonText: "忽略",
    type: "warning",
  })
    .then(() => "save" as const)
    .catch((action: string) => (action === "cancel" ? ("ignore" as const) : ("abort" as const)));
}

function removeTabWithoutConfirm(tabKey: string) {
  delete modifiedTabs[tabKey];
  openedTabs.value = openedTabs.value.filter((item) => getTabKey(item) !== tabKey);
  if (activeTabKey.value === tabKey) {
    const next = openedTabs.value[0];
    if (next) {
      openTemplate(next);
    } else {
      selectedTemplateId.value = null;
      selectedNodeType.value = null;
      activeTabKey.value = "";
      resetForm(undefined);
    }
  }
}

async function closeTabsWithConfirm(tabKeys: string[]) {
  snapshotActiveTab();
  for (const tabKey of tabKeys) {
    const action = await confirmUnsavedTab(tabKey);
    if (action === "abort") {
      return false;
    }
    if (action === "save") {
      const target = openedTabs.value.find((item) => getTabKey(item) === tabKey);
      if (!target) {
        continue;
      }
      openTemplate(target);
      const saved = await saveTemplate(false);
      if (!saved) {
        return false;
      }
      removeTabWithoutConfirm(activeTabKey.value || tabKey);
      continue;
    }
    removeTabWithoutConfirm(tabKey);
  }
  return true;
}

function closeCurrentTab() {
  void closeTabsWithConfirm([tabContextMenu.tabKey]);
  hideContextMenu();
}

function closeOtherTabs() {
  const keepKey = tabContextMenu.tabKey;
  const closingKeys = openedTabs.value
    .filter((item) => getTabKey(item) !== keepKey)
    .map((item) => getTabKey(item));
  void closeTabsWithConfirm(closingKeys);
  hideContextMenu();
}

function closeAllTabs() {
  void closeTabsWithConfirm(openedTabs.value.map((item) => getTabKey(item)));
  hideContextMenu();
}

function markActiveModified() {
  if (resetting || !activeTabKey.value || !openedTabs.value.length) {
    return;
  }
  snapshotActiveTab();
  modifiedTabs[activeTabKey.value] = true;
}

function beautifyBody() {
  try {
    bodyText.value = JSON.stringify(JSON.parse(bodyText.value || "{}"), null, 2);
  } catch {
    ElMessage.warning("请求体不是标准 JSON，已保留原文本");
  }
}

function handleShortcut(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    if (openedTabs.value.length) {
      void saveTemplate();
    }
  }
}

function handleGlobalPointer() {
  hideContextMenu();
}

function debugTemplate() {
  responseText.value = JSON.stringify(
    {
      message: "调试引擎将在测试用例迁移阶段接入",
      request: buildPayload(),
    },
    null,
    2,
  );
}

function syncProjectPath() {
  const project = context.selectedProject.value;
  projectPath.value = project && project.business_group_id !== null ? [project.business_group_id, project.id] : [];
}

function handleProjectPathChange(value: number[]) {
  const [groupId, projectId] = value;
  context.setGroup(groupId);
  if (projectId !== undefined) {
    context.setProject(projectId);
    return;
  }
  context.setProject(null);
}

watch(currentProjectId, () => {
  syncProjectPath();
  selectedFolderId.value = null;
  selectedTemplateId.value = null;
  selectedNodeType.value = null;
  void loadWorkspace();
});

watch(form, markActiveModified, { deep: true });
watch(headerRows, markActiveModified, { deep: true });
watch(paramRows, markActiveModified, { deep: true });
watch(bodyText, markActiveModified);

onMounted(async () => {
  window.addEventListener("keydown", handleShortcut);
  window.addEventListener("click", handleGlobalPointer);
  window.addEventListener("contextmenu", handleGlobalPointer);
  await context.ensureLoaded();
  if (!context.selectedProject.value && context.projects.value.length) {
    context.setProject(context.projects.value[0].id);
  }
  syncProjectPath();
  await loadWorkspace();
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleShortcut);
  window.removeEventListener("click", handleGlobalPointer);
  window.removeEventListener("contextmenu", handleGlobalPointer);
});
</script>

<template>
  <div class="interface-auto-desktop" @click="hideContextMenu">
    <aside class="template-nav">
      <div class="project-line">
        <span>项目：</span>
        <el-cascader
          v-model="projectPath"
          :options="projectOptions"
          :props="cascaderProps"
          size="small"
          class="project-cascader"
          placeholder="选择业务 / 项目"
          :show-all-levels="true"
          @change="handleProjectPathChange"
        />
        <el-button size="small" class="icon-tool" title="新增一级目录" @click.stop="createFolder(null)">
          <el-icon><FolderAdd /></el-icon>
        </el-button>
        <el-button
          size="small"
          class="icon-tool delete-tool"
          :class="{ active: selectedNodeType === 'folder' && Boolean(currentFolder) }"
          :disabled="selectedNodeType !== 'folder' || !currentFolder"
          title="删除目录"
          @click.stop="deleteTopFolder"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <el-input v-model="searchText" size="small" placeholder="输入接口名和描述..." clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-tree
        class="api-tree"
        node-key="id"
        :data="treeData"
        :props="{ label: 'label', children: 'children' }"
        default-expand-all
        draggable
        :allow-drop="canDropTreeNode"
        highlight-current
        @node-click="onTreeClick"
        @node-drop="onTreeDrop"
      >
        <template #default="{ data }">
          <span class="tree-node" :class="data.type" @contextmenu.stop="showContextMenu($event, data)">
            <template v-if="data.method">
              <b class="method-badge" :class="String(data.method || 'GET').toLowerCase()">{{ data.method }}</b>
              <span class="tree-label">{{ data.label }}</span>
            </template>
            <template v-else>
              <el-icon class="tree-folder-icon"><Folder /></el-icon>
              <span class="tree-label">{{ data.label }}</span>
            </template>
          </span>
        </template>
      </el-tree>
    </aside>

    <div
      v-if="contextMenu.visible"
      class="tree-context-menu"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      @click.stop
    >
      <template v-if="contextMenu.node?.type === 'folder'">
        <button @click="createChildFolder">新增子目录</button>
        <button @click="createTemplateInContextFolder">新增接口模板</button>
        <button @click="renameFolder">重命名目录</button>
        <button class="danger" @click="deleteContextNode">删除目录</button>
      </template>
      <template v-else>
        <button @click="copyTemplate(contextMenu.node?.template)">复制</button>
        <button class="danger" @click="deleteContextNode">删除</button>
      </template>
    </div>

    <div
      v-if="tabContextMenu.visible"
      class="tree-context-menu tab-menu"
      :style="{ left: `${tabContextMenu.x}px`, top: `${tabContextMenu.y}px` }"
      @click.stop
    >
      <button @click="closeCurrentTab">关闭当前</button>
      <button @click="closeOtherTabs">关闭其他</button>
      <button @click="closeAllTabs">关闭全部</button>
    </div>

    <main class="editor-shell" v-loading="loading">
      <div class="opened-tabs">
        <el-tag
          v-for="item in openedTabs"
          :key="getTabKey(item)"
          closable
          type="primary"
          :effect="activeTabKey === getTabKey(item) ? 'light' : 'plain'"
          class="open-tag"
          :class="{ inactive: activeTabKey !== getTabKey(item), modified: modifiedTabs[getTabKey(item)] }"
          @click="changeOpenedTab(getTabKey(item))"
          @close="closeOpenedTab(getTabKey(item))"
          @contextmenu.stop="showTabContextMenu($event, getTabKey(item))"
        >
          {{ getTabTitle(getTabKey(item)) }}
        </el-tag>
      </div>

      <section v-if="openedTabs.length" class="editor-main">
        <div class="field-row name-row">
          <label>接口名称</label>
          <el-input v-model="form.name" class="template-name-input" size="small" placeholder="请输入接口名称" />
        </div>

        <div class="field-row desc-row">
          <label>接口描述</label>
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入接口描述" />
        </div>

        <div class="field-row request-row">
          <label>请求方法</label>
          <el-select v-model="form.method" size="small" class="method-select">
            <el-option v-for="method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']" :key="method" :label="method" :value="method" />
          </el-select>
          <label class="url-label">URL:</label>
          <el-input v-model="form.url_path" size="small" class="url-input" placeholder="http:// 或 /api/path" />
        </div>

        <el-tabs v-model="activeEditorTab" class="request-tabs">
          <el-tab-pane label="请求头" name="headers">
            <div class="kv-table">
              <div v-for="row in headerRows" :key="row.id" class="kv-row">
                <el-input v-model="row.key" size="small" placeholder="Header名称" />
                <el-input v-model="row.value" size="small" placeholder="Header值" />
                <button class="row-icon add" @click="addHeaderRow">+</button>
                <button class="row-icon remove" @click="removeHeaderRow(row.id)">−</button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="参数" name="params">
            <div class="kv-table">
              <div v-for="row in paramRows" :key="row.id" class="kv-row">
                <el-input v-model="row.key" size="small" placeholder="参数名" />
                <el-input v-model="row.value" size="small" placeholder="参数值" />
                <button class="row-icon add" @click="addParamRow">+</button>
                <button class="row-icon remove" @click="removeParamRow(row.id)">−</button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="请求体" name="body">
            <div class="body-editor-wrap">
              <el-button class="beautify-icon" size="small" text title="格式化JSON" @click="beautifyBody">
                <el-icon><MagicStick /></el-icon>
              </el-button>
              <el-input
                v-model="bodyText"
                class="code-editor"
                type="textarea"
                :rows="13"
                placeholder='请输入JSON格式的请求体，例如：{"key":"value"}'
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="配置" name="config">
            <div class="config-grid">
              <div class="field-row inline">
                <label>超时(秒)</label>
                <el-input-number v-model="form.timeout" size="small" :min="1" :max="600" controls-position="right" />
              </div>
              <div class="field-row inline">
                <label>启用重试</label>
                <el-switch v-model="form.retry_enabled" />
              </div>
              <div class="field-row inline">
                <label>重试次数</label>
                <el-input-number v-model="form.retry_count" size="small" :min="0" :max="20" :disabled="!form.retry_enabled" controls-position="right" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <section class="response-panel">
          <div class="response-title">响应</div>
          <pre>{{ responseText }}</pre>
        </section>

        <div class="bottom-actions">
          <el-button size="small" type="success" @click="debugTemplate">调试</el-button>
          <el-button size="small" type="success" :loading="saving" @click="saveTemplate">保存</el-button>
        </div>
      </section>
      <section v-else class="empty-editor">
        <span>请选择接口</span>
      </section>
    </main>
  </div>
</template>

<style scoped>
.interface-auto-desktop {
  display: grid;
  grid-template-columns: 336px minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #f4f8fc;
}

.template-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-right: 1px solid #dbe3ec;
  padding: 8px;
  background: #fff;
}

.project-line {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2f4054;
  font-size: 12px;
  white-space: nowrap;
}

.project-cascader {
  width: 168px;
}

.icon-tool {
  width: 26px;
  padding: 5px 0 !important;
}

.delete-tool.active {
  border-color: #ffccc7;
  color: #cf1322;
}

.delete-tool.active:hover {
  border-color: #ff7875;
  background: #fff1f0;
  color: #a8071a;
}

.api-tree {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid #dfe7ef;
  background: #fff;
}

.tree-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 0;
  height: 24px;
  padding-right: 6px;
  color: #1f2937;
  font-size: 13px;
}

.tree-node.template {
  padding-left: 2px;
}

.tree-folder-icon {
  color: #3d7ee8;
}

.tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  height: 18px;
  border-radius: 6px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  text-transform: uppercase;
}

.method-badge.get {
  background: #ecf5ff;
  color: #2f7df6;
}

.method-badge.post {
  background: #fff0dc;
  color: #d26f00;
}

.method-badge.delete {
  background: #fff1f0;
  color: #cf1322;
}

.method-badge.put {
  background: #f0f9eb;
  color: #4a9f2e;
}

.method-badge.patch {
  background: #f4edff;
  color: #7c3aed;
}

.tree-context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 132px;
  border: 1px solid #cfd8e3;
  box-shadow: 0 8px 20px rgb(15 23 42 / 14%);
  padding: 4px;
  background: #fff;
}

.tree-context-menu button {
  display: block;
  width: 100%;
  border: 0;
  padding: 7px 10px;
  background: transparent;
  color: #263445;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.tree-context-menu button:hover {
  background: #eef6ff;
  color: #1677ff;
}

.tree-context-menu button.danger:hover {
  background: #fff1f0;
  color: #cf1322;
}

.editor-shell {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-left: 4px solid #edf2f7;
  background: #fff;
}

.opened-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  margin: 8px 12px 0;
  border: 1px solid #dce8f5;
  border-radius: 6px;
  padding: 0 10px;
  overflow-x: auto;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fd 100%);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 80%);
}

.open-tag {
  flex: 0 0 auto;
  height: 27px;
  border-radius: 4px;
  padding: 0 9px;
  cursor: pointer;
  transition: border-color 0.16s ease, background-color 0.16s ease, box-shadow 0.16s ease, color 0.16s ease;
  user-select: none;
}

.open-tag.inactive {
  border-color: transparent;
  background: rgb(255 255 255 / 64%);
  color: #4f6277;
}

.open-tag.inactive:hover {
  background: #eef6ff;
  color: #1677ff;
}

.open-tag:not(.inactive) {
  border-color: #bcd7ff;
  background: #edf5ff;
  color: #1677ff;
  box-shadow: 0 4px 12px rgb(22 119 255 / 10%);
}

.open-tag.modified {
  border-color: #bcd7ff;
  color: #1677ff;
}

.open-tag.modified.inactive {
  border-color: #d6e4ff;
  background: #f7fbff;
  color: #6b85a3;
}

.open-tag.modified:not(.inactive) {
  border-color: #7fb0ff;
  background: #e7f1ff;
  color: #145ecc;
  box-shadow: 0 0 0 1px rgb(64 158 255 / 18%), 0 4px 12px rgb(22 119 255 / 12%);
}

.editor-main {
  display: flex;
  position: relative;
  flex-direction: column;
  gap: 10px;
  height: calc(100% - 52px);
  padding: 10px 12px 48px;
  overflow: hidden;
}

.empty-editor {
  display: grid;
  height: calc(100% - 41px);
  place-items: center;
  color: #8a96a8;
  font-size: 16px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-row label {
  flex: 0 0 64px;
  color: #344054;
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
}

.name-row .el-input {
  max-width: 690px;
}

.desc-row {
  align-items: flex-start;
}

.desc-row .el-textarea {
  max-width: 690px;
}

.request-row {
  max-width: 990px;
}

.method-select {
  width: 150px;
}

.url-label {
  flex: 0 0 auto !important;
  width: auto;
}

.url-input {
  flex: 1;
}

.request-tabs {
  flex: 0 0 380px;
  min-height: 0;
  border: 1px solid #dbe3ec;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
}

.request-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: #f6f9fc;
}

.request-tabs :deep(.el-tabs__nav-wrap) {
  padding-left: 4px;
}

.request-tabs :deep(.el-tabs__item) {
  height: 36px;
  padding: 0 24px;
  font-size: 13px;
}

.request-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 700;
}

.request-tabs :deep(.el-tabs__content) {
  height: 342px;
  padding: 10px;
  overflow: auto;
}

.kv-table {
  display: grid;
  gap: 8px;
  padding: 4px 2px;
}

.kv-row {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(260px, 1fr) 18px 18px;
  gap: 8px;
  align-items: center;
}

.row-icon {
  border: 0;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.row-icon.add {
  color: #2bb673;
}

.row-icon.remove {
  color: #d93025;
}

.code-editor :deep(textarea) {
  height: 310px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.7;
}

.body-editor-wrap {
  position: relative;
  overflow: hidden;
  border: 1px solid #d7e2ee;
  border-radius: 6px;
  background: #fff;
}

.beautify-icon {
  position: absolute;
  top: 6px;
  right: 8px;
  z-index: 2;
  color: #1677ff;
}

.body-editor-wrap :deep(.el-textarea__inner) {
  border: 0;
  box-shadow: none;
}

.config-grid {
  display: grid;
  gap: 12px;
  align-content: start;
  justify-items: start;
}

.field-row.inline label {
  flex-basis: auto;
}

.response-panel {
  flex: 1;
  min-height: 180px;
  overflow: hidden;
  border: 0;
  background: transparent;
}

.response-title {
  height: 28px;
  padding: 5px 8px;
  color: #1f2937;
  font-size: 13px;
  font-weight: 700;
}

.response-panel pre {
  height: calc(100% - 32px);
  margin: 0;
  border: 1px solid #dbe3ec;
  border-radius: 6px;
  padding: 8px;
  overflow: auto;
  background: #fff;
  color: #667085;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.bottom-actions {
  display: flex;
  position: absolute;
  right: 12px;
  bottom: 10px;
  gap: 6px;
  justify-content: flex-end;
}

:deep(.el-button--small) {
  min-height: 24px;
  padding: 5px 10px;
  font-size: 12px;
}

:deep(.el-input--small .el-input__wrapper) {
  min-height: 28px;
}

:deep(.el-textarea__inner) {
  font-size: 13px;
}

@media (max-width: 1100px) {
  .interface-auto-desktop {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .kv-row {
    grid-template-columns: 1fr 1fr 18px 18px;
  }
}
</style>
