<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import BusinessProjectContextBar from "@/shared/components/BusinessProjectContextBar.vue";
import ModuleHeader from "@/shared/components/ModuleHeader.vue";

const route = useRoute();

const title = computed(() => String(route.meta.title ?? "模块页面"));
const subtitle = computed(() => String(route.meta.subtitle ?? "该模块页面已预留，可继续接入业务能力。"));
const note = computed(() => String(route.meta.note ?? "当前已完成菜单结构和页面占位。"));
const useBusinessContext = computed(() => Boolean(route.meta.useBusinessContext));
const contextTitle = computed(() => String(route.meta.contextTitle ?? "业务组 / 项目上下文"));
const contextSubtitle = computed(() =>
  String(route.meta.contextSubtitle ?? "当前页面已接入全局业务组/项目主数据，后续功能迁移可直接复用该上下文。"),
);
</script>

<template>
  <div class="page-shell">
    <ModuleHeader :title="title" :subtitle="subtitle" />
    <BusinessProjectContextBar
      v-if="useBusinessContext"
      :title="contextTitle"
      :subtitle="contextSubtitle"
      compact
    />

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div>
          <p class="section-title">模块说明</p>
          <p class="section-caption">当前页面先承接信息架构，后续可继续接入表单、列表、流程和关联关系。</p>
        </div>
      </template>

      <div class="soft-panel">
        <strong>{{ title }}</strong>
        <p>{{ note }}</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.soft-panel p {
  margin: 8px 0 0;
  color: var(--qm-text-secondary);
  font-size: 13px;
  line-height: 1.8;
}
</style>
