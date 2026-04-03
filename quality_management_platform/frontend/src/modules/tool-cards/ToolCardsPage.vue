<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { get } from "@/shared/api/client";
import ModuleHeader from "@/shared/components/ModuleHeader.vue";

type FolderItem = {
  id: number;
  name: string;
  description?: string;
  parent_id?: number | null;
};

const folders = ref<FolderItem[]>([]);
const projects = ref<Record<string, unknown>[]>([]);
const cards = ref<Record<string, unknown>[]>([]);
const currentFolder = ref<FolderItem | null>(null);
const loading = ref(false);

async function loadOverview() {
  loading.value = true;
  try {
    const data = await get<{ projects: Record<string, unknown>[]; folders: FolderItem[] }>(
      "/api/tool-cards/overview/",
    );
    projects.value = data.projects;
    folders.value = data.folders;
    if (folders.value[0]) {
      await loadFolder(folders.value[0]);
    }
  } catch (error) {
    ElMessage.error((error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function loadFolder(folder: FolderItem) {
  currentFolder.value = folder;
  const detail = await get<{ cards: Record<string, unknown>[] }>(`/api/tool-cards/folders/${folder.id}/`);
  cards.value = detail.cards;
}

onMounted(loadOverview);
</script>

<template>
  <div class="page-shell">
    <ModuleHeader
      title="工具卡片"
      subtitle="把项目、目录树和卡片资产集中成统一工作台，保持业务结构清晰，也更符合后台管理系统的操作节奏。"
    >
      <el-button :loading="loading" @click="loadOverview">刷新概览</el-button>
    </ModuleHeader>

    <div class="grid-three">
      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">项目集合</p>
              <p class="section-caption">查看工具卡片所属项目。</p>
            </div>
            <span class="muted-text">共 {{ projects.length }} 条</span>
          </div>
        </template>
        <el-table :data="projects" height="320">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="name" label="项目" min-width="140" />
          <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">目录树</p>
              <p class="section-caption">点击目录查看所属卡片。</p>
            </div>
            <span class="muted-text">共 {{ folders.length }} 条</span>
          </div>
        </template>
        <el-table :data="folders" height="320" @row-click="loadFolder">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="name" label="目录" min-width="140" />
          <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card class="surface-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <div>
              <p class="section-title">当前卡片</p>
              <p class="section-caption">当前目录：{{ currentFolder?.name || "未选择" }}</p>
            </div>
            <span class="muted-text">共 {{ cards.length }} 条</span>
          </div>
        </template>
        <el-table :data="cards" height="320">
          <el-table-column prop="id" label="ID" width="72" />
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="card_type" label="类型" min-width="120" />
          <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<style scoped></style>
