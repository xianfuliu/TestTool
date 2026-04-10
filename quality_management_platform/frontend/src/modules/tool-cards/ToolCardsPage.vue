<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { CirclePlus, Delete, Edit, FolderAdd } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  copyToolCard,
  createToolCardFolder,
  deleteToolCard,
  deleteToolCardFolder,
  executeToolCard,
  fetchToolCardFolderDetail,
  fetchToolCardFolders,
  fetchToolCardsBootstrap,
  updateToolCardFolder,
} from "./api";
import ToolCardConfigDialog from "./components/ToolCardConfigDialog.vue";
import ToolCardWidget from "./components/ToolCardWidget.vue";
import type { ToolCard, ToolCardExecutionResult, ToolCardFolder } from "./types";

type TreeNode = ToolCardFolder & {
  children: TreeNode[];
};

const treeRef = ref();
const loading = ref(false);
const folders = ref<ToolCardFolder[]>([]);
const cards = ref<ToolCard[]>([]);
const currentFolderId = ref<number | null>(null);
const folderKeyword = ref("");
const configDialogVisible = ref(false);
const editingCard = ref<ToolCard | null>(null);
const executionDialogVisible = ref(false);
const executionResult = ref<ToolCardExecutionResult | null>(null);

const contextMenu = reactive<{
  visible: boolean;
  x: number;
  y: number;
  folder: ToolCardFolder | null;
}>({
  visible: false,
  x: 0,
  y: 0,
  folder: null,
});

function buildTree(parentId: number | null): TreeNode[] {
  return folders.value
    .filter((folder) => (folder.parent_id ?? null) === parentId)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
    .map<TreeNode>((folder) => ({
      ...folder,
      children: buildTree(folder.id),
    }));
}

const folderTreeData = computed<TreeNode[]>(() => buildTree(null));

const currentFolder = computed(() =>
  folders.value.find((folder) => folder.id === currentFolderId.value) ?? null,
);

const formattedExecutionResult = computed(() =>
  executionResult.value ? JSON.stringify(executionResult.value, null, 2) : "",
);

function hideContextMenu() {
  contextMenu.visible = false;
  contextMenu.folder = null;
}

function filterTreeNode(keyword: string, data: TreeNode) {
  if (!keyword) {
    return true;
  }
  return data.name.toLowerCase().includes(keyword.toLowerCase());
}

watch(folderKeyword, (value) => {
  treeRef.value?.filter(value);
});

async function refreshFolders() {
  folders.value = await fetchToolCardFolders();
}

async function loadFolder(folderId: number) {
  const detail = await fetchToolCardFolderDetail(folderId);
  cards.value = detail.cards;
  currentFolderId.value = folderId;
  await nextTick();
  treeRef.value?.setCurrentKey(folderId);
}

async function loadBootstrap(force = false) {
  loading.value = true;
  try {
    const data = await fetchToolCardsBootstrap(force);
    folders.value = data.folders;
    const targetFolderId = data.selected_folder_id ?? data.folders[0]?.id ?? null;
    currentFolderId.value = targetFolderId;
    if (targetFolderId) {
      cards.value = data.selected_folder_id === targetFolderId ? data.cards : [];
      await nextTick();
      treeRef.value?.setCurrentKey(targetFolderId);
    } else {
      cards.value = [];
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function handleFolderNodeClick(node: TreeNode) {
  hideContextMenu();
  await loadFolder(node.id);
}

function showFolderContextMenu(event: MouseEvent, folder: ToolCardFolder) {
  event.preventDefault();
  contextMenu.visible = true;
  contextMenu.x = event.clientX + 4;
  contextMenu.y = event.clientY + 4;
  contextMenu.folder = folder;
  currentFolderId.value = folder.id;
  nextTick(() => {
    treeRef.value?.setCurrentKey(folder.id);
  });
}

async function promptFolderName(title: string, initialValue = "") {
  try {
    const { value } = await ElMessageBox.prompt("请输入文件夹名称", title, {
      inputValue: initialValue,
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      inputValidator: (input) => (input.trim() ? true : "文件夹名称不能为空"),
    });
    return value.trim();
  } catch {
    return null;
  }
}

async function createRootFolder() {
  const name = await promptFolderName("添加文件夹");
  if (!name) {
    return;
  }
  try {
    const detail = await createToolCardFolder({
      name,
      description: "",
      parent_id: null,
      sort_order: 0,
      is_default: false,
    });
    await refreshFolders();
    await loadFolder(detail.folder.id);
    ElMessage.success(`文件夹“${name}”已添加`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function createSubFolder(folder: ToolCardFolder) {
  const parent = folders.value.find((item) => item.id === folder.id);
  if (!parent) {
    return;
  }
  const parentOfParent = folders.value.find((item) => item.id === parent.parent_id);
  if (parentOfParent) {
    ElMessage.warning("工具卡片最多支持两级文件夹");
    return;
  }
  const name = await promptFolderName("添加子文件夹");
  if (!name) {
    return;
  }
  try {
    const detail = await createToolCardFolder({
      name,
      description: "",
      parent_id: folder.id,
      sort_order: 0,
      is_default: false,
    });
    await refreshFolders();
    await loadFolder(detail.folder.id);
    ElMessage.success(`子文件夹“${name}”已添加`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function renameFolder(folder: ToolCardFolder) {
  const name = await promptFolderName("编辑文件夹", folder.name);
  if (!name) {
    return;
  }
  try {
    await updateToolCardFolder(folder.id, {
      name,
      description: folder.description,
      parent_id: folder.parent_id,
      sort_order: folder.sort_order,
      is_default: folder.is_default,
    });
    await refreshFolders();
    await loadFolder(folder.id);
    ElMessage.success("文件夹名称已更新");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function removeFolder(folder: ToolCardFolder) {
  try {
    await ElMessageBox.confirm(`确定要删除文件夹“${folder.name}”吗？`, "确认删除", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }

  try {
    await deleteToolCardFolder(folder.id);
    await refreshFolders();
    const nextFolderId = folders.value[0]?.id ?? null;
    if (nextFolderId) {
      await loadFolder(nextFolderId);
    } else {
      currentFolderId.value = null;
      cards.value = [];
    }
    ElMessage.success("文件夹已删除");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

function openCreateCardDialog() {
  hideContextMenu();
  if (!currentFolderId.value) {
    ElMessage.info("请先选择文件夹");
    return;
  }
  editingCard.value = null;
  configDialogVisible.value = true;
}

function openEditCardDialog(card: ToolCard) {
  editingCard.value = card;
  configDialogVisible.value = true;
}

async function handleCardSaved(card: ToolCard) {
  await refreshFolders();
  await loadFolder(card.folder_id);
}

async function handleCopyCard(card: ToolCard) {
  try {
    const copied = await copyToolCard(card.id);
    await refreshFolders();
    await loadFolder(copied.folder_id);
    ElMessage.success(`卡片“${card.name}”已复制`);
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function handleDeleteCard(card: ToolCard) {
  try {
    await ElMessageBox.confirm(`确定要删除卡片“${card.name}”吗？`, "确认删除", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }

  try {
    await deleteToolCard(card.id);
    if (currentFolderId.value) {
      await refreshFolders();
      await loadFolder(currentFolderId.value);
    }
    ElMessage.success("卡片已删除");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function handleExecuteCard(payload: { card: ToolCard; variables: Record<string, unknown> }) {
  try {
    executionResult.value = await executeToolCard(payload.card.id, payload.variables);
    executionDialogVisible.value = true;
    ElMessage.success("执行完成");
  } catch (error) {
    ElMessage.error((error as Error).message);
  }
}

async function handleContextAction(action: "edit" | "add-card" | "add-child" | "delete") {
  const folder = contextMenu.folder;
  hideContextMenu();
  if (!folder) {
    return;
  }
  if (action === "edit") {
    await renameFolder(folder);
    return;
  }
  if (action === "add-card") {
    currentFolderId.value = folder.id;
    openCreateCardDialog();
    return;
  }
  if (action === "add-child") {
    await createSubFolder(folder);
    return;
  }
  await removeFolder(folder);
}

onMounted(() => {
  loadBootstrap(false);
  window.addEventListener("click", hideContextMenu);
});

onBeforeUnmount(() => {
  window.removeEventListener("click", hideContextMenu);
});
</script>

<template>
  <div v-loading="loading" class="tool-cards-page">
    <aside class="tool-cards-page__sidebar">
      <div class="tool-cards-page__toolbar">
        <el-tooltip content="添加文件夹" placement="bottom">
          <el-button text circle @click="createRootFolder">
            <el-icon><FolderAdd /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="删除文件夹" placement="bottom">
          <el-button text circle :disabled="!currentFolder" @click="currentFolder && removeFolder(currentFolder)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="添加卡片" placement="bottom">
          <el-button text circle :disabled="!currentFolder" @click="openCreateCardDialog">
            <el-icon><CirclePlus /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <div class="tool-cards-page__search">
        <span>搜索:</span>
        <el-input v-model="folderKeyword" size="small" placeholder="输入文件夹名称..." clearable />
      </div>

      <div class="tool-cards-page__tree-wrap">
        <el-tree
          ref="treeRef"
          :data="folderTreeData"
          node-key="id"
          default-expand-all
          highlight-current
          :filter-node-method="filterTreeNode"
          :expand-on-click-node="false"
          @node-click="handleFolderNodeClick"
        >
          <template #default="{ data }">
            <div class="tool-cards-page__tree-node" @contextmenu.prevent="showFolderContextMenu($event, data)">
              <span class="tool-cards-page__tree-label">{{ data.name }}</span>
            </div>
          </template>
        </el-tree>
      </div>
    </aside>

    <section class="tool-cards-page__content">
      <div v-if="cards.length === 0" class="tool-cards-page__empty">
        {{ currentFolder ? "该文件夹下暂无卡片" : "请先创建或选择文件夹" }}
      </div>

      <div v-else class="tool-cards-page__grid">
        <ToolCardWidget
          v-for="card in cards"
          :key="card.id"
          :card="card"
          @execute="handleExecuteCard"
          @edit="openEditCardDialog"
          @copy="handleCopyCard"
          @delete="handleDeleteCard"
        />
      </div>
    </section>

    <div
      v-if="contextMenu.visible && contextMenu.folder"
      class="tool-cards-page__context-menu"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      @click.stop
    >
      <button type="button" @click="handleContextAction('edit')">
        <el-icon><Edit /></el-icon>
        编辑
      </button>
      <button type="button" @click="handleContextAction('add-card')">
        <el-icon><CirclePlus /></el-icon>
        新增卡片
      </button>
      <button type="button" @click="handleContextAction('add-child')">
        <el-icon><FolderAdd /></el-icon>
        新增子文件夹
      </button>
      <button type="button" class="is-danger" @click="handleContextAction('delete')">
        <el-icon><Delete /></el-icon>
        删除
      </button>
    </div>

    <ToolCardConfigDialog
      v-model="configDialogVisible"
      :folder-id="currentFolderId"
      :card="editingCard"
      @saved="handleCardSaved"
    />

    <el-dialog v-model="executionDialogVisible" title="执行结果" width="820px">
      <el-input :model-value="formattedExecutionResult" type="textarea" :rows="24" readonly />
    </el-dialog>
  </div>
</template>

<style scoped>
.tool-cards-page {
  position: relative;
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #d6dde5;
  border-radius: 8px;
  background: #f8fafc;
}

.tool-cards-page__sidebar {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 6px;
  border-right: 1px solid #d9e1e8;
  background: #ffffff;
}

.tool-cards-page__toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0 6px;
}

.tool-cards-page__toolbar :deep(.el-button) {
  width: 32px;
  height: 32px;
  margin: 0;
  color: #334155;
}

.tool-cards-page__search {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
  padding-bottom: 6px;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.tool-cards-page__search :deep(.el-input__wrapper) {
  min-height: 28px;
  font-size: 12px;
}

.tool-cards-page__tree-wrap {
  min-height: 0;
  overflow: auto;
  border: 1px solid #d9e1e8;
  border-radius: 6px;
  background: #ffffff;
}

.tool-cards-page__tree-wrap :deep(.el-tree) {
  --el-tree-node-hover-bg-color: #f5f5f5;
  --el-tree-node-content-height: 34px;
  padding: 4px 0;
  background: #ffffff;
  font-size: 12px;
}

.tool-cards-page__tree-wrap :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: #e3f2fd;
}

.tool-cards-page__tree-node {
  width: 100%;
  display: flex;
  align-items: center;
}

.tool-cards-page__tree-label {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tool-cards-page__content {
  min-height: 0;
  overflow: auto;
  padding: 16px;
}

.tool-cards-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 360px);
  gap: 16px;
  align-content: start;
}

.tool-cards-page__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #64748b;
  font-size: 13px;
}

.tool-cards-page__context-menu {
  position: fixed;
  z-index: 30;
  display: flex;
  flex-direction: column;
  min-width: 144px;
  padding: 6px;
  border: 1px solid #d9e1e8;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
}

.tool-cards-page__context-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #334155;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}

.tool-cards-page__context-menu button:hover {
  background: #f1f5f9;
}

.tool-cards-page__context-menu button.is-danger {
  color: #dc2626;
}
</style>
