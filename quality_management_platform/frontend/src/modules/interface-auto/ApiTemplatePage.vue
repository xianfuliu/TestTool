<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import { Delete, Folder, FolderAdd, MagicStick, RefreshRight, Search } from "@element-plus/icons-vue";

import { del, get, post, put } from "@/shared/api/client";
import { useBusinessProjectContext } from "@/shared/composables/useBusinessProjectContext";
import type { ApiFolder, ApiTemplate, CascaderOption, JsonMap, KeyValueRow, TemplateDebugConfig, TreeNode, WorkspacePayload } from "./types";

const context = useBusinessProjectContext();
const route = useRoute();
const router = useRouter();
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

function getFolderDepth(folderId: number | null | undefined): number {
  if (folderId === null || folderId === undefined) {
    return 0;
  }
  let depth = 0;
  let current = folders.value.find((item) => item.id === folderId) ?? null;
  while (current) {
    depth += 1;
    current = current.parent_id ? folders.value.find((item) => item.id === current?.parent_id) ?? null : null;
  }
  return depth;
}

function canCreateChildFolder(folderId: number | null | undefined): boolean {
  return getFolderDepth(folderId) < 3;
}

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
    id: undefined,
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
    debug_config: createDefaultDebugConfig(),
    sort_order: 0,
  };
}

function rowId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function mapToRows(value: JsonMap | undefined) {
  return Object.entries(value ?? {}).map(([key, rowValue]) => ({ id: rowId(), key, value: String(rowValue) }));
}

function createDefaultDebugConfig(): TemplateDebugConfig {
  return {
    encryption: {
      enabled: false,
      encrypt_url: "",
      decrypt_url: "",
    },
    login_request: {
      enabled: false,
      protocol: "http",
      method: "POST",
      url: "",
      headers_rows: [{ rowKey: rowId(), key: "Content-Type", value: "application/json" }],
      body_text: "{}",
      extractions: [{ rowKey: rowId(), variable: "", path: "" }],
    },
  };
}

function normalizeDebugConfig(value: ApiTemplate["debug_config"] | undefined): TemplateDebugConfig {
  const fallback = createDefaultDebugConfig();
  return {
    encryption: {
      enabled: Boolean(value?.encryption?.enabled),
      encrypt_url: value?.encryption?.encrypt_url ?? "",
      decrypt_url: value?.encryption?.decrypt_url ?? "",
    },
    login_request: {
      enabled: Boolean(value?.login_request?.enabled),
      protocol: value?.login_request?.protocol ?? fallback.login_request.protocol,
      method: value?.login_request?.method ?? fallback.login_request.method,
      url: value?.login_request?.url ?? "",
      headers_rows: mapToRows(
        rowsToMap((value?.login_request?.headers_rows as unknown as KeyValueRow[]) ?? []),
      ) as unknown as TemplateDebugConfig["login_request"]["headers_rows"],
      body_text: stringifyBody(value?.login_request?.body_text ?? "{}"),
      extractions:
        Array.isArray(value?.login_request?.extractions) && value.login_request.extractions.length
          ? value.login_request.extractions.map((row) => ({
              rowKey: row.rowKey || rowId(),
              variable: row.variable ?? "",
              path: row.path ?? "",
            }))
          : fallback.login_request.extractions,
    },
  };
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
    id: next.id ?? undefined,
    tabKey: next.tabKey,
    ...next,
    headers: next.headers ?? {},
    params: next.params ?? {},
    body: next.body ?? {},
    timeout: next.timeout ?? 30,
    retry_enabled: Boolean(next.retry_enabled),
    retry_count: next.retry_count ?? 3,
    debug_config: normalizeDebugConfig(next.debug_config),
  });
  headerRows.value = mapToRows(form.headers);
  paramRows.value = mapToRows(form.params);
  if (!headerRows.value.length) {
    addHeaderRow();
  }
  if (!paramRows.value.length) {
    addParamRow();
  }
  if (!form.debug_config?.login_request.headers_rows.length) {
    form.debug_config!.login_request.headers_rows = [
      { rowKey: rowId(), key: "Content-Type", value: "application/json" },
    ];
  }
  if (!form.debug_config?.login_request.extractions.length) {
    form.debug_config!.login_request.extractions = [{ rowKey: rowId(), variable: "", path: "" }];
  }
  bodyText.value = stringifyBody(form.body);
  nextTick(() => {
    resetting = false;
  });
}

function getRouteTemplateId() {
  const rawValue = Array.isArray(route.query.openTemplateId) ? route.query.openTemplateId[0] : route.query.openTemplateId;
  const templateId = Number(rawValue);
  return Number.isFinite(templateId) && templateId > 0 ? templateId : null;
}

async function clearRouteTemplateQuery() {
  if (!("openTemplateId" in route.query)) {
    return;
  }
  const nextQuery = { ...route.query };
  delete nextQuery.openTemplateId;
  await router.replace({
    name: "interface-auto-templates",
    query: nextQuery,
  });
}

async function openTemplateFromRouteQuery() {
  const templateId = getRouteTemplateId();
  if (!templateId) {
    return;
  }
  const target = templates.value.find((item) => item.id === templateId);
  if (!target) {
    return;
  }
  openTemplate(target);
  await clearRouteTemplateQuery();
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
    await openTemplateFromRouteQuery();
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function refreshWorkspace() {
  hideContextMenu();
  await loadWorkspace();
}

function onTreeClick(node: TreeNode) {
  hideContextMenu();
  selectedNodeType.value = node.type;
  selectedFolderId.value = node.folderId;
  if (node.type === "template" && node.template) {
    openTemplateFromTree(node.template);
    return;
  }
  if (activeTabKey.value && openedTabs.value.length) {
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

function activateAdjacentTab(closedTabKey: string) {
  const closingIndex = openedTabs.value.findIndex((item) => getTabKey(item) === closedTabKey);
  const fallbackTab =
    closingIndex === -1
      ? null
      : openedTabs.value[closingIndex + 1] ?? openedTabs.value[closingIndex - 1] ?? null;

  openedTabs.value = openedTabs.value.filter((item) => getTabKey(item) !== closedTabKey);
  delete modifiedTabs[closedTabKey];

  if (fallbackTab) {
    openTemplate(fallbackTab);
    return;
  }

  selectedTemplateId.value = null;
  selectedNodeType.value = null;
  activeTabKey.value = "";
  resetForm(undefined);
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
  if (!canCreateChildFolder(contextMenu.node.folderId)) {
    ElMessage.warning("目录最多支持 3 层");
    hideContextMenu();
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

function addLoginHeaderRow() {
  form.debug_config!.login_request.headers_rows.push({ rowKey: rowId(), key: "", value: "" });
}

function removeLoginHeaderRow(index: number) {
  form.debug_config!.login_request.headers_rows.splice(index, 1);
  if (!form.debug_config!.login_request.headers_rows.length) {
    addLoginHeaderRow();
  }
}

function addLoginExtractionRow() {
  form.debug_config!.login_request.extractions.push({ rowKey: rowId(), variable: "", path: "" });
}

function removeLoginExtractionRow(index: number) {
  form.debug_config!.login_request.extractions.splice(index, 1);
  if (!form.debug_config!.login_request.extractions.length) {
    addLoginExtractionRow();
  }
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
    project_id: currentProjectId.value,
    folder_id: selectedFolderId.value,
    name: form.name,
    method: form.method,
    url_path: form.url_path,
    headers: rowsToMap(headerRows.value),
    params: rowsToMap(paramRows.value),
    body: parseBody(),
    description: form.description,
    timeout: form.timeout,
    retry_enabled: form.retry_enabled,
    retry_count: form.retry_count,
    debug_config: {
      encryption: {
        enabled: Boolean(form.debug_config?.encryption?.enabled),
        encrypt_url: form.debug_config?.encryption?.encrypt_url ?? "",
        decrypt_url: form.debug_config?.encryption?.decrypt_url ?? "",
      },
      login_request: {
        enabled: Boolean(form.debug_config?.login_request?.enabled),
        protocol: form.debug_config?.login_request?.protocol ?? "http",
        method: form.debug_config?.login_request?.method ?? "POST",
        url: form.debug_config?.login_request?.url ?? "",
        headers: rowsToMap((form.debug_config?.login_request?.headers_rows as unknown as KeyValueRow[]) ?? []),
        body: (() => {
          const text = (form.debug_config?.login_request?.body_text ?? "").trim();
          if (!text) {
            return {};
          }
          try {
            return JSON.parse(text);
          } catch {
            return text;
          }
        })(),
        extractions: (form.debug_config?.login_request?.extractions ?? [])
          .map((row) => ({
            variable: row.variable.trim(),
            path: row.path.trim(),
          }))
          .filter((row) => row.variable || row.path),
      },
    },
    sort_order: form.sort_order,
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
    debug_config: {
      encryption: {
        enabled: Boolean(form.debug_config?.encryption?.enabled),
        encrypt_url: form.debug_config?.encryption?.encrypt_url ?? "",
        decrypt_url: form.debug_config?.encryption?.decrypt_url ?? "",
      },
      login_request: {
        enabled: Boolean(form.debug_config?.login_request?.enabled),
        protocol: form.debug_config?.login_request?.protocol ?? "http",
        method: form.debug_config?.login_request?.method ?? "POST",
        url: form.debug_config?.login_request?.url ?? "",
        headers_rows: (form.debug_config?.login_request?.headers_rows ?? []).map((row) => ({
          key: row.key,
          value: row.value,
        })),
        body_text: form.debug_config?.login_request?.body_text ?? "{}",
        extractions: (form.debug_config?.login_request?.extractions ?? []).map((row) => ({
          rowKey: row.rowKey,
          variable: row.variable,
          path: row.path,
        })),
      },
    },
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
  const deletingTabKey = activeTabKey.value || getTabKey(form);
  await ElMessageBox.confirm(`确定删除接口模板「${form.name}」吗？`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
  });
  await del(`/api/interface-auto/api-templates/${form.id}/`);
  ElMessage.success("模板已删除");
  activateAdjacentTab(deletingTabKey);
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

function handleGlobalPointer() {
  hideContextMenu();
}

function handleSaveShortcut() {
  if (route.name !== "interface-auto-templates") {
    return;
  }
  if (openedTabs.value.length) {
    void saveTemplate();
  }
}

function debugTemplate() {
  void runTemplateDebug();
  return;
  responseText.value = JSON.stringify(
    {
      message: "调试引擎将在测试用例迁移阶段接入",
      request: buildPayload(),
    },
    null,
    2,
  );
}

async function runTemplateDebug() {
  try {
    const result = await post<Record<string, unknown>>("/api/interface-auto/api-templates/debug/", buildPayload());
    responseText.value = JSON.stringify(result, null, 2);
  } catch (error) {
    responseText.value = JSON.stringify({ error: (error as Error).message, request: buildPayload() }, null, 2);
    ElMessage.error((error as Error).message);
  }
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
watch(
  () => route.query.openTemplateId,
  () => {
    if (templates.value.length) {
      void openTemplateFromRouteQuery();
    }
  },
);

watch(form, markActiveModified, { deep: true });
watch(headerRows, markActiveModified, { deep: true });
watch(paramRows, markActiveModified, { deep: true });
watch(bodyText, markActiveModified);

onMounted(async () => {
  window.addEventListener("click", handleGlobalPointer);
  window.addEventListener("contextmenu", handleGlobalPointer);
  window.addEventListener("interface-auto:save-templates", handleSaveShortcut as EventListener);
  await context.ensureLoaded();
  if (!context.selectedProject.value && context.projects.value.length) {
    context.setProject(context.projects.value[0].id);
  }
  syncProjectPath();
  await loadWorkspace();
});

onBeforeUnmount(() => {
  window.removeEventListener("click", handleGlobalPointer);
  window.removeEventListener("contextmenu", handleGlobalPointer);
  window.removeEventListener("interface-auto:save-templates", handleSaveShortcut as EventListener);
});
</script>

<template>
  <div class="interface-auto-desktop" @click="hideContextMenu">
    <aside class="template-nav">
      <div class="project-toolbar">
        <span class="toolbar-label">项目：</span>
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
        <button class="icon-button" title="新建目录" @click.stop="createFolder(null)">
          <el-icon><FolderAdd /></el-icon>
        </button>
        <button
          class="icon-button"
          :class="{ disabled: selectedNodeType !== 'folder' || !currentFolder }"
          :disabled="selectedNodeType !== 'folder' || !currentFolder"
          title="删除目录"
          @click.stop="deleteTopFolder"
        >
          <el-icon><Delete /></el-icon>
        </button>
        <button class="icon-button" title="刷新" @click.stop="refreshWorkspace">
          <el-icon><RefreshRight /></el-icon>
        </button>
        <button class="icon-button" title="新增接口" @click.stop="createTemplate">+</button>
      </div>

      <div class="search-line">
        <el-icon><Search /></el-icon>
        <input v-model="searchText" class="search-input" placeholder="输入接口名称或描述..." />
      </div>

      <el-tree
        class="api-tree"
        node-key="id"
        :current-node-key="selectedTemplateId ? `template-${selectedTemplateId}` : undefined"
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
        <button v-if="canCreateChildFolder(contextMenu.node.folderId)" @click="createChildFolder(); hideContextMenu()">新增子目录</button>
        <button @click="createTemplateInContextFolder(); hideContextMenu()">新增接口模板</button>
        <button @click="renameFolder(); hideContextMenu()">重命名目录</button>
        <button class="danger" @click="deleteContextNode(); hideContextMenu()">删除目录</button>
      </template>
      <template v-else>
        <button @click="copyTemplate(contextMenu.node?.template); hideContextMenu()">复制</button>
        <button class="danger" @click="deleteContextNode(); hideContextMenu()">删除</button>
      </template>
    </div>

    <div
      v-if="tabContextMenu.visible"
      class="tree-context-menu tab-menu"
      :style="{ left: `${tabContextMenu.x}px`, top: `${tabContextMenu.y}px` }"
      @click.stop
    >
      <button @click="closeCurrentTab(); hideContextMenu()">关闭当前</button>
      <button @click="closeOtherTabs(); hideContextMenu()">关闭其他</button>
      <button @click="closeAllTabs(); hideContextMenu()">关闭全部</button>
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
          <el-tab-pane label="调试" name="debug">
            <div class="global-config-panel inline-panel">
              <div class="global-config-content">
                <div class="global-config-tab-panel global-config-stack">
                  <div class="global-config-hint">调试按钮执行时，如果配置了登录态获取，会先登录提取变量，再替换请求头中的占位符后发起接口请求。</div>

                  <div class="global-config-section-card">
                    <div class="global-config-toolbar align-left">
                      <label class="encryption-check compact-check">
                        <input v-model="form.debug_config!.encryption.enabled" type="checkbox" />
                        <span class="global-config-section-title">加解密配置</span>
                      </label>
                    </div>
                    <div v-if="form.debug_config?.encryption.enabled" class="global-config-section-panel">
                      <div class="global-config-form-row encryption-config-row">
                        <span class="global-config-row-label">加密URL</span>
                        <input v-model="form.debug_config!.encryption.encrypt_url" class="text-field global-config-row-control" placeholder="请输入加密URL" />
                        <span class="global-config-row-label compact">解密URL</span>
                        <input v-model="form.debug_config!.encryption.decrypt_url" class="text-field global-config-row-control" placeholder="请输入解密URL" />
                      </div>
                    </div>
                  </div>
                  
                  <div class="global-config-section-card">
                    <div class="global-config-toolbar align-left">
                      <label class="encryption-check compact-check">
                        <input v-model="form.debug_config!.login_request.enabled" type="checkbox" />
                        <span class="global-config-section-title">登录态获取</span>
                      </label>
                    </div>
                    <div v-if="form.debug_config?.login_request.enabled" class="global-config-section-panel">
                      <div class="global-config-stack">
                        <div class="global-config-form-row">
                          <span class="global-config-row-label">请求方式</span>
                          <el-select v-model="form.debug_config!.login_request.method" class="env-select global-config-row-control global-config-method-control" size="small">
                            <el-option v-for="method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']" :key="method" :label="method" :value="method" />
                          </el-select>
                          <span class="global-config-row-label compact">URL</span>
                          <input v-model="form.debug_config!.login_request.url" class="text-field global-config-row-control" placeholder="请输入登录 URL" />
                        </div>

                        <div class="global-config-form-row global-config-form-row-top">
                          <span class="global-config-row-label">请求头</span>
                          <div class="global-config-row-block">
                            <div class="global-config-list-content">
                              <div
                                v-for="(row, index) in form.debug_config.login_request.headers_rows"
                                :key="row.rowKey || `login-header-${index}`"
                                class="global-config-kv-row"
                              >
                                <input v-model="row.key" class="tool-input config-input" placeholder="Header Name" />
                                <input v-model="row.value" class="tool-input config-input" placeholder="Header Value" />
                                <div class="global-config-row-actions">
                                  <button class="row-icon add" type="button" @click="addLoginHeaderRow">+</button>
                                  <button class="row-icon remove" type="button" @click="removeLoginHeaderRow(index)">-</button>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div class="global-config-form-row global-config-form-row-top">
                          <span class="global-config-row-label">请求体</span>
                          <div class="global-config-row-block">
                            <el-input v-model="form.debug_config.login_request.body_text" type="textarea" :rows="4" resize="none" />
                          </div>
                        </div>

                        <div class="global-config-form-row global-config-form-row-top">
                          <span class="global-config-row-label">参数提取</span>
                          <div class="global-config-row-block">
                            <div class="global-config-list-content">
                              <div
                                v-for="(row, index) in form.debug_config.login_request.extractions"
                                :key="row.rowKey || `login-extraction-${index}`"
                                class="global-config-kv-row"
                              >
                                <input v-model="row.variable" class="tool-input config-input" placeholder="token" />
                                <input v-model="row.path" class="tool-input config-input" placeholder="headers.Authorization or body.data.token" />
                                <div class="global-config-row-actions">
                                  <button class="row-icon add" type="button" @click="addLoginExtractionRow">+</button>
                                  <button class="row-icon remove" type="button" @click="removeLoginExtractionRow(index)">-</button>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="请求头" name="headers">
            <div class="kv-table">
              <div v-for="row in headerRows" :key="row.id" class="kv-row">
                <el-input v-model="row.key" size="small" placeholder="Header名称" />
                <el-input v-model="row.value" size="small" placeholder="Header值，可使用 ${token}" />
                <button class="row-icon add" @click="addHeaderRow">+</button>
                <button class="row-icon remove" @click="removeHeaderRow(row.id)">-</button>
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
  gap: 0;
  border-right: 1px solid #dbe3ec;
  padding: 8px;
  background: #fff;
}

.project-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  margin-bottom: 6px;
  color: #2d3a4b;
  font-size: 12px;
}

.project-toolbar > span:first-child,
.toolbar-label {
  flex: 0 0 auto;
  font-weight: 600;
}

.project-cascader {
  width: 160px;
}

.icon-tool,
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid #ccd7e3;
  border-radius: 4px;
  padding: 0;
  background: #fff;
  color: #506176;
  cursor: pointer;
}

.icon-tool {
  padding: 0 !important;
}

.icon-tool:disabled,
.icon-button:disabled,
.icon-button.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.search-line {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  margin-bottom: 4px;
  color: #4d5d71;
}

.search-input {
  width: 100%;
  height: 28px;
  border: 1px solid #d7e1ec;
  border-radius: 6px;
  padding: 0 10px;
  box-sizing: border-box;
  color: #2d3a4b;
  outline: none;
}

.search-input:focus {
  border-color: #75a7ff;
}

.template-nav > .el-input {
  display: none;
}

.delete-tool.active {
  border-color: #ccd7e3;
  color: #506176;
}

.delete-tool.active:hover {
  border-color: #ccd7e3;
  background: #fff;
  color: #506176;
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
  background: #e8faf6;
  color: #0f8a6c;
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

.global-config-shell {
  margin-bottom: 12px;
  border: 1px solid #dbe3ec;
  border-radius: 10px;
  background: #fff;
}

.global-config-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: 0;
  padding: 10px 12px;
  background: transparent;
  color: #1f2937;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.global-config-toggle-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  transform: rotate(0deg);
  transition: transform 0.2s ease;
}

.global-config-toggle-icon.expanded {
  transform: rotate(90deg);
}

.global-config-panel {
  padding: 12px;
}

.global-config-content,
.global-config-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.global-config-tab-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.global-config-hint {
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.global-config-section-card {
  border: 1px solid #e5eaf1;
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}

.global-config-toolbar.align-left {
  justify-content: flex-start;
}

.global-config-toolbar {
  display: flex;
  align-items: center;
}

.encryption-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #334155;
  font-size: 13px;
}

.compact-check {
  font-weight: 600;
}

.global-config-section-panel {
  margin-top: 12px;
}

.global-config-form-row {
  display: grid;
  grid-template-columns: 88px minmax(180px, 240px) 52px minmax(0, 1fr);
  gap: 10px 12px;
  align-items: center;
}

.encryption-config-row {
  grid-template-columns: 88px minmax(0, 1fr) 88px minmax(0, 1fr);
}

.global-config-form-row-top {
  align-items: start;
}

.global-config-row-label {
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  line-height: 32px;
}

.global-config-row-label.compact {
  text-align: right;
}

.global-config-row-control {
  width: 100%;
}

.global-config-method-control {
  min-width: 0;
}

.global-config-row-block {
  grid-column: 2 / 5;
  min-width: 0;
}

.global-config-inline-grid {
  display: grid;
  gap: 12px;
}

.global-config-inline-grid.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.global-config-inline-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.global-config-inline-label,
.global-config-section-title {
  color: #334155;
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 960px) {
  .global-config-form-row {
    grid-template-columns: 88px minmax(0, 1fr);
  }

  .global-config-row-label.compact {
    text-align: left;
  }

  .global-config-row-block,
  .global-config-form-row > .global-config-row-control:nth-child(4) {
    grid-column: 2;
  }
}

.global-config-kv-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.global-config-list-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.global-config-row-actions {
  display: inline-flex;
  gap: 6px;
}

.tool-input.config-input,
.global-config-inline-field .text-field,
.text-field.global-config-row-control {
  width: 100%;
  min-height: 32px;
  border: 1px solid #d7e1ec;
  border-radius: 8px;
  padding: 0 10px;
  box-sizing: border-box;
  color: #1f2937;
  background: #fff;
  outline: none;
}

.tool-input.config-input:focus,
.global-config-inline-field .text-field:focus,
.text-field.global-config-row-control:focus {
  border-color: #7aa2f7;
}

.tool-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid #d7e1ec;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.tool-action.danger {
  color: #dc2626;
}

:deep(.el-button--small) {
  min-height: 24px;
  padding: 5px 10px;
  font-size: 12px;
}

:deep(.el-input--small .el-input__wrapper) {
  min-height: var(--qm-form-control-height-sm);
}

:deep(.el-textarea__inner) {
  font-family: var(--qm-form-font-family);
  font-size: var(--qm-form-font-size);
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
